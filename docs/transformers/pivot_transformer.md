# PivotTransformer

Collapses multiple `SensorRecord` objects that share the same `sensor_id` and
`timestamp` into a single record by pivoting one field's *value* into a new key.

This is useful when a sensor emits one reading per metric (e.g. MQTT topics
publishing `{"metric": "temperature", "value": 22.5}`) and you want a single
wide record `{"temperature": 22.5, "humidity": 60.0}` per sensor per timestamp.

## Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `group_by` | `str` | `"sensor_id"` | Field used to group records (always combined with timestamp). |
| `pivot_field` | `str` | `"metric"` | Reading field whose *value* becomes a new key in the output record. |
| `value_field` | `str` | `"value"` | Reading field whose *value* is placed under the new key. |
| `timestamp_tolerance` | `int` | `0` | Reserved for future use – max seconds between records in the same group. Must be ≥ 0. |

## Behaviour

- Records where `pivot_field` or `value_field` is absent are **dropped** and
  counted in `TransformResult.dropped`.
- All other reading keys (i.e. those that are neither `pivot_field` nor
  `value_field`) are preserved verbatim in the output record.
- If two records in the same group have the *same* pivot value, the last one
  wins (dict update semantics).
- `metadata` is taken from the first record seen for each group.

## Example

```python
from agri_etl.transform.pivot_transformer import PivotTransformer

transformer = PivotTransformer(
    config={
        "pivot_field": "metric",
        "value_field": "value",
    }
)

result = transformer.transform(records)
for r in result.records:
    print(r.sensor_id, r.timestamp, r.readings)
# s1 2024-06-01T12:00:00+00:00 {'temperature': 22.5, 'humidity': 60.0}
```

## Pipeline example

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform.pivot_transformer import PivotTransformer
from agri_etl.transform.unit_transformer import UnitTransformer

pipeline = Pipeline(
    reader=mqtt_reader,
    transformers=[
        PivotTransformer({"pivot_field": "metric", "value_field": "reading"}),
        UnitTransformer({"conversions": {"temperature": ("celsius", "fahrenheit")}}),
    ],
    loader=postgres_loader,
)
pipeline.run()
```
