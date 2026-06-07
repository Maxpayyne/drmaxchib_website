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
from .models import ear_rot, mycotoxin, southern_rust, tarspot
from .weather import daily_summary, fetch

SEASON_START_MONTH = 4
SEASON_END_MONTH = 11

# In-repo input data lives alongside the pipeline (sibling to src/), so the
# build is reproducible from a fresh clone. Both scouting workbooks and the
# southern-rust arrivals JSON sit under tools/corndash/data/.
PIPELINE_ROOT = Path(__file__).resolve().parents[2]  # tools/corndash/
DEFAULT_SCOUTING_DIR = PIPELINE_ROOT / "data" / "scouting"
DEFAULT_ARRIVALS_DIR = PIPELINE_ROOT / "data" / "arrivals"

# Default planting dates by site & year — overridable on the CLI. Best
# guesses for southern Wisconsin silage corn; update as you get truth.
DEFAULT_PLANTING = {
    "pds": {"default": dt.date(1900, 5, 1)},  # placeholder, year is patched
    "arl": {"default": dt.date(1900, 5, 5)},
    "msh": {"default": dt.date(1900, 5, 10)},
}


def _planting_for(site: str, year: int, override: dt.date | None) -> dt.date:
    # The --planting flag describes the planting for ITS OWN year. When the
    # pipeline is processing other years, we ignore the override and use the
    # per-site calendar default. That keeps historical years on sensible
    # defaults instead of carrying a current-year date across decades.
    if override and override.year == year:
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
    out_dir: Path | None = None,
    arrivals_dir: Path | None = None,
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
    sr = southern_rust.compute(daily, wf.hourly, arrivals_dir=arrivals_dir, year=year)
    mx = mycotoxin.compute(er, silking_window=silking)

    # Mask tarspot risk to the agronomically valid window (30 d before
    # silking through silking + 75 d or Oct 31, whichever first).
    try:
        valid_from = pd.Timestamp(silking["window_start"]) - pd.Timedelta(days=30)
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

    merged = daily.join([er, ts, sr, mx])

    season_mask = (merged.index.month >= SEASON_START_MONTH) & (
        merged.index.month <= SEASON_END_MONTH
    )
    public = merged.loc[season_mask].copy()
    public.index = public.index.astype(str)

    # Pull the scouting records for this site-year, if provided. If no fresh
    # xlsx was passed on this run, preserve whatever scouting overlay was
    # written to disk last time — this keeps the daily auto-refresh from
    # silently wiping out manually-attached observations.
    scouting_for_site: list[dict] = []
    if scouting_records:
        scouting_for_site = [
            r for r in scouting_records
            if r.get("field") and dt.date.fromisoformat(r["date"]).year == year
            # Field 3300 and 8710 are both at PdS.
            and (site_code == "pds" if str(r["field"]) in ("3300", "8710") else False)
        ]
    elif out_dir is not None:
        prev_file = out_dir / f"{site_code}_{year}.json"
        if prev_file.exists():
            try:
                prev = json.loads(prev_file.read_text())
                scouting_for_site = prev.get("scouting", []) or []
                if scouting_for_site:
                    print(f"  [{site_code} {year}] preserved {len(scouting_for_site)} scouting records from prior run")
            except (OSError, json.JSONDecodeError) as e:
                print(f"  [{site_code} {year}] could not read prior scouting: {e}")

    # Window-window sums for southern rust during silking
    sr_silking_sum = None
    try:
        s = dt.date.fromisoformat(silking["window_start"])
        e = dt.date.fromisoformat(silking["window_end"])
        mask = (sr.index >= pd.Timestamp(s)) & (sr.index <= pd.Timestamp(e))
        sr_silking_sum = int(sr.loc[mask, "srust_conducive"].sum())
    except (KeyError, ValueError):
        pass

    arrival_final = sr.attrs.get("arrival_final_status") or {}
    myc_silking_mean = mx.attrs.get("silking_mean")

    # Headline mycotoxin numbers — categorize using the silking-window mean
    # so the verbal label tracks the period of actual susceptibility.
    myc_category = mycotoxin.categorize(myc_silking_mean if myc_silking_mean is not None else 0)
    myc_dominant = mycotoxin.dominant_driver(
        er.attrs.get("ger_silking_window_sum") or 0,
        er.attrs.get("fer_silking_window_sum") or 0,
    )

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
        "srust_conducive_days": int(sr["srust_conducive"].sum()),
        "srust_silking_window_sum": sr_silking_sum,
        "srust_peak_risk": (
            float(sr["srust_risk"].max()) if sr["srust_risk"].notna().any() else None
        ),
        "srust_arrival_tier": arrival_final.get("tier"),
        "srust_arrival_state": arrival_final.get("reference_state"),
        "srust_arrival_date": arrival_final.get("reference_date"),
        "srust_arrival_modifier": arrival_final.get("modifier"),
        "mycotoxin_peak_score": (
            float(mx["mycotoxin_score"].max()) if mx["mycotoxin_score"].notna().any() else None
        ),
        "mycotoxin_silking_mean": myc_silking_mean,
        "mycotoxin_category": myc_category,
        "mycotoxin_dominant": myc_dominant,
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
            "southern_rust": southern_rust.METADATA,
            "mycotoxin": mycotoxin.METADATA,
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
                    help="Path to a scouting xlsx. If omitted, auto-detects every xlsx in tools/corndash/data/scouting/.")
    ap.add_argument("--no-scouting", action="store_true",
                    help="Skip scouting ingest entirely (will still preserve prior overlay from disk).")
    ap.add_argument("--arrivals-dir", type=str, default=None,
                    help="Directory of per-year southern-rust arrivals JSON. Defaults to tools/corndash/data/arrivals/.")
    ap.add_argument("--out", default="data/output")
    args = ap.parse_args()

    if args.current:
        years = [dt.date.today().year]
    elif args.years:
        years = args.years
    else:
        years = list(range(2020, dt.date.today().year + 1))

    planting = dt.date.fromisoformat(args.planting) if args.planting else None
    arrivals_dir = Path(args.arrivals_dir) if args.arrivals_dir else DEFAULT_ARRIVALS_DIR

    # Resolve scouting: explicit path > in-repo auto-detect > none
    scouting_records: list[dict] = []
    from .scouting import load_groundtruth
    if args.no_scouting:
        pass
    elif args.scouting:
        scouting_records = load_groundtruth(args.scouting)
        print(f"[scouting] loaded {len(scouting_records)} records from {args.scouting}")
    elif DEFAULT_SCOUTING_DIR.exists():
        # Prefer CSV (canonical) over xlsx (legacy). When both exist for the
        # same season the CSV wins because it's been audited / hand-edited.
        csv_files = sorted(DEFAULT_SCOUTING_DIR.glob("*.csv"))
        xlsx_files = sorted(DEFAULT_SCOUTING_DIR.glob("*.xlsx")) if not csv_files else []
        for path in csv_files + xlsx_files:
            recs = load_groundtruth(path)
            scouting_records.extend(recs)
            print(f"[scouting] loaded {len(recs)} records from {path.name}")
        if not csv_files and not xlsx_files:
            print(f"[scouting] no scouting files in {DEFAULT_SCOUTING_DIR}/ (will preserve prior overlay from JSON)")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for site_code in args.sites:
        for year in years:
            payload = run_site_year(
                site_code, year, planting, scouting_records,
                out_dir=out_dir, arrivals_dir=arrivals_dir,
            )
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
