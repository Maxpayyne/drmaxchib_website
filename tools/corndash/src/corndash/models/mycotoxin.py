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
    grain_fill_days_after_silking: int = 45,
) -> pd.DataFrame:
    """Compute daily mycotoxin score from the ear_rot output frame.

    Expects the ear_rot_frame to contain ger_14d and fer_14d columns
    (rolling 14-day sums of conducive flags).

    The score is masked to zero outside the ear-susceptibility window.
    Gibberella and Fusarium ear rots infect through the silks (Reid 1999)
    and mycotoxin synthesis occurs in developing kernels through grain
    fill. No silks, no ears, no infection, no mycotoxin — so conducive
    weather before silking and after physiological maturity does not
    contribute to mycotoxin pressure. The window runs from the
    silking-window start (~R1 minus a few days) through silking +
    `grain_fill_days_after_silking` (default 45 d, approximately R6).
    """
    if "ger_14d" not in ear_rot_frame.columns or "fer_14d" not in ear_rot_frame.columns:
        raise ValueError("ear_rot_frame must contain ger_14d and fer_14d columns")

    out = pd.DataFrame(index=ear_rot_frame.index)
    daily_score = (W_GER * ear_rot_frame["ger_14d"] + W_FER * ear_rot_frame["fer_14d"]) / 14.0
    out["mycotoxin_score"] = daily_score.clip(0, 1)

    if silking_window:
        try:
            window_start = pd.Timestamp(silking_window["window_start"])
            # End of susceptibility = silking + grain_fill days (~R6).
            # If we have an explicit silking_date use it; otherwise pad the
            # window_end conservatively.
            if silking_window.get("silking_date"):
                susceptibility_end = (
                    pd.Timestamp(silking_window["silking_date"])
                    + pd.Timedelta(days=grain_fill_days_after_silking)
                )
            else:
                susceptibility_end = (
                    pd.Timestamp(silking_window["window_end"])
                    + pd.Timedelta(days=grain_fill_days_after_silking - 18)
                )

            outside_mask = (out.index < window_start) | (out.index > susceptibility_end)
            out.loc[outside_mask, "mycotoxin_score"] = 0.0

            # Silking-window mean uses the silking window itself, not the
            # full susceptibility window — that's the period of primary
            # infection and is what the dashboard card surfaces.
            silk_end = pd.Timestamp(silking_window["window_end"])
            silk_mask = (out.index >= window_start) & (out.index <= silk_end)
            silking_mean = float(out.loc[silk_mask, "mycotoxin_score"].mean())
            out.attrs["silking_mean"] = silking_mean if pd.notna(silking_mean) else 0.0
            out.attrs["susceptibility_window"] = {
                "start": window_start.date().isoformat(),
                "end": susceptibility_end.date().isoformat(),
            }
        except (KeyError, ValueError):
            out.attrs["silking_mean"] = None
    else:
        # Without a silking window we have no biological anchor — clamp to
        # zero so the dashboard never shows pre-emergence mycotoxin risk.
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
