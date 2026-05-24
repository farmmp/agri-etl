# EncodeTransformer

Encodes categorical fields in sensor records as numeric values using either
**label encoding** or **one-hot encoding**.

## Configuration

| Key | Type | Required | Description |
|---|---|---|---|
| `encodings` | `dict` | Yes | Mapping of field name → encoding spec |

Each encoding spec can be:
- A plain string `"label"` or `"onehot"`
- A dict with keys `strategy` (required) and `classes` (optional list)

## Strategies

### `label`

Replaces the field value with an integer index.  If `classes` is supplied the
ordinal order is fixed; otherwise classes are assigned in the order they are
first encountered within the batch.

```python
EncodeTransformer({
    "encodings": {
        "soil_type": {
            "strategy": "label",
            "classes": ["clay", "sand", "silt"]
        }
    }
})
```

**Input readings:** `{"soil_type": "sand"}`  
**Output readings:** `{"soil_type": 1}`

### `onehot`

Replaces the field with a set of binary indicator fields named
`<field>_<class>`.  Provide `classes` to fix the set of indicator columns;
otherwise the unique values seen in the current batch are used.

```python
EncodeTransformer({
    "encodings": {
        "alert_status": {
            "strategy": "onehot",
            "classes": ["ok", "warn", "err"]
        }
    }
})
```

**Input readings:** `{"alert_status": "warn"}`  
**Output readings:** `{"alert_status_ok": 0, "alert_status_warn": 1, "alert_status_err": 0}`

## Handling Unknown Values

When a record contains a value not present in the supplied `classes` list the
behaviour depends on the strategy:

| Strategy | Behaviour |
|---|---|
| `label` | The unknown value is appended to the class list and assigned the next available index. |
| `onehot` | All indicator columns for that field are set to `0` (no class is active). |

This only affects the **current batch**; because label maps are not persisted,
the assigned index may differ in a subsequent `transform()` call.  To guarantee
consistent encoding across batches always provide an explicit `classes` list.

## Notes

- Fields not listed in `encodings` are passed through unchanged.
- Label maps are **not** persisted between `transform()` calls; supply `classes`
  for stable cross-batch encoding.
- `errors` in the returned `TransformResult` is always empty; the transformer
  does not silently drop records.
