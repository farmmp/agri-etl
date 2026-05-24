# RateTransformer

Computes the **per-second rate of change** (first derivative) of numeric sensor fields between consecutive records.

## Configuration

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `fields` | `list[str]` | ✅ | — | Field names to differentiate |
| `output_suffix` | `str` | ❌ | `"_rate"` | Suffix appended to each field name for the output column |
| `drop_first` | `bool` | ❌ | `true` | Drop the first record (no previous value available) |

## Behaviour

- For each record after the first, the transformer calculates:
  ```
  rate = (current_value - previous_value) / elapsed_seconds
  ```
- The original field values are **preserved**; the rate is written to a new key (e.g. `temp_rate`).
- Records where elapsed time is ≤ 0 are **skipped** and an error message is emitted.
- Missing field values produce a per-field error and that field's rate is omitted.
- Internal state persists across `transform()` calls, enabling streaming use.

## Example

```python
from agri_etl.transform import RateTransformer

transformer = RateTransformer({
    "fields": ["temperature", "soil_moisture"],
    "output_suffix": "_rate",
    "drop_first": True,
})

result = transformer.transform(batch)
for rec in result.records:
    print(rec.readings["temperature_rate"])  # °C / second
```

## Errors

Errors are non-fatal and collected in `TransformResult.errors`:

- `"Non-positive elapsed time …"` — duplicate or out-of-order timestamps.
- `"Missing field '…'"` — a required field is absent from one of the records.
- `"Cannot compute rate for '…'"` — field value is not numeric.
