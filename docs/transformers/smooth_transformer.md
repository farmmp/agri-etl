# SmoothTransformer

Applies a **simple moving-average (SMA)** to one or more numeric sensor fields,
reducing high-frequency noise in the data stream.

## Config

| Key | Type | Required | Default | Description |
|-----|------|----------|---------|-------------|
| `fields` | `dict[str, int]` | ✅ | — | Mapping of field name → window size (must be ≥ 2) |
| `fill_partial` | `bool` | ❌ | `False` | Emit smoothed values before the window is full |

## Behaviour

- For each field listed in `fields`, the transformer maintains an internal
  sliding buffer of the configured window size.
- Once the buffer is full the output value is replaced with the arithmetic mean
  of all values in the buffer.
- When `fill_partial=False` (default), records are **dropped** until the buffer
  reaches its target window size. This avoids emitting poorly-averaged values at
  pipeline startup.
- When `fill_partial=True`, smoothing begins immediately using however many
  samples are available.
- Fields absent from a record are silently skipped.
- Non-numeric field values are skipped with an error entry; the record is still
  passed downstream.
- All other readings and metadata on the record are preserved unchanged.

## Example

```python
from agri_etl.transform import SmoothTransformer

transformer = SmoothTransformer({
    "fields": {
        "temperature_c": 5,   # 5-sample moving average
        "soil_moisture": 3,
    },
    "fill_partial": False,
})

result = transformer.transform(batch)
print(result.passed)   # smoothed records
print(result.dropped)  # records held back while window fills
```

## Pipeline integration

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform import SmoothTransformer, ClampTransformer

pipeline = Pipeline(
    reader=reader,
    transformers=[
        ClampTransformer({"bounds": {"temperature_c": [-40, 60]}}),
        SmoothTransformer({"fields": {"temperature_c": 5}, "fill_partial": True}),
    ],
    loader=loader,
)
pipeline.run()
```

## Notes

- The internal buffer is **stateful across batches**, so smoothing is continuous
  even when records arrive in multiple `transform()` calls.
- Window sizes must be integers ≥ 2; a window of 1 would be a no-op.
