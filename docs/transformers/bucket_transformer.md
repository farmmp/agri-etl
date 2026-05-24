# BucketTransformer

Assigns numeric sensor readings to named buckets (bins) based on configurable range rules.
A new field is added to each record containing the bucket label for the matched range.

## Configuration

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `buckets` | `dict` | Yes | — | Mapping of field names to a list of bucket specs |
| `output_suffix` | `str` | No | `"_bucket"` | Suffix appended to the source field name for the output field |
| `default_label` | `str` | No | `"unknown"` | Label assigned when no bucket range matches |

### Bucket Spec Fields

Each entry in a bucket list is a dict with:

| Key | Type | Required | Description |
|---|---|---|---|
| `label` | `str` | Yes | Name assigned when the value falls in this range |
| `min` | `float` | No* | Inclusive lower bound (`-inf` if omitted) |
| `max` | `float` | No* | Exclusive upper bound (`+inf` if omitted) |

\* At least one of `min` or `max` must be provided.

Ranges follow half-open interval semantics: `min <= value < max`.

## Example

```python
from agri_etl.transform.bucket_transformer import BucketTransformer

transformer = BucketTransformer({
    "buckets": {
        "temperature": [
            {"label": "cold",   "min": -20, "max": 10},
            {"label": "mild",   "min":  10, "max": 25},
            {"label": "hot",    "min":  25, "max": 50},
        ],
        "soil_moisture": [
            {"label": "dry",    "max": 30},
            {"label": "moist",  "min": 30, "max": 70},
            {"label": "wet",    "min": 70},
        ],
    },
    "output_suffix": "_bucket",
    "default_label": "out_of_range",
})

result = transformer.transform(records)
# Each record gains fields like `temperature_bucket` and `soil_moisture_bucket`.
```

## Notes

- Fields absent from a record or with a `None` value are silently skipped.
- The original source field is preserved unchanged.
- Bucket specs are evaluated in order; the first matching range wins.
