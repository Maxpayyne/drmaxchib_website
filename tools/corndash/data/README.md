# tools/corndash/data/

Input data files the pipeline reads. These are part of the repo so the
build is fully reproducible from a fresh clone.

## scouting/

Place on-farm scouting workbooks (`.xlsx`) here. The pipeline will pick
up all xlsx files in this directory automatically when `--scouting` is
omitted, so the daily GitHub Action can refresh the dashboard without
needing to know any paths.

Schema is a multi-sheet workbook with one sheet per scouting date named
like `Scout_Sample_M.D.YY` (e.g. `Scout_Sample_8.26.25`). Within each
sheet, plant-level rows under sparse Field/point/lat/lon identifiers
that are forward-filled by the parser. See `corndash/scouting.py` for
the full ingest logic.

Currently committed:
- `2025_south_rust_GroundTruthData.xlsx` — Max's PdS fields 3300 and
  8710, August and September 2025 ratings.

## arrivals/

Per-year JSON files of state-level southern rust first-confirmation
dates, used by `corndash.models.southern_rust` to compute the arrival
modifier. One file per year, named `<year>.json`.

Schema:

```json
{
  "year": 2025,
  "source_url": "https://corn.ipmpipe.org/southerncornrust/",
  "updated": "2025-12-31",
  "estimated": true,
  "notes": "optional human-readable provenance notes",
  "states": {
    "WI": "2025-08-26",
    "IL": "2025-08-05"
  }
}
```

`estimated: true` flags that the dates haven't been verified against the
weekly CPN observations table; the dashboard displays this caveat to the
reader. Set `estimated: false` once you've cross-referenced.

Years without a file get an empty arrivals dict, which means the southern
rust model uses the lowest-tier modifier (0.05) — effectively no arrival
risk.
