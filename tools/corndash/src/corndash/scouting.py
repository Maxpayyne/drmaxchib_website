"""Ingest scouting workbooks (xlsx or CSV) into the dashboard format.

The CSV format is the canonical going-forward input — text-based, git-
diffable, easy to edit in any tool. The xlsx parser remains for backward
compatibility with Max's original 2025 workbook. When both formats exist
for the same season, the pipeline prefers the CSV (see corndash.pipeline).

Both parsers emit the same point-aggregated dict shape that the dashboard
component consumes:

    {
        "date": "2025-08-26",
        "field": "3300",
        "point": "1",
        "latitude": 43.3465, "longitude": -89.7014,
        "n_plants_rated": 5,
        "southern_rust": {
            "incidence_category": "Low",
            "incidence_pct": 0.077,
            "severity_E_minus_1_mean": 0.4,
            "severity_E_mean": 0.0,
            "severity_E_plus_1_mean": 0.0,
        },
        "ear_rot": {...}  # only present if ear rot data was recorded
    }
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _clean_coord(v) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    m = re.match(r"^(-?\d+\.?\d*)\s*([NSEW]?)$", s, re.IGNORECASE)
    if not m:
        try:
            return float(s)
        except ValueError:
            return None
    val = float(m.group(1))
    suf = m.group(2).upper()
    if suf in ("S", "W"):
        val = -abs(val)
    return val


def _mean(s):
    if s is None:
        return None
    s2 = pd.to_numeric(s, errors="coerce").dropna()
    if s2.empty:
        return None
    return round(float(s2.mean()), 3)


def _aggregate_point(date: dt.date, field, point, group: pd.DataFrame) -> dict | None:
    """Build a point-level record from a group of plant rows.

    Returns None if the point has no disease data (neither southern rust
    nor ear rot ratings present) — those rows are field-visits without
    scouting and shouldn't appear as ghost points in the dashboard.
    """
    field_str = str(int(field)) if isinstance(field, (int, float)) and not pd.isna(field) else str(field)
    point_str = str(int(point)) if isinstance(point, (int, float)) and not pd.isna(point) else str(point)

    lat = lon = None
    if "latitude" in group.columns:
        lat_raw = group["latitude"].dropna().iloc[0] if group["latitude"].notna().any() else None
        lat = _clean_coord(lat_raw)
    if "longitude" in group.columns:
        lon_raw = group["longitude"].dropna().iloc[0] if group["longitude"].notna().any() else None
        lon = _clean_coord(lon_raw)
    if lon is not None and lon > 0:
        lon = -abs(lon)

    # Count only plants that received at least one rating (severity or
    # category). Both CSV and xlsx may include placeholder rows for plants
    # that were skipped — those shouldn't bump the n_plants_rated count.
    rating_cols = [c for c in (
        "sr_severity_e_minus_1", "sr_severity_e", "sr_severity_e_plus_1",
        "ear_rot_severity",
        "E-1_sev", "E_sev", "E+1_sev",
        "Ear_rot_sev",
    ) if c in group.columns]
    if rating_cols:
        non_null = group[rating_cols].apply(lambda r: r.notna().any(), axis=1)
        n_rated = int(non_null.sum())
    else:
        n_rated = int(group.shape[0])

    rec: dict = {
        "date": date.isoformat(),
        "field": field_str,
        "point": point_str,
        "latitude": lat,
        "longitude": lon,
        "n_plants_rated": n_rated,
    }

    # Southern rust
    sr_cat = None
    sr_pct = None
    cat_col = "sr_incidence_category" if "sr_incidence_category" in group.columns else "SR_Incid"
    pct_col = (
        "sr_incidence_pct" if "sr_incidence_pct" in group.columns
        else "SR_Incid_no" if "SR_Incid_no" in group.columns
        else "SR_Incid_no(%)" if "SR_Incid_no(%)" in group.columns
        else None
    )
    if cat_col in group.columns:
        cat_vals = group[cat_col].dropna()
        if not cat_vals.empty:
            sr_cat = str(cat_vals.iloc[0])
    if pct_col and pct_col in group.columns:
        pct_vals = pd.to_numeric(group[pct_col], errors="coerce").dropna()
        if not pct_vals.empty:
            v = float(pct_vals.iloc[0])
            sr_pct = v / 100 if v > 1 else v

    sev_columns = [
        ("severity_E_minus_1_mean", ["sr_severity_e_minus_1", "E-1_sev"]),
        ("severity_E_mean",         ["sr_severity_e",         "E_sev"]),
        ("severity_E_plus_1_mean",  ["sr_severity_e_plus_1",  "E+1_sev"]),
    ]
    sev = {}
    for out_key, candidates in sev_columns:
        for c in candidates:
            if c in group.columns:
                sev[out_key] = _mean(group[c])
                break
        else:
            sev[out_key] = None

    if sr_cat or sr_pct is not None or any(v is not None for v in sev.values()):
        rec["southern_rust"] = {
            "incidence_category": sr_cat,
            "incidence_pct": round(sr_pct, 4) if sr_pct is not None else None,
            **sev,
        }

    # Ear rot
    er_pct_col = "ear_rot_incidence_pct" if "ear_rot_incidence_pct" in group.columns else "Ear_rot_incid"
    er_sev_col = "ear_rot_severity" if "ear_rot_severity" in group.columns else "Ear_rot_sev"
    if er_pct_col in group.columns and group[er_pct_col].notna().any():
        rec["ear_rot"] = {
            "incidence_pct": _mean(group.get(er_pct_col)),
            "severity_mean": _mean(group.get(er_sev_col)),
        }

    # Skip points with no disease data — those are field visits without
    # scouting that shouldn't appear as ghost points in the dashboard.
    if "southern_rust" not in rec and "ear_rot" not in rec:
        return None

    return rec


# ---------------------------------------------------------------------------
# CSV loader (preferred)
# ---------------------------------------------------------------------------
def _load_csv(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns:
        return []
    out: list[dict] = []
    for (date_str, field, point), grp in df.groupby(["date", "field", "point"], dropna=True):
        if pd.isna(field) or pd.isna(point):
            continue
        try:
            date = dt.date.fromisoformat(str(date_str))
        except ValueError:
            continue
        rec = _aggregate_point(date, field, point, grp)
        if rec is not None:
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# XLSX loader (legacy)
# ---------------------------------------------------------------------------
def _ffill_point(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("Field", "point", "latitude", "longitude"):
        if c in df.columns:
            df[c] = df[c].ffill()
    return df


def _parse_xlsx_sheet(df: pd.DataFrame, date: dt.date) -> list[dict]:
    df = _ffill_point(df)
    if not all(c in df.columns for c in ("Field", "point")):
        return []
    needed = [c for c in ("E-1_sev", "E_sev", "E+1_sev", "SR_Incid") if c in df.columns]
    df = df.dropna(how="all", subset=needed) if needed else df

    out: list[dict] = []
    for (field, point), grp in df.groupby(["Field", "point"], dropna=True):
        if pd.isna(field) or pd.isna(point):
            continue
        rec = _aggregate_point(date, field, point, grp)
        if rec is not None:
            out.append(rec)
    return out


def _load_xlsx(path: Path) -> list[dict]:
    xl = pd.ExcelFile(path)
    out: list[dict] = []
    for sheet in xl.sheet_names:
        m = re.match(r"Scout_Sample_(\d{1,2})\.(\d{1,2})\.(\d{2,4})", sheet)
        if not m:
            continue
        mo, day, yr = (int(x) for x in m.groups())
        if yr < 100:
            yr += 2000
        date = dt.date(yr, mo, day)
        out.extend(_parse_xlsx_sheet(xl.parse(sheet), date))
    return out


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def load_groundtruth(path: str | Path) -> list[dict]:
    """Load scouting records from a CSV or xlsx workbook."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return _load_csv(p)
    if suffix in (".xlsx", ".xls"):
        return _load_xlsx(p)
    raise ValueError(f"unsupported scouting file format: {p.suffix}")
