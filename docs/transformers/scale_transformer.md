# ScaleTransformer

Multiplies sensor reading fields by a constant numeric scale factor.  Useful
for unit conversions that can be expressed as a simple multiplication, such as
converting raw ADC counts to engineering units or rescaling voltage readings.

## Configuration

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `scales` | `dict[str, float]` | **yes** | — | Mapping of field name to scale factor. |
| `skip_missing` | `bool` | no | `False` | Skip fields absent from the record instead of recording an error. |

### Constraints

- `scales` must be a non-empty `dict`.
- Each factor must be a non-zero numeric value (`int` or `float`).
- Fields whose current value is not numeric will be skipped and an error entry
  added to `TransformResult.errors`.

## Example

```python
from agri_etl.transform.scale_transformer import ScaleTransformer

transformer = ScaleTransformer({
    "scales": {
        "voltage_mv": 0.001,   # millivolts -> volts
        "temp_raw": 0.0625,    # raw 12-bit ADC -> degrees Celsius
    },
    "skip_missing": True,
})

result = transformer.transform(records)
for rec in result.records:
    print(rec.readings)
```

## Behaviour

1. For each `SensorRecord` in the input list a new record is produced with
   scaled field values; all other fields are left unchanged.
2. If a target field is absent and `skip_missing` is `False` (default) an
   error message is appended to `TransformResult.errors` and the record is
   still emitted with the remaining fields scaled.
3. If a target field value is not numeric an error is recorded and the field
   is left at its original value.

## Notes

- To invert a scale (divide instead of multiply) use a factor of `1/N`,
  e.g. `0.001` instead of dividing by `1000`.
- Negative factors are permitted and will flip the sign of the value.
