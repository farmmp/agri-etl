# DiffTransformer

Computes finite differences of consecutive sensor readings for one or more numeric fields.
Useful for detecting rates of change (e.g. temperature rise per interval) or preparing data for derivative-based models.

## Configuration

| Key      | Type          | Required | Default | Description                                      |
|----------|---------------|----------|---------|--------------------------------------------------|
| `fields` | `list[str]`   | Yes      | —       | Field names to differentiate.                    |
| `order`  | `int` (≥ 1)   | No       | `1`     | Order of the finite difference (1 = first diff). |

## Behaviour

- For each field listed in `fields`, the transformer maintains a rolling history of the last `order + 1` values.
- The first `order` records **per field** are dropped because there is not yet enough history to compute the difference.
- All fields **not** listed in `fields` are passed through unchanged.
- State is preserved across `transform()` calls, so the transformer works correctly when processing data in batches.

### First-order difference (default)

```
out[n] = in[n] - in[n-1]
```

### Second-order difference (`order: 2`)

```
out[n] = in[n] - 2*in[n-1] + in[n-2]
```

## Example

```python
from agri_etl.transform.diff_transformer import DiffTransformer

transformer = DiffTransformer({
    "fields": ["soil_moisture", "temperature"],
    "order": 1,
})

result = transformer.transform(batch)
print(result.dropped)   # records discarded while building history
print(result.records)   # SensorRecord list with differenced values
```

## Notes

- Input field values must support the `-` operator (numeric types).
- If a configured field is absent from a record, that record is passed through without modification for that field.
- Combine with `ResampleTransformer` to ensure uniform time spacing before differencing.
