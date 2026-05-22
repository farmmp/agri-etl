from typing import Any
from datetime import datetime, timezone
from collections import defaultdict

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult

SUPPORTED_FUNCTIONS = ("mean", "min", "max", "sum", "count")


class AggregationTransformer(BaseTransformer):
    """Aggregates sensor readings by sensor_id over a rolling window of records.

    Config keys:
        aggregations (dict): mapping of field name -> aggregation function.
            Supported functions: mean, min, max, sum, count.
        window_size (int): number of records to accumulate before emitting
            an aggregated record. Defaults to 10.
    """

    def _validate_config(self) -> None:
        aggs = self.config.get("aggregations")
        if not aggs:
            raise ValueError("AggregationTransformer requires 'aggregations' in config")
        if not isinstance(aggs, dict):
            raise TypeError("'aggregations' must be a dict mapping field -> function")
        for field, func in aggs.items():
            if func not in SUPPORTED_FUNCTIONS:
                raise ValueError(
                    f"Unsupported aggregation function '{func}' for field '{field}'. "
                    f"Choose from: {SUPPORTED_FUNCTIONS}"
                )
        window = self.config.get("window_size", 10)
        if not isinstance(window, int) or window < 1:
            raise ValueError("'window_size' must be a positive integer")

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._window_size: int = self.config.get("window_size", 10)
        self._buckets: dict[str, list[SensorRecord]] = defaultdict(list)

    def transform(self, record: SensorRecord) -> TransformResult:
        sensor_id = record.sensor_id
        self._buckets[sensor_id].append(record)

        if len(self._buckets[sensor_id]) < self._window_size:
            return TransformResult(output=None, dropped=True, drop_reason="window not full")

        window = self._buckets.pop(sensor_id)
        aggs = self.config["aggregations"]
        aggregated: dict[str, Any] = {}

        for field, func in aggs.items():
            values = [
                r.readings[field]
                for r in window
                if field in r.readings and r.readings[field] is not None
            ]
            if not values:
                aggregated[field] = None
                continue
            if func == "mean":
                aggregated[field] = sum(values) / len(values)
            elif func == "min":
                aggregated[field] = min(values)
            elif func == "max":
                aggregated[field] = max(values)
            elif func == "sum":
                aggregated[field] = sum(values)
            elif func == "count":
                aggregated[field] = len(values)

        output = SensorRecord(
            sensor_id=sensor_id,
            timestamp=datetime.now(tz=timezone.utc),
            readings=aggregated,
            metadata={"aggregated_from": self._window_size, "source": sensor_id},
        )
        return TransformResult(output=output, dropped=False)
