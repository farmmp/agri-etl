# SanitizeTransformer

Replaces or removes sensor readings whose values match a configurable list of
**sentinel values** (e.g. `-999`, `None`, empty string).

## Config reference

| Key           | Type          | Required | Default | Description |
|---------------|---------------|----------|---------|-------------|
| `fields`      | `list[str]`   | ✓        | –       | Field names to inspect in each record. |
| `sentinels`   | `list`        | ✓        | –       | Values considered invalid / missing. |
| `replacement` | `any` / `null`| ✗        | `null`  | Substitute value. When `null` the key is **dropped** from the record. |
| `strict`      | `bool`        | ✗        | `false` | When `true`, an error is recorded for every listed field that does not exist in a record. |

## Example

```python
from agri_etl.transform import SanitizeTransformer

transformer = SanitizeTransformer({
    "fields": ["temperature", "humidity"],
    "sentinels": [-999, None, ""],
    "replacement": None,   # drop the key entirely
})

result = transformer.transform(records)
print(result.records)   # records with bad readings removed
print(result.errors)    # empty unless strict=True and fields were absent
```

## Behaviour

1. For each record, every field listed in `fields` is inspected.
2. If the field's value is in `sentinels`:
   - The key is **removed** from `readings` when `replacement` is `null`.
   - The key is **set to `replacement`** otherwise.
3. Fields not present in a record are silently skipped unless `strict: true`,
   in which case an error string is appended to `TransformResult.errors`.
4. Records are **always** passed through; no record is dropped entirely.

## Pipeline usage

```python
from agri_etl.pipeline import Pipeline

pipeline = Pipeline(
    reader=reader,
    transformers=[
        SanitizeTransformer({
            "fields": ["soil_moisture"],
            "sentinels": [-999, -1],
        }),
    ],
    loader=loader,
)
pipeline.run()
```
