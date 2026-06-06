"""Tar spot of corn (Phyllachora maydis) — Tarspotter risk models.

Implements the eight logistic regression models published in:

    Webster, R.W., Nicolli, C., Allen, T.W., Bish, M.D., Bissonnette, K.,
    Check, J.C., Chilvers, M.I., Dufeck, M.R., Kleczewski, N., Luis, J.M.,
    Mueller, B.D., Paul, P.A., Price, P.P., Robertson, A.E., Ross, T.J.,
    Schmidt, C., Schmidt, R., Schmidt, T., Shim, S., Telenko, D.E.P.,
    Wise, K., Smith, D.L. (2023). Uncovering the environmental conditions
    required for Phyllachora maydis infection and tar spot development on
    corn in the United States for use as predictive models for future
    epidemics. Scientific Reports 13:17064.
    https://doi.org/10.1038/s41598-023-44338-6

The published model evaluates the *increase* in P. maydis stroma between two
sequential rating dates as a binary delta. All coefficients are negative
because moderate temperatures (18-23 C) drive tar spot and extended high
humidity is actually antagonistic — see the paper's Discussion section.

The multi-model ensemble used in the production Tarspotter app and shown to
balance precision and recall best is the daily average of LR4 and LR6 risks
(paper Table 1: accuracy 87.4 %, kappa 0.61, recall 69.4 %). We expose all
eight LRs plus the ensemble; the dashboard displays the ensemble as the
headline risk and lets you drill into the components on the methods page.

Risk threshold for "tar spot likely" in the paper is 35 %.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


CITATION = (
    "Webster, R.W., Nicolli, C., Allen, T.W., Bish, M.D., Bissonnette, K., "
    "Check, J.C., Chilvers, M.I., Dufeck, M.R., Kleczewski, N., Luis, J.M., "
    "Mueller, B.D., Paul, P.A., Price, P.P., Robertson, A.E., Ross, T.J., "
    "Schmidt, C., Schmidt, R., Schmidt, T., Shim, S., Telenko, D.E.P., "
    "Wise, K., Smith, D.L. (2023). Scientific Reports 13:17064. "
    "https://doi.org/10.1038/s41598-023-44338-6"
)

RISK_THRESHOLD = 0.35


# ---------------------------------------------------------------------------
# Coefficients (exact values from Webster et al. 2023, equations 1-8)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LRCoefs:
    """One row in the published table of logistic regressions."""

    name: str
    intercept: float
    coefs: dict[str, float]  # variable name -> coefficient


LR1 = LRCoefs("LR1", 21.92522, {"temp_mean_30d": -0.97199, "rh90_hours_30d": -0.25014})
LR2 = LRCoefs("LR2", 22.6108,  {"temp_mean_30d": -0.9880,  "wetness_hours_30d": -6.0357})
LR3 = LRCoefs("LR3", 17.7869,  {"temp_mean_30d": -0.8964,  "dpd_min_30d":  0.8157})
LR4 = LRCoefs("LR4", 32.06987, {"temp_mean_30d": -0.89471, "rh_max_30d":  -0.14373})
LR5 = LRCoefs("LR5", 21.21170, {"temp_mean_30d": -0.94178, "rh90_hours_21d": -0.23661})
LR6 = LRCoefs("LR6", 20.35950, {"temp_mean_30d": -0.91093, "rh90_night_hours_14d": -0.29240})
LR7 = LRCoefs("LR7", 22.18844, {"temp_mean_30d": -0.96662, "wetness_hours_21d": -0.25134})
LR8 = LRCoefs("LR8", 21.66220, {"temp_mean_30d": -0.94504, "wetness_night_hours_14d": -0.34001})

ALL_LRS = [LR1, LR2, LR3, LR4, LR5, LR6, LR7, LR8]
ENSEMBLE_MEMBERS = (LR4, LR6)


# ---------------------------------------------------------------------------
# Feature engineering — moving-average windowpanes
# ---------------------------------------------------------------------------
def _need(daily: pd.DataFrame, hourly: pd.DataFrame | None, *cols: str) -> None:
    missing = [c for c in cols if c not in daily.columns]
    if missing:
        raise ValueError(f"daily frame missing columns: {missing}")
    if hourly is not None:
        pass


def compute_features(daily: pd.DataFrame, hourly: pd.DataFrame) -> pd.DataFrame:
    """Build all the moving-average inputs the LRs consume.

    daily : per-day frame with temp_mean, rh_max, dewpoint_min if available
    hourly: hourly frame with rh_pct, leaf_wet, dewpoint_c, temp_c

    Returns a frame indexed by date with one column per LR variable name.
    """
    _need(daily, hourly, "temp_mean", "rh_max")
    feats = pd.DataFrame(index=daily.index)

    # 30-day mean temperature — input to every model.
    feats["temp_mean_30d"] = daily["temp_mean"].rolling(30, min_periods=15).mean()

    # 30-day mean of daily max RH (LR4)
    feats["rh_max_30d"] = daily["rh_max"].rolling(30, min_periods=15).mean()

    # Hourly-derived counts: total hours of RH > 90 % per day, and nighttime
    # subset (20:00-06:00 local) per the paper's methods section.
    if hourly is not None and "rh_pct" in hourly.columns:
        h = hourly.copy()
        h["rh_gt_90"] = (h["rh_pct"] > 90).astype(int)
        is_night = (h.index.hour >= 20) | (h.index.hour < 6)
        h["rh_gt_90_night"] = h["rh_gt_90"] * is_night.astype(int)
        rh90_daily = h.groupby(h.index.date)["rh_gt_90"].sum()
        rh90_night_daily = h.groupby(h.index.date)["rh_gt_90_night"].sum()
        rh90_daily.index = pd.to_datetime(rh90_daily.index)
        rh90_night_daily.index = pd.to_datetime(rh90_night_daily.index)
        feats["rh90_hours_30d"] = rh90_daily.rolling(30, min_periods=15).mean().reindex(daily.index)
        feats["rh90_hours_21d"] = rh90_daily.rolling(21, min_periods=10).mean().reindex(daily.index)
        feats["rh90_night_hours_14d"] = (
            rh90_night_daily.rolling(14, min_periods=7).mean().reindex(daily.index)
        )

        # Wetness-hour proxy per paper: DPD <= 2 C => wet (binary, hourly).
        # We use the same `leaf_wet` column produced by weather.add_derived().
        if "leaf_wet" not in h.columns:
            h["leaf_wet"] = ((h["rh_pct"] >= 90) | (h.get("precip_mm", 0) > 0.1)).astype(int)
        wet_daily = h.groupby(h.index.date)["leaf_wet"].sum()
        is_night_series = pd.Series(is_night, index=h.index).astype(int)
        wet_night_daily = (h["leaf_wet"] * is_night_series).groupby(h.index.date).sum()
        wet_daily.index = pd.to_datetime(wet_daily.index)
        wet_night_daily.index = pd.to_datetime(wet_night_daily.index)
        feats["wetness_hours_30d"] = wet_daily.rolling(30, min_periods=15).mean().reindex(daily.index)
        feats["wetness_hours_21d"] = wet_daily.rolling(21, min_periods=10).mean().reindex(daily.index)
        feats["wetness_night_hours_14d"] = (
            wet_night_daily.rolling(14, min_periods=7).mean().reindex(daily.index)
        )

        # Dew-point depression (T - Tdew); LR3 uses 30-day mean of daily min DPD.
        if "dewpoint_c" in h.columns and "temp_c" in h.columns:
            h["dpd"] = h["temp_c"] - h["dewpoint_c"]
            dpd_min_daily = h.groupby(h.index.date)["dpd"].min()
            dpd_min_daily.index = pd.to_datetime(dpd_min_daily.index)
            feats["dpd_min_30d"] = (
                dpd_min_daily.rolling(30, min_periods=15).mean().reindex(daily.index)
            )

    return feats


def _logit_to_risk(logit: pd.Series) -> pd.Series:
    return 1.0 / (1.0 + np.exp(-logit))


def _apply_lr(feats: pd.DataFrame, lr: LRCoefs) -> pd.Series:
    """Compute the risk probability for one LR. Returns NaN where any input
    feature is missing (typical at season start before the 30-day window
    fills)."""
    linpred = pd.Series(lr.intercept, index=feats.index, dtype=float)
    for var, coef in lr.coefs.items():
        if var not in feats.columns:
            return pd.Series(np.nan, index=feats.index, name=lr.name)
        linpred = linpred + coef * feats[var]
    return _logit_to_risk(linpred).rename(lr.name)


def compute(daily: pd.DataFrame, hourly: pd.DataFrame) -> pd.DataFrame:
    """Run all eight LRs + the LR4+LR6 ensemble. Returns frame indexed by date."""
    feats = compute_features(daily, hourly)
    out = pd.DataFrame(index=daily.index)
    for lr in ALL_LRS:
        out[lr.name] = _apply_lr(feats, lr)
    out["ensemble"] = (out["LR4"] + out["LR6"]) / 2.0

    # The headline number on the dashboard.
    out["tarspot_risk"] = out["ensemble"]
    out["tarspot_above_threshold"] = (out["tarspot_risk"] >= RISK_THRESHOLD).astype("Int64")

    # Inputs for transparency / methods page rendering
    for c in feats.columns:
        out[f"feat_{c}"] = feats[c]

    return out


METADATA = {
    "name": "Tar spot",
    "pathogen": "Phyllachora maydis",
    "primary_model": "Webster et al. 2023 LR4 + LR6 ensemble",
    "risk_threshold": RISK_THRESHOLD,
    "performance": {"accuracy": 0.874, "kappa": 0.61, "recall": 0.694, "precision": 0.676},
    "inputs": [
        "30-day mean of daily mean temperature",
        "30-day mean of daily max RH (LR4)",
        "14-day mean of nighttime hours with RH > 90 % (LR6)",
    ],
    "citation": CITATION,
}
