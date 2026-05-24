# LagTransformer

Adds lagged (previous-value) fields for specified sensor readings, enabling
feature engineering for time-series analysis and anomaly detection.

## Configuration

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `fields` | `dict[str, int]` | Yes | — | Mapping of field name → lag steps (≥ 1) |
| `fill_value` | `any` | No | `None` | Value used when history is insufficient |

## Output fields

For each entry `{"<field>": <steps>}` a new reading key `<field>_lag<steps>` is
added to every record.  The original field is preserved unchanged.

## Example

```python
from agri_etl.transform.lag_transformer import LagTransformer

transformer = LagTransformer({
    "fields": {
        "temperature": 1,
        "soil_moisture": 3,
    },
    "fill_value": 0.0,
})

result = transformer.transform(records)
```

With the config above each output record will contain:

- `temperature_lag1` — value of `temperature` from the previous record
- `soil_moisture_lag3` — value of `soil_moisture` from three records ago

## Notes

- State is **stateful per transformer instance**: the internal buffer is
  maintained across successive `transform()` calls, so the transformer can be
  used in a streaming pipeline without losing history between batches.
- The lag buffer is reset when a new `LagTransformer` instance is created.
- If a field is absent from a record, `None` is stored in the buffer for that
  step, and the lagged value will reflect that `None`.
