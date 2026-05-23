# agri-etl

Modular ETL pipeline framework for ingesting agricultural sensor and weather station data.

## Overview

`agri-etl` provides a composable set of **readers**, **transformers**, and **loaders** that
can be wired together into a `Pipeline` to move data from sensors or weather stations into
any downstream storage or messaging system.

## Quick start

```python
from agri_etl.ingestion import CsvReader
from agri_etl.transform import UnitTransformer, WindowTransformer
from agri_etl.load import CsvLoader
from agri_etl.pipeline import Pipeline

reader = CsvReader({"path": "data/sensors.csv", "sensor_id_col": "id"})
transformers = [
    UnitTransformer({"conversions": {"temp_f": {"operation": "subtract", "value": 32}}}),
    WindowTransformer({"windows": {"temp_f": {"size": 5, "function": "mean"}}}),
]
loader = CsvLoader({"path": "out/processed.csv"})

pipeline = Pipeline(reader=reader, transformers=transformers, loader=loader)
pipeline.run()
```

## Readers

| Class | Source |
|---|---|
| `CsvReader` | Local CSV files |
| `MqttReader` | MQTT broker topics |
| `HttpReader` | REST / JSON endpoints |

## Transformers

| Class | Purpose |
|---|---|
| `UnitTransformer` | Arithmetic unit conversions |
| `FilterTransformer` | Row-level predicate filtering |
| `AggregationTransformer` | Batch aggregation (mean, min, max, …) |
| `RenameTransformer` | Rename reading fields |
| `ClampTransformer` | Clamp values to [min, max] bounds |
| `FillTransformer` | Fill missing values (constant / forward-fill) |
| `RoundTransformer` | Round numeric fields to N decimal places |
| `DropTransformer` | Drop unwanted fields |
| `TimestampTransformer` | Timezone conversion and offset adjustment |
| `SchemaTransformer` | Enforce field presence and ordering |
| `DeduplicateTransformer` | Deduplicate records within a sliding window |
| `NormalizeTransformer` | Min-max normalisation |
| `ZScoreTransformer` | Z-score standardisation |
| `OutlierTransformer` | IQR-based outlier removal |
| `CastTransformer` | Type casting (int, float, str, bool) |
| `TagTransformer` | Inject static metadata tags |
| `ExpressionTransformer` | Evaluate arithmetic expressions to new fields |
| `SplitTransformer` | Split one record into multiple by field mapping |
| `MergeTransformer` | Merge multiple fields into a single field |
| `InterpolateTransformer` | Linear interpolation for missing values |
| `WindowTransformer` | Rolling-window statistics (mean/min/max/sum/count) |

## Loaders

| Class | Destination |
|---|---|
| `CsvLoader` | Local CSV files |
| `PostgresLoader` | PostgreSQL via psycopg2 |
| `MqttLoader` | MQTT broker topics |
| `HttpLoader` | REST endpoints |

## Development

```bash
pip install -e .[dev]
pytest
```

## License

MIT
