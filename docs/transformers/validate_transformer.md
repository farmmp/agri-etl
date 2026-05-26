# ValidateTransformer

Validates sensor record readings against per-field type and range constraints.
Invalid records can be flagged (metadata annotated), silently dropped, or cause
an immediate exception.

## Config

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `rules` | `dict` | ✅ | — | Mapping of field name → constraint dict |
| `on_fail` | `str` | ❌ | `"flag"` | How to handle violations: `"flag"`, `"drop"`, or `"raise"` |

### Constraint keys (per field)

| Key | Type | Description |
|-----|------|-------------|
| `type` | `str` | Expected Python type: `"int"`, `"float"`, `"str"`, `"bool"` |
| `min` | `number` | Inclusive lower bound |
| `max` | `number` | Inclusive upper bound |
| `required` | `bool` | Whether absence of the field is an error (default `True`) |

## Behaviour

- **`flag`** (default): invalid records are kept; a `_validation_errors` list is
  added to `record.metadata` describing each violation.
- **`drop`**: invalid records are silently removed; `TransformResult.dropped` is
  incremented.
- **`raise`**: a `ValueError` is raised on the first invalid record.

## Example

```python
from agri_etl.transform.validate_transformer import ValidateTransformer

transformer = ValidateTransformer({
    "rules": {
        "temperature": {"type": "float", "min": -40.0, "max": 85.0},
        "humidity":    {"type": "float", "min": 0.0,   "max": 100.0},
        "station_id":  {"type": "str"},
        "battery":     {"type": "float", "min": 0.0, "required": False},
    },
    "on_fail": "flag",
})

result = transformer.transform(records)
print(f"Flagged: {result.metadata['flagged']}")
print(f"Dropped: {result.dropped}")

for rec in result.records:
    if "_validation_errors" in rec.metadata:
        print(rec.sensor_id, rec.metadata["_validation_errors"])
```

## Pipeline integration

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform.validate_transformer import ValidateTransformer
from agri_etl.transform.unit_transformer import UnitTransformer

pipeline = Pipeline(
    reader=my_reader,
    transformers=[
        ValidateTransformer({
            "rules": {
                "temperature": {"type": "float", "min": -40.0, "max": 85.0},
            },
            "on_fail": "drop",
        }),
        UnitTransformer({
            "conversions": {"temperature": {"operation": "multiply", "factor": 1.8}},
        }),
    ],
    loader=my_loader,
)
pipeline.run()
```
