# RollingTransformer – Pipeline Integration Example

This example shows how to wire `RollingTransformer` into a full
`agri_etl` pipeline that reads from a CSV file, computes rolling
statistics, and writes results to another CSV file.

## Scenario

A weather station emits temperature and humidity readings every minute.
We want to:
1. Compute a 5-sample rolling **mean** for temperature.
2. Compute a 10-sample rolling **max** for humidity.
3. Write the enriched records to an output CSV.

## Code

```python
from agri_etl.ingestion.csv_reader import CsvReader
from agri_etl.transform.rolling_transformer import RollingTransformer
from agri_etl.load.csv_loader import CsvLoader
from agri_etl.pipeline import Pipeline

reader = CsvReader({
    "path": "data/weather_station.csv",
    "timestamp_col": "ts",
    "sensor_id_col": "station_id",
})

rolling = RollingTransformer({
    "windows": {
        "temperature": {
            "size": 5,
            "function": "mean",
            "output": "temp_mean5",
        },
        "humidity": {
            "size": 10,
            "function": "max",
            "output": "humidity_max10",
        },
    }
})

loader = CsvLoader({
    "path": "output/enriched_weather.csv",
    "append": False,
})

pipeline = Pipeline(
    reader=reader,
    transformers=[rolling],
    loader=loader,
    batch_size=64,
)

pipeline.run()
```

## Notes

- The rolling buffer is initialised empty; the first records will have a
  window smaller than `size` until it fills up — this is intentional and
  matches standard streaming behaviour.
- Chaining multiple transformers before `RollingTransformer` (e.g.
  `UnitTransformer` to convert °F → °C) is fully supported because each
  transformer operates on plain `SensorRecord` objects.
- For very large datasets consider combining `RollingTransformer` with
  `ResampleTransformer` upstream to reduce input cardinality.
