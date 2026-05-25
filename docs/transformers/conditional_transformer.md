# ConditionalTransformer

Applies a value to an output field based on a boolean condition evaluated
against an existing reading field.

## Config

```yaml
conditions:
  <output_field>:
    field: <source_field>      # reading to evaluate
    op: <operator>             # see supported operators below
    value: <comparison_value>  # right-hand side of comparison
    then: <value_if_true>      # assigned when condition is True
    else: <value_if_false>     # optional; assigned when condition is False
```

### Supported Operators

| op       | meaning                        |
|----------|--------------------------------|
| `eq`     | equal (`==`)                   |
| `ne`     | not equal (`!=`)               |
| `gt`     | greater than (`>`)             |
| `gte`    | greater than or equal (`>=`)   |
| `lt`     | less than (`<`)                |
| `lte`    | less than or equal (`<=`)      |
| `in`     | membership (`in list`)         |
| `not_in` | non-membership (`not in list`) |

## Behaviour

- When the condition evaluates to `True`, `then` is written to `output_field`.
- When the condition evaluates to `False` and `else` is provided, `else` is
  written to `output_field`; otherwise the field is left unchanged.
- If the source `field` is absent from a record, an error is appended to
  `TransformResult.errors` and the record is still emitted (unchanged for
  that output field).
- All other readings are preserved.

## Examples

### Flag high-temperature readings

```python
from agri_etl.transform import ConditionalTransformer

transformer = ConditionalTransformer({
    "conditions": {
        "temp_alert": {
            "field": "temperature_c",
            "op": "gt",
            "value": 35,
            "then": "HIGH",
            "else": "OK",
        }
    }
})
```

### Categorise soil-moisture status

```python
transformer = ConditionalTransformer({
    "conditions": {
        "moisture_status": {
            "field": "soil_moisture",
            "op": "lt",
            "value": 20,
            "then": "DRY",
            "else": "ADEQUATE",
        }
    }
})
```

### Check sensor code membership

```python
transformer = ConditionalTransformer({
    "conditions": {
        "valid_sensor": {
            "field": "sensor_code",
            "op": "in",
            "value": ["S01", "S02", "S03"],
            "then": True,
            "else": False,
        }
    }
})
```
