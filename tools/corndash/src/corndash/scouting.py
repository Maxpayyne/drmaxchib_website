"""Ingest the GroundTruthData scouting workbook into the dashboard format.

The 2025 PdS scouting workbook (provided by Max) has multiple sheets at
different dates and varying schemas. This module:

  1. Reads the per-date Scout_Sample sheets.
  2. Aggregates the plant-level rows up to the point-level (mean severity,
     incidence proportion, etc.) since the spreadsheet uses sparse rows
     where Field/point/lat/lon are only filled in the first plant row.
  3. Optionally pulls silage quality NIR predictions if a quality sheet exists.

Output: a list of dicts with date, field, point, lat/lon, disease, metrics.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd


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
    if m.group(2).upper() in ("S", "W"):
        val = -val
    if m.group(2).upper() == "W" and val > 0:
        val = -val
    return val


def _ffill_point(df: pd.DataFrame, point_cols=("Field", "point", "latitude", "longitude")) -> pd.DataFrame:
    """Forward-fill the point identifiers down the plant-rows."""
    df = df.copy()
    for c in point_cols:
        if c in df.columns:
            df[c] = df[c].ffill()
    return df


def parse_scout_sample(df: pd.DataFrame, date: dt.date) -> list[dict]:
    """One Scout_Sample sheet -> list of point-level observation dicts."""
    df = _ffill_point(df)
    # Drop rows where no plant data is present
    needed = [c for c in ["E-1_sev", "E_sev", "E+1_sev", "SR_Incid"] if c in df.columns]
    df = df.dropna(how="all", subset=needed) if needed else df

    out: list[dict] = []
    if not all(c in df.columns for c in ("Field", "point")):
        return out

    for (field, point), grp in df.groupby(["Field", "point"], dropna=True):
        if pd.isna(field) or pd.isna(point):
            continue
        lat = _clean_coord(grp["latitude"].iloc[0]) if "latitude" in grp.columns else None
        lon = _clean_coord(grp["longitude"].iloc[0]) if "longitude" in grp.columns else None
        # Longitude is recorded as positive in Wisconsin even though it's west.
        if lon is not None and lon > 0:
            lon = -lon

        sr_incid_cat = grp["SR_Incid"].dropna().iloc[0] if "SR_Incid" in grp.columns and grp["SR_Incid"].notna().any() else None
        sr_incid_pct = None
        if "SR_Incid_no(%)" in grp.columns:
            v = grp["SR_Incid_no(%)"].dropna()
            if not v.empty and isinstance(v.iloc[0], (int, float)):
                sr_incid_pct = float(v.iloc[0])
        elif "SR_Incid_no" in grp.columns:
            v = grp["SR_Incid_no"].dropna()
            if not v.empty:
                first = v.iloc[0]
                if isinstance(first, (int, float)):
                    pct = float(first)
                    sr_incid_pct = pct * 100 if pct <= 1 else pct

        rec = {
            "date": date.isoformat(),
            "field": str(int(field)) if isinstance(field, (int, float)) and not pd.isna(field) else str(field),
            "point": str(int(point)) if isinstance(point, (int, float)) and not pd.isna(point) else str(point),
            "latitude": lat,
            "longitude": lon,
            "n_plants_rated": int(grp.shape[0]),
        }
        if sr_incid_cat or sr_incid_pct is not None:
            rec["southern_rust"] = {
                "incidence_category": sr_incid_cat,
                "incidence_pct": sr_incid_pct,
                "severity_E_minus_1_mean": _mean(grp.get("E-1_sev")),
                "severity_E_mean": _mean(grp.get("E_sev")),
                "severity_E_plus_1_mean": _mean(grp.get("E+1_sev")),
            }
        if "Ear_rot_incid" in grp.columns and grp["Ear_rot_incid"].notna().any():
            rec["ear_rot"] = {
                "incidence_pct": _mean(grp.get("Ear_rot_incid")),
                "severity_mean": _mean(grp.get("Ear_rot_sev")),
            }
        out.append(rec)
    return out


def _mean(s):
    if s is None:
        return None
    s2 = pd.to_numeric(s, errors="coerce").dropna()
    if s2.empty:
        return None
    return round(float(s2.mean()), 3)


def load_groundtruth(xlsx_path: str | Path) -> list[dict]:
    """Load every Scout_Sample_* sheet in the workbook."""
    xl = pd.ExcelFile(xlsx_path)
    records: list[dict] = []
    for sheet in xl.sheet_names:
        m = re.match(r"Scout_Sample_(\d{1,2})\.(\d{1,2})\.(\d{2,4})", sheet)
        if not m:
            continue
        mo, day, yr = (int(x) for x in m.groups())
        if yr < 100:
            yr += 2000
        date = dt.date(yr, mo, day)
        df = xl.parse(sheet)
        records.extend(parse_scout_sample(df, date))
    return records
