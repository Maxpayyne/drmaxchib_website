"""Disease risk models. Each module exposes a `compute(daily, hourly)` function
returning a pandas Series indexed by date with the model's risk index, plus a
`CITATION` string and a `METADATA` dict describing the model."""
