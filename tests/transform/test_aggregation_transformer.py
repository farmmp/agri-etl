import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.aggregation_transformer import AggregationTransformer


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_record(sensor_id: str = "s1", temp: float = 20.0, humidity: float = 50.0) -> SensorRecord:
    return SensorRecord(
        sensor_id=sensor_id,
        timestamp=TS,
        readings={"temperature": temp, "humidity": humidity},
    )


class TestAggregationTransformerInit:
    def test_missing_aggregations_raises(self):
        with pytest.raises(ValueError, match="aggregations"):
            AggregationTransformer({})

    def test_invalid_aggregations_type_raises(self):
        with pytest.raises(TypeError, match="dict"):
            AggregationTransformer({"aggregations": ["mean"]})

    def test_unsupported_function_raises(self):
        with pytest.raises(ValueError, match="Unsupported aggregation function"):
            AggregationTransformer({"aggregations": {"temperature": "median"}})

    def test_invalid_window_size_raises(self):
        with pytest.raises(ValueError, match="window_size"):
            AggregationTransformer({"aggregations": {"temperature": "mean"}, "window_size": 0})

    def test_valid_config_creates_instance(self):
        t = AggregationTransformer({"aggregations": {"temperature": "mean"}, "window_size": 3})
        assert t is not None


class TestAggregationTransformerTransform:
    def _make_transformer(self, func: str = "mean", window: int = 3) -> AggregationTransformer:
        return AggregationTransformer(
            {"aggregations": {"temperature": func, "humidity": func}, "window_size": window}
        )

    def test_drops_record_before_window_full(self):
        t = self._make_transformer(window=3)
        result = t.transform(make_record())
        assert result.dropped is True
        assert result.output is None

    def test_emits_record_when_window_full(self):
        t = self._make_transformer(window=3)
        for _ in range(2):
            t.transform(make_record())
        result = t.transform(make_record())
        assert result.dropped is False
        assert result.output is not None

    def test_mean_aggregation_correct(self):
        t = self._make_transformer(func="mean", window=3)
        temps = [10.0, 20.0, 30.0]
        for temp in temps:
            result = t.transform(make_record(temp=temp))
        assert result.output.readings["temperature"] == pytest.approx(20.0)

    def test_min_aggregation_correct(self):
        t = self._make_transformer(func="min", window=3)
        for temp in [5.0, 15.0, 25.0]:
            result = t.transform(make_record(temp=temp))
        assert result.output.readings["temperature"] == pytest.approx(5.0)

    def test_max_aggregation_correct(self):
        t = self._make_transformer(func="max", window=3)
        for temp in [5.0, 15.0, 25.0]:
            result = t.transform(make_record(temp=temp))
        assert result.output.readings["temperature"] == pytest.approx(25.0)

    def test_sum_aggregation_correct(self):
        t = self._make_transformer(func="sum", window=3)
        for temp in [1.0, 2.0, 3.0]:
            result = t.transform(make_record(temp=temp))
        assert result.output.readings["temperature"] == pytest.approx(6.0)

    def test_count_aggregation_correct(self):
        t = self._make_transformer(func="count", window=3)
        for temp in [1.0, 2.0, 3.0]:
            result = t.transform(make_record(temp=temp))
        assert result.output.readings["temperature"] == 3

    def test_window_resets_after_emit(self):
        t = self._make_transformer(window=2)
        t.transform(make_record())
        t.transform(make_record())  # emits
        result = t.transform(make_record())  # first of new window
        assert result.dropped is True

    def test_separate_buckets_per_sensor(self):
        t = self._make_transformer(window=2)
        t.transform(make_record(sensor_id="s1"))
        t.transform(make_record(sensor_id="s2"))
        r1 = t.transform(make_record(sensor_id="s1"))
        r2 = t.transform(make_record(sensor_id="s2"))
        assert r1.dropped is False and r1.output.sensor_id == "s1"
        assert r2.dropped is False and r2.output.sensor_id == "s2"

    def test_output_metadata_contains_window_size(self):
        t = self._make_transformer(window=3)
        for _ in range(3):
            result = t.transform(make_record())
        assert result.output.metadata["aggregated_from"] == 3
