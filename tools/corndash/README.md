# corndash

Python pipeline that fetches weather, runs corn disease models, and emits
JSON consumed by `src/pages/projects/corn-dashboard.astro`.

This package lives under `tools/corndash/` in the drmaxchib-site repo.
Its output goes to `src/data/corn-dashboard/` (not `public/`, because
Astro's Vite-based glob doesn't see files in `public/`).

## Local use

```bash
cd tools/corndash
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Backfill 2020-2024 across all three sites
python -m corndash.pipeline \
  --years 2020 2021 2022 2023 2024 \
  --out ../../src/data/corn-dashboard

# Current year for Prairie du Sac with actual planting date + scouting overlay
python -m corndash.pipeline \
  --years 2025 \
  --sites pds \
  --planting 2025-05-03 \
  --scouting /path/to/GroundTruthData.xlsx \
  --out ../../src/data/corn-dashboard
```

Then from the repo root: `npm run dev` and visit `/projects/corn-dashboard`.

## CLI flags

| Flag | What it does |
|---|---|
| `--years 2020 2021 …` | Refresh specific years. |
| `--current` | Refresh the current year only. |
| `--sites pds arl msh` | Which sites to run (any subset). |
| `--planting YYYY-MM-DD` | Override planting date; otherwise uses per-site default. |
| `--scouting path/to/xlsx` | Read the GroundTruthData workbook for the scouting overlay. |
| `--out path` | Where JSON gets written. |

## What the pipeline does, step by step

For each (site, year) pair it fetches hourly weather from Open-Meteo
(falling back to IEM ASOS if Open-Meteo is unreachable), resamples to
daily summaries, computes growing degree days from the planting date,
identifies the silking window, runs the Webster et al. 2023 tar spot
ensemble plus the Gibberella and Fusarium conducive-day indices, masks
tar spot risk outside the agronomic validity window, attaches any
scouting records relevant to that site-year, and writes a single
`<site>_<year>.json`. After all pairs run, an `index.json` is emitted
that lists every site-year with its summary statistics.

## Source layout

```
src/corndash/
  __init__.py
  sites.py          # PdS, Arlington, Marshfield definitions
  weather.py        # Open-Meteo + IEM fetchers, hourly→daily resample
  gdd.py            # Growing degree days + silking window from planting
  scouting.py       # Reads the GroundTruthData.xlsx workbook
  pipeline.py       # Orchestrates everything; CLI entry point
  models/
    __init__.py
    ear_rot.py      # Gibberella + Fusarium conduciveness
    tarspot.py      # Webster 2023 LR1-LR8 + ensemble
```
