# RollingTransformer

Computes rolling-window statistics over specified numeric fields in a stream of
`SensorRecord` objects. The transformer maintains an internal buffer per field
and emits a new derived reading alongside the original readings.

## Configuration

```yaml
type: rolling
windows:
  <field_name>:
    size: <int>          # required – number of records in the window (>= 1)
    function: <str>      # optional – one of mean|min|max|sum|count (default: mean)
    output: <str>        # optional – output field name (default: <field>_rolling_<function>)
```

## Supported Functions

| Function | Description                     |
|----------|---------------------------------|
| `mean`   | Arithmetic mean of the window   |
| `min`    | Minimum value in the window     |
| `max`    | Maximum value in the window     |
| `sum`    | Sum of all values in the window |
| `count`  | Number of buffered samples      |

## Example

```python
from agri_etl.transform.rolling_transformer import RollingTransformer

transformer = RollingTransformer({
    "windows": {
        "temperature": {"size": 5, "function": "mean", "output": "temp_avg5"},
        "soil_moisture": {"size": 10, "function": "min"},
    }
})

result = transformer.transform(records)
```

## Behaviour

- The buffer grows up to `size` records and then slides (FIFO).
- If a field is absent or non-numeric for a record, an error entry is appended
  to `TransformResult.errors` and the record is still emitted (without the
  rolling output field for that window).
- All other readings on the record are passed through unchanged.
- State is **persistent across `transform()` calls**, making it suitable for
  incremental / streaming use inside a `Pipeline`.
