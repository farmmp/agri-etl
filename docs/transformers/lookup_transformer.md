# LookupTransformer

Replaces field values using a static lookup table. Useful for decoding
numeric status codes, translating sensor mode flags, or normalising
categorical labels ingested from external devices.

## Config

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `lookups` | `dict[str, dict]` | Yes | Maps each field name to a `{old_value: new_value}` table. |
| `default` | any | No | Fallback value used when a field value is not found in its table. If omitted the original value is kept. |

## Example

```python
from agri_etl.transform.lookup_transformer import LookupTransformer

transformer = LookupTransformer({
    "lookups": {
        "status_code": {
            0: "idle",
            1: "active",
            2: "fault",
        },
        "irrigation_mode": {
            "A": "auto",
            "M": "manual",
            "O": "off",
        },
    },
    "default": "unknown",
})

result = transformer.transform(batch)
```

## Behaviour

- Each record in the batch is processed independently.
- For every field listed in `lookups`, if the current value exists as a key
  in the corresponding table the value is replaced with the mapped entry.
- If the value is **not** in the table:
  - When `default` is configured, the field is set to the default.
  - When `default` is **not** configured, the original value is preserved.
- Fields present in `lookups` but absent from a record are silently skipped.
- The original `SensorRecord` objects are never mutated; new records are
  returned in the `TransformResult`.
- `dropped` is always `0` — no records are discarded.

## Notes

- Lookup keys are compared by equality (`==`), so `1` (int) and `"1"` (str)
  are treated as different keys. Ensure the types in the table match the
  types produced by your reader.
- Combine with `CastTransformer` upstream to normalise types before lookup.
