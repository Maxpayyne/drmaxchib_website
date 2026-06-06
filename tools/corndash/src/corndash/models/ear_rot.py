"""Gibberella ear rot (GER) and Fusarium ear rot (FER) risk indices.

Implements the conducive-day logic from Max Chibuogwu's R script for
Fusarium graminearum (GER) and the analogous Munkvold thresholds for
Fusarium verticillioides (FER). The silking window — which is when the
ear is most susceptible to infection through the silks — can be supplied
explicitly (date range) or computed from GDD via the gdd module.

Thresholds:
- GER: T >= 15 °C AND RH >= 80 %  (strict variant: RH >= 90 %)
- FER: 20 <= T <= 35 °C AND RH >= 70 %

References:
- Reid, L.M., Mather, D.E., Hamilton, R.I., Bolton, A.T. (1999). Plant
  Disease 83:711-717.
- Munkvold, G.P. (2003). Cultural and genetic approaches to managing
  mycotoxins in maize. Eur. J. Plant Pathol. 109:705-713.
- Reyes-Velazquez, W.P., et al. (2011) on FER moisture thresholds.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd


CITATION_GER = (
    "Reid, L.M., Mather, D.E., Hamilton, R.I., Bolton, A.T. (1999). "
    "Plant Disease 83:711-717. Thresholds in Munkvold, G.P. (2003), "
    "Eur. J. Plant Pathol. 109:705-713."
)
CITATION_FER = (
    "Munkvold, G.P. (2003). Eur. J. Plant Pathol. 109:705-713. "
    "Reyes-Velazquez et al. (2011)."
)


def conducive_days_ger(daily: pd.DataFrame, *, strict: bool = False) -> pd.Series:
    rh_cut = 90 if strict else 80
    cond = (daily["temp_mean"] >= 15) & (daily["rh_mean"] >= rh_cut)
    return cond.astype(int).rename("ger_strict" if strict else "ger")


def conducive_days_fer(daily: pd.DataFrame) -> pd.Series:
    cond = (
        (daily["temp_mean"] >= 20)
        & (daily["temp_mean"] <= 35)
        & (daily["rh_mean"] >= 70)
    )
    return cond.astype(int).rename("fer")


def window_sum(cond: pd.Series, start: dt.date, end: dt.date) -> int:
    """Sum of conducive days within [start, end] inclusive."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    mask = (cond.index >= s) & (cond.index <= e)
    return int(cond[mask].sum())


def compute(
    daily: pd.DataFrame,
    hourly: pd.DataFrame | None = None,
    silking_window: dict | None = None,
) -> pd.DataFrame:
    """Run all ear-rot related indices.

    silking_window : dict with keys window_start, window_end (ISO dates) — if
    provided, the silking-weighted summary in the output frame's attrs is
    computed against this window.
    """
    out = pd.DataFrame(index=daily.index)
    out["ger_conducive"] = conducive_days_ger(daily, strict=False)
    out["ger_conducive_strict"] = conducive_days_ger(daily, strict=True)
    out["fer_conducive"] = conducive_days_fer(daily)
    out["ger_14d"] = out["ger_conducive"].rolling(14, min_periods=1).sum()
    out["fer_14d"] = out["fer_conducive"].rolling(14, min_periods=1).sum()

    if silking_window:
        start = dt.date.fromisoformat(silking_window["window_start"])
        end = dt.date.fromisoformat(silking_window["window_end"])
        out.attrs["ger_silking_window_sum"] = window_sum(out["ger_conducive"], start, end)
        out.attrs["fer_silking_window_sum"] = window_sum(out["fer_conducive"], start, end)
        out.attrs["silking_window"] = silking_window

    return out


METADATA = {
    "ger": {
        "name": "Gibberella ear rot",
        "pathogen": "Fusarium graminearum",
        "primary_mycotoxin": "Deoxynivalenol (DON), zearalenone",
        "thresholds": "T >= 15 °C, RH >= 80 % (strict: RH >= 90 %)",
        "citation": CITATION_GER,
    },
    "fer": {
        "name": "Fusarium ear rot",
        "pathogen": "Fusarium verticillioides, F. proliferatum",
        "primary_mycotoxin": "Fumonisins",
        "thresholds": "20 <= T <= 35 °C, RH >= 70 %",
        "citation": CITATION_FER,
    },
}
