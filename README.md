# agri-etl

Modular ETL pipeline framework for ingesting agricultural sensor and weather station data.

## Overview

`agri-etl` provides a composable set of readers, transformers, and loaders that can be wired together into a `Pipeline` to move sensor data from various sources to various destinations.

## Components

### Ingestion (Readers)

| Class | Description |
|---|---|
| `CsvReader` | Reads sensor records from a local CSV file |
| `MqttReader` | Subscribes to an MQTT broker topic |
| `HttpReader` | Polls a REST endpoint for sensor data |

### Transform

| Class | Description |
|---|---|
| `UnitTransformer` | Converts field values between physical units |
| `FilterTransformer` | Drops records that fail threshold rules |
| `AggregationTransformer` | Aggregates readings over a window (mean/min/max/sum) |
| `RenameTransformer` | Renames reading fields |
| `ClampTransformer` | Clamps field values to `[min, max]` bounds |
| `FillTransformer` | Fills missing fields with a constant or forward-fill strategy |
| `RoundTransformer` | Rounds numeric fields to a specified number of decimal places |

### Load (Loaders)

| Class | Description |
|---|---|
| `CsvLoader` | Appends records to a local CSV file |
| `PostgresLoader` | Inserts records into a PostgreSQL table |
| `MqttLoader` | Publishes records to an MQTT broker topic |
| `HttpLoader` | POSTs records to a REST endpoint |

## Quick Start

```python
from agri_etl.ingestion import CsvReader
from agri_etl.transform import UnitTransformer, RoundTransformer
from agri_etl.load import CsvLoader
from agri_etl.pipeline import Pipeline

reader = CsvReader(config={"path": "data/sensors.csv", "sensor_id_col": "id"})

transformers = [
    UnitTransformer(config={"conversions": {"temp_f": {"operation": "fahrenheit_to_celsius"}}}),
    RoundTransformer(config={"fields": {"temp_f": 2, "humidity": 1}}),
]

loader = CsvLoader(config={"path": "output/cleaned.csv"})

pipeline = Pipeline(reader=reader, transformers=transformers, loader=loader, batch_size=100)
pipeline.run()
```

## Running Tests

```bash
pip install -e .[dev]
pytest
```
