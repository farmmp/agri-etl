from typing import Any, Dict, List
from agri_etl.transform.base_transformer import BaseTransformer, TransformResult
from agri_etl.ingestion.base_reader import SensorRecord


class DiffTransformer(BaseTransformer):
    """Computes the difference between consecutive values for specified fields.

    Config keys:
        fields (list[str]): Field names to differentiate.
        order   (int):      Difference order (default 1).
    """

    def _validate_config(self) -> None:
        fields = self.config.get("fields")
        if fields is None:
            raise ValueError("DiffTransformer requires 'fields' in config")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("'fields' must be a non-empty list")
        for f in fields:
            if not isinstance(f, str):
                raise ValueError("Each entry in 'fields' must be a string")
        order = self.config.get("order", 1)
        if not isinstance(order, int) or order < 1:
            raise ValueError("'order' must be a positive integer")

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._order: int = self.config.get("order", 1)
        self._fields: List[str] = self.config["fields"]
        # previous[field] holds a deque of the last `order` values
        self._prev: Dict[str, List[Any]] = {f: [] for f in self._fields}

    def transform(self, records: List[SensorRecord]) -> TransformResult:
        out: List[SensorRecord] = []
        dropped = 0

        for record in records:
            new_data: Dict[str, Any] = dict(record.data)
            skip = False

            for field in self._fields:
                if field not in record.data:
                    continue
                value = record.data[field]
                history = self._prev[field]
                history.append(value)

                if len(history) <= self._order:
                    # Not enough history yet — drop the record
                    skip = True
                    break

                # Compute n-th order finite difference
                diff_vals = list(history[-(self._order + 1):])
                for _ in range(self._order):
                    diff_vals = [
                        diff_vals[i + 1] - diff_vals[i]
                        for i in range(len(diff_vals) - 1)
                    ]
                new_data[field] = diff_vals[0]

                # Keep only what we need
                if len(history) > self._order + 1:
                    self._prev[field] = history[-(self._order + 1):]

            if skip:
                dropped += 1
                continue

            out.append(
                SensorRecord(
                    sensor_id=record.sensor_id,
                    timestamp=record.timestamp,
                    data=new_data,
                    meta=record.meta,
                )
            )

        return TransformResult(records=out, dropped=dropped)
