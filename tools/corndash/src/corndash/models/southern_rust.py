"""Southern corn rust (Puccinia polysora) risk model.

Two parts combined:

1. Local conduciveness — a binary daily flag tuned for Upper Midwest
   conditions where the disease operates near the cool end of its
   developmental range. Thresholds:
       22 °C <= daily mean T <= 32 °C
       AND leaf wetness hours per day >= 4

   The published "optimum" for Puccinia polysora is 25-30 °C with leaf
   wetness of 6+ hours (Casela & Frederiksen 1993), but spore germination
   and lesion expansion proceed at reduced rates from ~20 to ~32 °C and
   begin with as little as 3-4 h of leaf wetness (Sikora et al. 2014,
   Hennessy et al. 2007). Coding the optimum as a hard wall produced a
   model that wildly under-predicted disease pressure observed in WI
   2025 scouting — incidence ranging from Low to "All (hotspot)" at PdS
   despite the binary risk reading 15%. The broader thresholds here
   capture days that are favorable-but-suboptimum, which matches the
   observed disease pressure pattern.

2. Arrival modifier — Puccinia polysora does NOT overwinter north of the
   Gulf Coast and arrives in the Midwest by long-distance wind dispersal
   from the south each year. Risk before arrival is essentially zero
   regardless of how conducive the local weather is. We capture this by
   weighting local conduciveness by an arrival modifier that reflects
   how close confirmed observations have advanced to the target site's
   state.

   Tiers (anchored on Wisconsin, the primary site state):
     local       — confirmed in WI  → 1.00
     adjacent    — confirmed in IL, IA, MN, MI → 0.70
     regional    — confirmed in IN, OH, MO, NE, SD → 0.40
     southern    — only confirmed in states south of the Corn Belt → 0.15
     none        — no confirmations anywhere → 0.05

   Arrival data is loaded from a per-year JSON file under
   tools/corndash/data/arrivals/<year>.json. The file lists state codes
   and the first confirmed date of southern rust in each. The model uses
   the date as a ramp-on — risk before the date is set to the lower-tier
   modifier, and to the full tier modifier after.

References:
    Casela, C.R. and Frederiksen, R.A. (1993). Survival of Puccinia
        polysora urediniospores. Phytopathology 83:566-571.
    Hennessy, A. et al. (2007). Influence of temperature and relative
        humidity on infection of corn by Puccinia polysora. Plant
        Disease 91:444-447.
    Sikora, E.J. et al. (2014). Southern rust of corn. Plant Health
        Instructor doi:10.1094/PHI-I-2014-0824-01.
    Crop Protection Network — Southern Rust IPM PIPE
        https://corn.ipmpipe.org/southerncornrust/
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd


CITATION = (
    "Casela, C.R. and Frederiksen, R.A. (1993). Phytopathology 83:566-571. "
    "Arrival data from Crop Protection Network IPM PIPE southern rust "
    "tracker (https://corn.ipmpipe.org/southerncornrust/)."
)


# State tier definitions, anchored on the target growing region.
# These are tuned for Wisconsin / Upper Midwest sites; if we ever support
# sites further south we'd want a per-site override.
LOCAL_STATE = "WI"
ADJACENT_STATES = {"IL", "IA", "MN", "MI"}
REGIONAL_STATES = {"IN", "OH", "MO", "NE", "SD", "KS"}
SOUTHERN_STATES = {
    "TX", "OK", "AR", "LA", "MS", "AL", "GA", "FL",
    "TN", "KY", "NC", "SC", "VA", "WV",
}

TIER_MODIFIERS = {
    "local": 1.00,
    "adjacent": 0.70,
    "regional": 0.40,
    "southern": 0.15,
    "none": 0.05,
}


def conducive_days(daily: pd.DataFrame) -> pd.Series:
    """Daily 0/1 flag for local southern rust conduciveness.

    Tuned for Upper Midwest conditions — see the module docstring for
    why these are looser than the published "optimum" thresholds.
    """
    needed = ["temp_mean", "leaf_wet_hrs"]
    for c in needed:
        if c not in daily.columns:
            raise ValueError(f"daily summary missing column {c!r}")
    cond = (
        (daily["temp_mean"] >= 22)
        & (daily["temp_mean"] <= 32)
        & (daily["leaf_wet_hrs"] >= 4)
    )
    return cond.astype(int).rename("srust_conducive")


def load_arrivals(arrivals_dir: Path | str, year: int) -> dict:
    """Load the per-year arrivals JSON. Returns {} if file missing.

    Expected file shape:
        {
          "year": 2025,
          "source_url": "https://corn.ipmpipe.org/southerncornrust/",
          "updated": "2025-09-15",
          "notes": "optional human-readable notes",
          "estimated": true | false,
          "states": {
              "WI": "2025-08-26",
              "IL": "2025-08-05",
              ...
          }
        }
    """
    p = Path(arrivals_dir) / f"{year}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _tier_for_state(state: str) -> str:
    if state == LOCAL_STATE:
        return "local"
    if state in ADJACENT_STATES:
        return "adjacent"
    if state in REGIONAL_STATES:
        return "regional"
    if state in SOUTHERN_STATES:
        return "southern"
    return "none"


def arrival_status(arrivals: dict, as_of: dt.date) -> dict:
    """Given the arrivals dict and an as-of date, return the most-advanced
    tier reached by that date.

    Returns dict with: tier (str), modifier (float), reference_state (str|None),
    reference_date (str|None), all_confirmed (list of (state, date) sorted).
    """
    states = arrivals.get("states", {})
    confirmed_by_date = []
    for st, date_str in states.items():
        try:
            date = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        if date <= as_of:
            confirmed_by_date.append((st, date))

    if not confirmed_by_date:
        return {
            "tier": "none",
            "modifier": TIER_MODIFIERS["none"],
            "reference_state": None,
            "reference_date": None,
            "all_confirmed": [],
        }

    # Pick the most-advanced tier currently reached.
    tier_order = ["local", "adjacent", "regional", "southern", "none"]
    best_tier = "none"
    best_state = None
    best_date = None
    for st, dte in sorted(confirmed_by_date, key=lambda x: x[1]):
        t = _tier_for_state(st)
        if tier_order.index(t) < tier_order.index(best_tier):
            best_tier = t
            best_state = st
            best_date = dte

    return {
        "tier": best_tier,
        "modifier": TIER_MODIFIERS[best_tier],
        "reference_state": best_state,
        "reference_date": best_date.isoformat() if best_date else None,
        "all_confirmed": [(s, d.isoformat()) for s, d in sorted(confirmed_by_date, key=lambda x: x[1])],
    }


def compute(
    daily: pd.DataFrame,
    hourly: pd.DataFrame | None = None,
    arrivals_dir: Path | str | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    """Compute daily southern rust indices.

    Output columns:
      srust_conducive            — 0/1, local weather meets thresholds
      srust_conducive_14d        — rolling sum of conducive days (last 14 d)
      srust_local_index          — srust_conducive_14d / 14, in [0, 1]
      srust_arrival_modifier     — tier modifier valid for each date
      srust_risk                 — local_index * arrival_modifier, in [0, 1]
    """
    out = pd.DataFrame(index=daily.index)
    out["srust_conducive"] = conducive_days(daily)
    out["srust_conducive_14d"] = out["srust_conducive"].rolling(14, min_periods=1).sum()
    out["srust_local_index"] = (out["srust_conducive_14d"] / 14.0).clip(0, 1)

    arrivals = load_arrivals(arrivals_dir, year) if arrivals_dir and year else {}

    modifiers = []
    for idx in out.index:
        as_of = idx.date() if hasattr(idx, "date") else idx
        status = arrival_status(arrivals, as_of)
        modifiers.append(status["modifier"])
    out["srust_arrival_modifier"] = modifiers

    out["srust_risk"] = (out["srust_local_index"] * out["srust_arrival_modifier"]).clip(0, 1)
    out.attrs["arrivals"] = arrivals
    out.attrs["arrival_final_status"] = arrival_status(arrivals, dt.date(year, 12, 31)) if year else None
    return out


METADATA = {
    "name": "Southern rust",
    "pathogen": "Puccinia polysora",
    "primary_mycotoxin": None,
    "inputs": [
        "Daily mean temperature (22-32 °C)",
        "Daily leaf wetness hours (≥ 4)",
        "State-level arrival confirmations from CPN IPM PIPE",
    ],
    "thresholds": "T ∈ [22, 32] °C AND leaf wetness ≥ 4 h (loosened from optimum-only thresholds to match observed disease pressure)",
    "tier_modifiers": TIER_MODIFIERS,
    "citation": CITATION,
}