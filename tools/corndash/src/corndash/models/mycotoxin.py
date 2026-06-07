"""Mycotoxin risk composite.

A condition-based composite that combines Gibberella ear rot (GER) and
Fusarium ear rot (FER) conducive-day pressure into a single 0-1 score
plus a verbal category and dominant-driver label. The two diseases produce
different mycotoxins relevant to silage feed safety:

    GER (F. graminearum)   → deoxynivalenol (DON), zearalenone
    FER (F. verticillioides) → fumonisins

This is NOT a quantitative toxin prediction model — we don't have toxin
assays to fit one. It is a weather-based hazard index: when this score is
high, the conditions that historically produce mycotoxin-contaminated
silage have been present for an extended period during the susceptibility
window.

Score formula:
    daily mycotoxin_score = (w_ger * ger_14d + w_fer * fer_14d) / 14

with w_ger = 0.6, w_fer = 0.4 (reflecting that DON is the predominant
mycotoxin concern in Upper Midwest silage corn per Munkvold 2017). Output
is clipped to [0, 1].

Season summary:
    mycotoxin_peak           — max daily score
    mycotoxin_score_silking  — mean daily score across the silking window
    category                 — Low / Moderate / Elevated / High
    dominant                 — DON-leaning / Fumonisin-leaning / Both / —

References:
    Munkvold, G.P. (2017). Fusarium species and their associated
        mycotoxins. Methods Mol Biol 1542:51-106.
    Reid, L.M. et al. (1999). Plant Disease 83:711-717.
"""

from __future__ import annotations

import datetime as dt
import pandas as pd


CITATION = (
    "Munkvold, G.P. (2017). Fusarium species and their associated mycotoxins. "
    "Methods Mol Biol 1542:51-106. Reid et al. (1999) Plant Disease 83:711-717."
)


W_GER = 0.6
W_FER = 0.4

CATEGORY_BREAKS = [
    (0.15, "Low"),
    (0.40, "Moderate"),
    (0.70, "Elevated"),
    (1.01, "High"),
]


def categorize(score: float) -> str:
    if score is None or pd.isna(score):
        return "—"
    for thr, label in CATEGORY_BREAKS:
        if score < thr:
            return label
    return "High"


def dominant_driver(ger_silk_days: int, fer_silk_days: int) -> str:
    """Which mycotoxin family dominates the conducive pressure?"""
    if ger_silk_days == 0 and fer_silk_days == 0:
        return "—"
    g = max(ger_silk_days, 0)
    f = max(fer_silk_days, 0)
    if g >= 1.5 * f:
        return "DON-leaning"
    if f >= 1.5 * g:
        return "Fumonisin-leaning"
    return "Both"


def compute(
    ear_rot_frame: pd.DataFrame,
    silking_window: dict | None = None,
) -> pd.DataFrame:
    """Compute daily mycotoxin score from the ear_rot output frame.

    Expects the ear_rot_frame to contain ger_14d and fer_14d columns
    (rolling 14-day sums of conducive flags).

    The score is masked to zero BEFORE silking only — once ears exist they
    remain susceptible through grain fill, drying-down, late-season
    standing corn, and (where moisture allows) into stored silage. We
    do not impose an artificial upper-bound cutoff because:

    - Some growers leave corn in the field well into October-November,
      and the GER/FER infection thresholds (T ≥ 15 °C AND RH ≥ 80 %)
      can still be satisfied during that period.
    - Once kernels are infected, mycotoxin can continue accumulating
      whenever the weather is conducive.
    - The rolling 14-day weather sums naturally taper the score in late
      autumn when conducive conditions become rare — no artificial cap
      is needed.

    The pre-silking mask remains absolute: with no ears, there can be no
    ear-rot infection and no resulting mycotoxin, regardless of how
    conducive the weather is.
    """
    if "ger_14d" not in ear_rot_frame.columns or "fer_14d" not in ear_rot_frame.columns:
        raise ValueError("ear_rot_frame must contain ger_14d and fer_14d columns")

    out = pd.DataFrame(index=ear_rot_frame.index)
    daily_score = (W_GER * ear_rot_frame["ger_14d"] + W_FER * ear_rot_frame["fer_14d"]) / 14.0
    out["mycotoxin_score"] = daily_score.clip(0, 1)

    if silking_window:
        try:
            window_start = pd.Timestamp(silking_window["window_start"])
            # Pre-silking: zero — no ears exist yet.
            pre_silking = out.index < window_start
            out.loc[pre_silking, "mycotoxin_score"] = 0.0

            # Silking-window mean for the headline card number — primary
            # infection window only.
            silk_end = pd.Timestamp(silking_window["window_end"])
            silk_mask = (out.index >= window_start) & (out.index <= silk_end)
            silking_mean = float(out.loc[silk_mask, "mycotoxin_score"].mean())
            out.attrs["silking_mean"] = silking_mean if pd.notna(silking_mean) else 0.0
            out.attrs["mask_start"] = window_start.date().isoformat()
        except (KeyError, ValueError):
            out.attrs["silking_mean"] = None
    else:
        # No silking window — zero out everything since we can't anchor
        # the susceptibility start without it.
        out["mycotoxin_score"] = 0.0
        out.attrs["silking_mean"] = None

    return out


METADATA = {
    "name": "Mycotoxin risk (DON + fumonisin composite)",
    "pathogens": "Fusarium graminearum, Fusarium verticillioides",
    "primary_mycotoxins": ["DON (deoxynivalenol)", "Fumonisins"],
    "inputs": [
        "14-day rolling sums of Gibberella ear rot conducive days (w=0.6)",
        "14-day rolling sums of Fusarium ear rot conducive days (w=0.4)",
    ],
    "categories": "Low (<0.15), Moderate (<0.40), Elevated (<0.70), High",
    "citation": CITATION,
    "limitations": (
        "Condition-based hazard index, not a quantitative toxin prediction. "
        "High score means conditions favoring mycotoxin-producing infections "
        "were present, not that toxin levels will exceed thresholds at feed-out."
    ),
}