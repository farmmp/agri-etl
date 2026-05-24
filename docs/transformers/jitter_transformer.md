# JitterTransformer

Adds small random noise (jitter) to numeric sensor readings. Useful for
simulation, data augmentation, or privacy-preserving perturbation of sensor
streams before export.

## Config

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `fields` | `dict[str, float]` | Yes | Mapping of field name → maximum jitter magnitude. |
| `seed` | `int` | No | Random seed for reproducible noise. Omit for non-deterministic output. |

## Behaviour

- For each field listed in `fields`, a uniform random value in
  `[-magnitude, +magnitude]` is sampled and added to the original value.
- Fields not present in a record are silently skipped.
- Non-numeric field values are skipped and an error message is appended to
  `TransformResult.errors`.
- A `seed` value makes output fully deterministic across runs.

## Example

```python
from agri_etl.transform.jitter_transformer import JitterTransformer

transformer = JitterTransformer({
    "fields": {
        "temperature_c": 0.5,   # ±0.5 °C noise
        "soil_moisture": 1.0,   # ±1.0 % noise
    },
    "seed": 42,
})

result = transformer.transform(records)
```

## Pipeline usage

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform.jitter_transformer import JitterTransformer

pipeline = Pipeline(
    reader=reader,
    transformers=[
        JitterTransformer({"fields": {"temperature_c": 0.3}, "seed": 0}),
    ],
    loader=loader,
)
pipeline.run()
```

## Notes

- Magnitude must be `>= 0`. A magnitude of `0` leaves the value unchanged.
- The transformer does **not** clip values after adding noise; combine with
  `ClampTransformer` if bounded output is required.
