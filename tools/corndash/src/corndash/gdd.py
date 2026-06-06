"""Growing Degree Days (GDD) and corn phenology estimation.

GDD for corn uses the modified Method 1 with base 50 °F (10 °C) and a cap
at 86 °F (30 °C). In Celsius:

    GDD_C = max(0, ((min(Tmax, 30) + max(Tmin, 10)) / 2 - 10))

This is the standard NCGA / UW Extension formulation. Cumulative GDD from
planting date predicts the corn growth stages with much more biological
fidelity than calendar day.

Silking (R1) for full-season corn in southern Wisconsin typically falls
around 1400 GDD°F (~778 GDD°C). Short-season hybrids silk earlier
(~1200 GDD°F / ~667 GDD°C). The dashboard accepts a hybrid maturity rating
in GDD°C and computes the silking window dynamically.

References:
- Neild, R.E., Newman, J.E. (1986). Growing season characteristics and
  requirements in the corn belt. NCH-40, Purdue Coop. Ext. Service.
- UW-Madison Corn Agronomy: "Growing Degree Day Calculator" guidance.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd


# Defaults for full-season silage corn at Prairie du Sac (~104-day RM).
DEFAULT_HYBRID_GDD_TO_SILK_C = 778.0   # ≈ 1400 GDD °F
SILKING_WINDOW_DAYS_BEFORE = 3
SILKING_WINDOW_DAYS_AFTER = 18  # Schoeneberger & Hesketh: critical infection ≈ R1 → ~R3


def gdd_c(tmin: pd.Series, tmax: pd.Series, base: float = 10.0, cap: float = 30.0) -> pd.Series:
    """Daily GDD in degrees Celsius using the corn modified method."""
    tmax_capped = np.minimum(tmax, cap)
    tmin_floored = np.maximum(tmin, base)
    gdd = (tmax_capped + tmin_floored) / 2.0 - base
    return pd.Series(np.maximum(0.0, gdd.values), index=tmin.index, name="gdd_c")


def cumulative_gdd_from_planting(
    daily: pd.DataFrame, planting_date: dt.date
) -> pd.Series:
    """Returns cumulative GDD °C from planting through the season."""
    gdd_series = gdd_c(daily["temp_min"], daily["temp_max"])
    start = pd.Timestamp(planting_date)
    mask = gdd_series.index >= start
    cum = gdd_series.where(mask, 0).cumsum()
    return cum.rename("gdd_cum_c")


def estimate_silking_date(
    daily: pd.DataFrame,
    planting_date: dt.date,
    hybrid_gdd_to_silk_c: float = DEFAULT_HYBRID_GDD_TO_SILK_C,
) -> dt.date | None:
    """First date when cumulative GDD reaches the silking threshold.

    Returns None if the season hasn't accumulated enough GDD yet.
    """
    cum = cumulative_gdd_from_planting(daily, planting_date)
    above = cum[cum >= hybrid_gdd_to_silk_c]
    if above.empty:
        return None
    return above.index[0].date()


def silking_window(
    silking_date: dt.date,
    before: int = SILKING_WINDOW_DAYS_BEFORE,
    after: int = SILKING_WINDOW_DAYS_AFTER,
) -> tuple[dt.date, dt.date]:
    return (silking_date - dt.timedelta(days=before),
            silking_date + dt.timedelta(days=after))


def silking_window_from_planting(
    daily: pd.DataFrame,
    planting_date: dt.date,
    hybrid_gdd_to_silk_c: float = DEFAULT_HYBRID_GDD_TO_SILK_C,
) -> dict:
    """One-stop helper: returns dict with silking_date and window endpoints,
    or a default DOY-200–220 fallback window if GDD threshold not reached."""
    silk = estimate_silking_date(daily, planting_date, hybrid_gdd_to_silk_c)
    if silk is None:
        # Fallback: use literature default for southern WI corn (DOY 200-220)
        year = planting_date.year
        return {
            "silking_date": None,
            "window_start": pd.Timestamp(f"{year}-01-01").date() + dt.timedelta(days=199),
            "window_end": pd.Timestamp(f"{year}-01-01").date() + dt.timedelta(days=219),
            "source": "default_doy_200_220",
            "planting_date": planting_date.isoformat(),
            "hybrid_gdd_to_silk_c": hybrid_gdd_to_silk_c,
        }
    start, end = silking_window(silk)
    return {
        "silking_date": silk.isoformat(),
        "window_start": start.isoformat() if hasattr(start, "isoformat") else start,
        "window_end": end.isoformat() if hasattr(end, "isoformat") else end,
        "source": "gdd_from_planting",
        "planting_date": planting_date.isoformat(),
        "hybrid_gdd_to_silk_c": hybrid_gdd_to_silk_c,
    }
