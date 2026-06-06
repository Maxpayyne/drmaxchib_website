"""Weather data fetchers.

Primary source: Open-Meteo ERA5 reanalysis (archive) + forecast.
Free, no API key, no rate limits in practice. Hourly resolution.

Fallback: Iowa Environmental Mesonet (IEM) ASOS observations. Real station
data, no key, but only at airport locations (KY01 / KMSN / KMFI for us).

Leaf wetness is not directly measured by either; we estimate it using a
simple, well-cited dew-period proxy: any hour where RH >= 90% OR there
was precipitation is counted as 1 hour of leaf wetness. This matches the
heuristic used by NEWA's CART-derived approximation when sensors are
absent (Sentelhas et al. 2008, Agric For Meteorol).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import httpx
import pandas as pd

from .sites import Site


OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
IEM_ASOS = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

# Hourly variables we pull from Open-Meteo. Names per their API docs.
OM_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "shortwave_radiation",
    "wind_speed_10m",
]


@dataclass
class WeatherFrame:
    """Hourly weather + derived columns, with provenance."""

    hourly: pd.DataFrame  # index = tz-aware datetime, columns named below
    source: str  # 'open-meteo' or 'iem-asos'
    site_code: str

    # Standard column names downstream code expects:
    #   temp_c, rh_pct, dewpoint_c, precip_mm, solar_wm2, wind_ms, leaf_wet


def _fetch_open_meteo_range(
    site: Site, start: dt.date, end: dt.date, *, forecast: bool = False
) -> pd.DataFrame:
    """Pull hourly data from Open-Meteo for [start, end] inclusive."""
    # Request UTC times — local-timezone responses produce ambiguous hours
    # during DST transitions (the November "fall back" 1 AM happens twice
    # and pandas can't disambiguate from the string alone). UTC has no
    # such ambiguity, and tz_convert handles DST correctly.
    params = {
        "latitude": site.latitude,
        "longitude": site.longitude,
        "hourly": ",".join(OM_HOURLY_VARS),
        "timezone": "UTC",
        "windspeed_unit": "ms",
    }
    if forecast:
        # Forecast endpoint: past_days back, forecast_days forward.
        today = dt.date.today()
        past = max(0, (today - start).days)
        future = max(0, (end - today).days)
        params["past_days"] = min(past, 92)  # API cap
        params["forecast_days"] = min(future, 16)
        url = OPEN_METEO_FORECAST
    else:
        params["start_date"] = start.isoformat()
        params["end_date"] = end.isoformat()
        url = OPEN_METEO_ARCHIVE

    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    h = data["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["time"] = df["time"].dt.tz_convert(site.timezone)
    df = df.set_index("time").rename(columns={
        "temperature_2m": "temp_c",
        "relative_humidity_2m": "rh_pct",
        "dew_point_2m": "dewpoint_c",
        "precipitation": "precip_mm",
        "shortwave_radiation": "solar_wm2",
        "wind_speed_10m": "wind_ms",
    })
    return df


def _fetch_iem_asos(site: Site, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Observational fallback from IEM. Returns frame with same columns as OM."""
    params = {
        "station": site.nearest_asos,
        "data": "tmpf,dwpf,relh,p01i,sknt,drct",
        "year1": start.year, "month1": start.month, "day1": start.day,
        "year2": end.year, "month2": end.month, "day2": end.day,
        "tz": "Etc/UTC",
        "format": "onlycomma",
        "latlon": "no",
        "missing": "empty",
        "trace": "0.0001",
        "report_type": "3,4",
    }
    with httpx.Client(timeout=60.0) as client:
        r = client.get(IEM_ASOS, params=params)
        r.raise_for_status()
        text = r.text
    df = pd.read_csv(pd.io.common.StringIO(text))
    df["valid"] = pd.to_datetime(df["valid"], utc=True)
    df = df.set_index("valid").tz_convert(site.timezone)
    # Convert units: °F → °C, in/hr precip → mm, knots → m/s
    out = pd.DataFrame(index=df.index)
    out["temp_c"] = (df["tmpf"] - 32) * 5 / 9
    out["dewpoint_c"] = (df["dwpf"] - 32) * 5 / 9
    out["rh_pct"] = df["relh"]
    out["precip_mm"] = df["p01i"] * 25.4
    out["solar_wm2"] = pd.NA  # ASOS doesn't report solar
    out["wind_ms"] = df["sknt"] * 0.5144
    # Resample to hourly mean (some ASOS reports come at 5-min intervals)
    out = out.resample("1h").mean()
    return out


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Add columns: leaf_wet (0/1 per hour) and a few helpers."""
    df = df.copy()
    import numpy as np
    df["leaf_wet"] = ((df["rh_pct"] >= 90) | (df["precip_mm"].fillna(0) > 0.1)).astype(int)
    # Vapor pressure deficit (kPa), Tetens formula
    es = 0.6108 * np.exp(17.27 * df["temp_c"] / (df["temp_c"] + 237.3))
    df["vpd_kpa"] = es * (1 - df["rh_pct"] / 100)
    return df


def fetch(site: Site, start: dt.date, end: dt.date) -> WeatherFrame:
    """Get hourly weather for [start, end]. Tries Open-Meteo, falls back to IEM."""
    today = dt.date.today()
    try:
        if end <= today - dt.timedelta(days=2):
            hourly = _fetch_open_meteo_range(site, start, end, forecast=False)
        elif start >= today - dt.timedelta(days=92):
            hourly = _fetch_open_meteo_range(site, start, end, forecast=True)
        else:
            # Span crosses archive/forecast boundary: stitch.
            split = today - dt.timedelta(days=2)
            a = _fetch_open_meteo_range(site, start, split, forecast=False)
            b = _fetch_open_meteo_range(site, split + dt.timedelta(days=1), end, forecast=True)
            hourly = pd.concat([a, b]).sort_index()
        source = "open-meteo"
    except Exception as e:
        print(f"[warn] Open-Meteo failed for {site.code}: {e}; falling back to IEM ASOS")
        hourly = _fetch_iem_asos(site, start, end)
        source = "iem-asos"

    hourly = add_derived(hourly)
    return WeatherFrame(hourly=hourly, source=source, site_code=site.code)


def daily_summary(wf: WeatherFrame) -> pd.DataFrame:
    """Resample hourly to daily, replicating Max's R script summaries."""
    h = wf.hourly
    # Defensively drop rows with NaT in the index (can happen with messy
    # observational data even though Open-Meteo UTC fetch shouldn't produce any).
    h = h[h.index.notna()]
    daily = pd.DataFrame(index=pd.DatetimeIndex(sorted(set(h.index.date))))
    daily.index.name = "date"
    g = h.groupby(h.index.date)
    daily["temp_mean"] = g["temp_c"].mean().values
    daily["temp_min"] = g["temp_c"].min().values
    daily["temp_max"] = g["temp_c"].max().values
    daily["rh_mean"] = g["rh_pct"].mean().values
    daily["rh_min"] = g["rh_pct"].min().values
    daily["rh_max"] = g["rh_pct"].max().values
    daily["precip_mm"] = g["precip_mm"].sum().values
    daily["leaf_wet_hrs"] = g["leaf_wet"].sum().values
    daily["solar_mj"] = (g["solar_wm2"].sum() * 3600 / 1e6).values  # MJ/m²/day
    return daily
