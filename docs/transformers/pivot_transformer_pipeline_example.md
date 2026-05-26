# PivotTransformer – Full Pipeline Example

This example shows how to integrate `PivotTransformer` in a real agricultural
monitoring pipeline that ingests narrow MQTT messages and stores wide rows in
Postgres.

## Scenario

Field sensors publish one MQTT message per metric:

```json
{"sensor_id": "field-01", "ts": "2024-06-01T06:00:00Z", "metric": "soil_moisture", "value": 34.2}
{"sensor_id": "field-01", "ts": "2024-06-01T06:00:00Z", "metric": "temperature",   "value": 18.7}
{"sensor_id": "field-01", "ts": "2024-06-01T06:00:00Z", "metric": "humidity",      "value": 72.1}
```

We want a single Postgres row per `(sensor_id, timestamp)` with columns
`soil_moisture`, `temperature`, and `humidity`.

## Pipeline code

```python
from agri_etl.pipeline import Pipeline
from agri_etl.ingestion.mqtt_reader import MqttReader
from agri_etl.transform.pivot_transformer import PivotTransformer
from agri_etl.transform.clamp_transformer import ClampTransformer
from agri_etl.transform.round_transformer import RoundTransformer
from agri_etl.load.postgres_loader import PostgresLoader

reader = MqttReader(
    config={
        "host": "broker.example.com",
        "port": 1883,
        "topic": "sensors/field/#",
        "client_id": "agri-etl-pivot",
    }
)

transformers = [
    # Collapse narrow records into wide records
    PivotTransformer(
        config={
            "pivot_field": "metric",
            "value_field": "value",
        }
    ),
    # Guard against out-of-range sensor readings
    ClampTransformer(
        config={
            "bounds": {
                "soil_moisture": {"min": 0.0, "max": 100.0},
                "temperature": {"min": -40.0, "max": 85.0},
                "humidity": {"min": 0.0, "max": 100.0},
            }
        }
    ),
    # Round to 2 decimal places for storage
    RoundTransformer(
        config={
            "fields": {
                "soil_moisture": 2,
                "temperature": 2,
                "humidity": 2,
            }
        }
    ),
]

loader = PostgresLoader(
    config={
        "dsn": "postgresql://user:pass@db.example.com/agri",
        "table": "sensor_readings",
    }
)

pipeline = Pipeline(reader=reader, transformers=transformers, loader=loader, batch_size=50)

if __name__ == "__main__":
    pipeline.run()
```

## Expected output row

| sensor_id | timestamp            | soil_moisture | temperature | humidity |
|-----------|----------------------|---------------|-------------|----------|
| field-01  | 2024-06-01T06:00:00Z | 34.2          | 18.7        | 72.1     |
