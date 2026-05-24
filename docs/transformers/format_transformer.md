# FormatTransformer

Applies string formatting operations to selected fields in each `SensorRecord`.

## Config

| Key       | Type   | Required | Description                                          |
|-----------|--------|----------|------------------------------------------------------|
| `formats` | `dict` | Yes      | Mapping of field name to format operation to apply.  |

### Supported Operations

| Operation | Description                          |
|-----------|--------------------------------------|
| `upper`   | Convert string to upper-case         |
| `lower`   | Convert string to lower-case         |
| `strip`   | Remove leading and trailing whitespace |
| `title`   | Convert string to title-case         |

## Behaviour

- Fields not present in a record are silently skipped.
- If a targeted field contains a non-string value, the value is left unchanged
  and a descriptive message is added to `TransformResult.errors`.
- The original `SensorRecord` objects are never mutated; new records are returned.

## Example

```python
from agri_etl.transform.format_transformer import FormatTransformer

transformer = FormatTransformer({
    "formats": {
        "sensor_label": "upper",
        "location":     "title",
        "raw_tag":      "strip",
    }
})

result = transformer.transform(records)
for rec in result.records:
    print(rec.readings)
```

## Pipeline Usage

```python
from agri_etl.pipeline import Pipeline
from agri_etl.transform.format_transformer import FormatTransformer

pipeline = Pipeline(
    reader=my_reader,
    transformers=[
        FormatTransformer({"formats": {"device_name": "lower"}}),
    ],
    loader=my_loader,
)
pipeline.run()
```

## Errors

Non-fatal errors (e.g. non-string fields) are collected in `TransformResult.errors`
and do **not** stop the pipeline.
