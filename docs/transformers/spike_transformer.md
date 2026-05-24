# SpikeTransformer

Detects and handles single-sample spikes in sensor readings by comparing each
value against the previous value for the same field. If the absolute delta
exceeds the configured threshold the record is either **dropped** or the
offending field is set to **null**.

## Configuration

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `thresholds` | `dict[str, float]` | ✅ | — | Field → max allowed absolute delta |
| `action` | `str` | ❌ | `drop` | `drop` removes the record; `null` nulls the field |

## Example

```python
from agri_etl.transform.spike_transformer import SpikeTransformer

transformer = SpikeTransformer({
    "thresholds": {
        "temperature_c": 10.0,
        "soil_moisture": 20.0,
    },
    "action": "null",
})
```

## Behaviour

- The **first** record seen for each field is always passed through (no
  previous value to compare against).
- State is maintained **across `transform()` calls**, so the transformer can
  be used in a streaming / batch pipeline without losing context between
  batches.
- When `action` is `drop` the entire record is moved to `TransformResult.dropped`.
- When `action` is `null` the record is kept but the spiking field value is
  replaced with `None`; the previous-value register is **not** updated so the
  next normal reading can recover cleanly.
- Fields not listed in `thresholds` are ignored.
- Non-numeric field values are silently skipped.

## Pipeline Example

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform.spike_transformer import SpikeTransformer

pipeline = Pipeline(
    reader=my_reader,
    transformers=[
        SpikeTransformer({"thresholds": {"temperature_c": 10.0}, "action": "drop"}),
    ],
    loader=my_loader,
)
pipeline.run()
```
