# ConditionalTransformer — Pipeline Example

This example shows how to combine `ConditionalTransformer` with other
transformers in a full `Pipeline` to flag anomalous sensor readings before
loading them to a CSV file.

## Scenario

A weather station streams temperature and humidity readings.  We want to:

1. Clamp raw values to physically plausible ranges.
2. Add a `heat_stress` flag when temperature exceeds 38 °C **and** humidity
   is above 70 %.
3. Mark any record whose sensor code is not in the approved list as
   `unverified`.
4. Write the enriched records to a CSV.

## Code

```python
from agri_etl.pipeline import Pipeline
from agri_etl.ingestion.csv_reader import CsvReader
from agri_etl.load.csv_loader import CsvLoader
from agri_etl.transform import ClampTransformer, ConditionalTransformer

reader = CsvReader({
    "path": "data/station_raw.csv",
    "timestamp_field": "ts",
    "sensor_id_field": "station_id",
})

clamp = ClampTransformer({
    "bounds": {
        "temperature_c": {"min": -50, "max": 60},
        "humidity_pct": {"min": 0, "max": 100},
    }
})

flag_heat = ConditionalTransformer({
    "conditions": {
        "heat_stress": {
            "field": "temperature_c",
            "op": "gt",
            "value": 38,
            "then": "STRESS",
            "else": "NORMAL",
        }
    }
})

flag_verified = ConditionalTransformer({
    "conditions": {
        "verified": {
            "field": "station_id",
            "op": "in",
            "value": ["WS-001", "WS-002", "WS-003"],
            "then": True,
            "else": False,
        }
    }
})

loader = CsvLoader({
    "path": "data/station_enriched.csv",
})

pipeline = Pipeline(
    reader=reader,
    transformers=[clamp, flag_heat, flag_verified],
    loader=loader,
    batch_size=500,
)

pipeline.run()
```

## Output columns

The enriched CSV will contain all original columns plus:

| column        | values              | description                        |
|---------------|---------------------|------------------------------------|
| `heat_stress` | `STRESS` / `NORMAL` | temperature-based heat stress flag |
| `verified`    | `True` / `False`    | whether station ID is approved     |
