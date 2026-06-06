"""End-to-end pipeline. Fetches weather, runs models, writes JSON for the
Astro frontend.

Usage examples:

    # All known site-years
    python -m corndash.pipeline

    # Just the current season for PdS, with a specified planting date
    python -m corndash.pipeline --current --sites pds --planting 2026-05-01

    # Refresh a specific historical year, write to a custom path
    python -m corndash.pipeline --years 2023 --out ../site/public/data/corn-dashboard

Output:
  <out>/<site>_<year>.json        per site-year, daily risk + features
  <out>/index.json                index of all site-years generated
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import gdd as gdd_mod
from . import sites as sites_mod
from .models import ear_rot, tarspot
from .weather import daily_summary, fetch

SEASON_START_MONTH = 4
SEASON_END_MONTH = 11

# Default planting dates by site & year — overridable on the CLI. Best
# guesses for southern Wisconsin silage corn; update as you get truth.
DEFAULT_PLANTING = {
    "pds": {"default": dt.date(1900, 5, 1)},  # placeholder, year is patched
    "arl": {"default": dt.date(1900, 5, 5)},
    "msh": {"default": dt.date(1900, 5, 10)},
}


def _planting_for(site: str, year: int, override: dt.date | None) -> dt.date:
    if override:
        return override
    seed = DEFAULT_PLANTING.get(site, {}).get("default", dt.date(1900, 5, 1))
    return dt.date(year, seed.month, seed.day)


def _json_safe(obj):
    """Recursively replace NaN/Inf with None so the result is valid JSON."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def run_site_year(
    site_code: str,
    year: int,
    planting_date: dt.date | None = None,
    scouting_records: list[dict] | None = None,
) -> dict:
    site = sites_mod.get(site_code)
    today = dt.date.today()
    start = dt.date(year, 1, 1)
    end = dt.date(year, 12, 31) if year < today.year else today + dt.timedelta(days=14)

    print(f"[{site_code} {year}] fetching {start} → {end} …")
    wf = fetch(site, start, end)
    daily = daily_summary(wf)

    # Phenology — silking window from planting date if we can compute it.
    planting = _planting_for(site_code, year, planting_date)
    silking = gdd_mod.silking_window_from_planting(daily, planting)

    er = ear_rot.compute(daily, wf.hourly, silking_window=silking)
    ts = tarspot.compute(daily, wf.hourly)

    # Mask tarspot risk to the agronomically valid window: from 30 days
    # before silking through harvest. The model's 30-day rolling means
    # produce extreme values outside the growing season (paper does not
    # claim validity before vegetative growth is established).
    try:
        valid_from = pd.Timestamp(silking["window_start"]) - pd.Timedelta(days=30)
        # Cap at silking date + 75 days (~R6 + silage dry-down) or Oct 31,
        # whichever comes first. Past this, the field has typically been
        # harvested and the model's late-season values are not actionable.
        silking_anchor = (
            pd.Timestamp(silking["silking_date"])
            if silking.get("silking_date")
            else pd.Timestamp(silking["window_start"])
        )
        valid_to = min(silking_anchor + pd.Timedelta(days=75),
                       pd.Timestamp(f"{year}-10-31"))
        invalid = (ts.index < valid_from) | (ts.index > valid_to)
        for col in ("tarspot_risk", "tarspot_above_threshold", "LR1", "LR2", "LR3",
                    "LR4", "LR5", "LR6", "LR7", "LR8", "ensemble"):
            if col in ts.columns:
                ts.loc[invalid, col] = pd.NA
    except (KeyError, ValueError) as e:
        print(f"[warn] could not apply tarspot mask for {site_code} {year}: {e}")

    merged = daily.join([er, ts])

    season_mask = (merged.index.month >= SEASON_START_MONTH) & (
        merged.index.month <= SEASON_END_MONTH
    )
    public = merged.loc[season_mask].copy()
    public.index = public.index.astype(str)

    # Pull the scouting records for this site-year, if provided.
    scouting_for_site = []
    if scouting_records:
        scouting_for_site = [
            r for r in scouting_records
            if r.get("field") and dt.date.fromisoformat(r["date"]).year == year
            # Field 3300 and 8710 are both at PdS.
            and (site_code == "pds" if str(r["field"]) in ("3300", "8710") else False)
        ]

    summary = {
        "ger_conducive_days": int(er["ger_conducive"].sum()),
        "ger_conducive_days_strict": int(er["ger_conducive_strict"].sum()),
        "fer_conducive_days": int(er["fer_conducive"].sum()),
        "ger_silking_window_sum": er.attrs.get("ger_silking_window_sum"),
        "fer_silking_window_sum": er.attrs.get("fer_silking_window_sum"),
        "tarspot_peak_risk": (
            float(ts["tarspot_risk"].max()) if ts["tarspot_risk"].notna().any() else None
        ),
        "tarspot_peak_date": (
            str(ts["tarspot_risk"].idxmax()) if ts["tarspot_risk"].notna().any() else None
        ),
        "tarspot_days_above_threshold": int(
            ts["tarspot_above_threshold"].fillna(0).sum()
        ),
    }

    daily_records = (
        public.round(3)
        .reset_index()
        .rename(columns={"index": "date"})
        .to_dict(orient="records")
    )

    payload = {
        "site": site_code,
        "site_name": site.name,
        "year": year,
        "data_source": wf.source,
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "phenology": silking,
        "summary": summary,
        "daily": daily_records,
        "scouting": scouting_for_site,
        "model_metadata": {
            "tarspot": tarspot.METADATA,
            "ear_rot": ear_rot.METADATA,
        },
    }
    return _json_safe(payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=None)
    ap.add_argument("--current", action="store_true")
    ap.add_argument("--sites", nargs="+", default=["pds", "arl", "msh"])
    ap.add_argument("--planting", type=str, default=None,
                    help="Planting date for the current year (ISO yyyy-mm-dd). Applied to all sites.")
    ap.add_argument("--scouting", type=str, default=None,
                    help="Path to GroundTruthData.xlsx for scouting overlay.")
    ap.add_argument("--out", default="data/output")
    args = ap.parse_args()

    if args.current:
        years = [dt.date.today().year]
    elif args.years:
        years = args.years
    else:
        years = list(range(2020, dt.date.today().year + 1))

    planting = dt.date.fromisoformat(args.planting) if args.planting else None

    scouting_records = []
    if args.scouting:
        from .scouting import load_groundtruth
        scouting_records = load_groundtruth(args.scouting)
        print(f"[scouting] loaded {len(scouting_records)} point-level observations")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for site_code in args.sites:
        for year in years:
            payload = run_site_year(site_code, year, planting, scouting_records)
            fname = f"{site_code}_{year}.json"
            (out_dir / fname).write_text(json.dumps(payload))
            n_days = len(payload["daily"])
            n_scout = len(payload["scouting"])
            print(f"  → {fname}  ({n_days} days, {n_scout} scouting, src={payload['data_source']})")
            written.append(fname)

    # Rebuild index.json from EVERY file in the output dir, not just the ones
    # we wrote in this run. This makes partial runs idempotent: running the
    # pipeline for a single year never clobbers the index entries for other
    # years that are already on disk.
    full_index = []
    for f in sorted(out_dir.glob("*_*.json")):
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"  [warn] skipping {f.name}: {e}")
            continue
        full_index.append({
            "site": data.get("site"),
            "site_name": data.get("site_name"),
            "year": data.get("year"),
            "file": f.name,
            "summary": data.get("summary", {}),
            "phenology": data.get("phenology", {}),
        })
    (out_dir / "index.json").write_text(json.dumps(full_index, indent=2))
    print(f"[done] wrote {len(written)} this run, index now lists {len(full_index)} site-years -> {out_dir}/")


if __name__ == "__main__":
    main()
