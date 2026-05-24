import pytest
from datetime import datetime, timezone

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.encode_transformer import EncodeTransformer


TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=TS,
        readings=readings,
        meta={},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestEncodeTransformerInit:
    def test_missing_encodings_raises(self):
        with pytest.raises(ValueError, match="encodings"):
            EncodeTransformer({})

    def test_empty_encodings_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            EncodeTransformer({"encodings": {}})

    def test_invalid_encodings_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            EncodeTransformer({"encodings": ["label"]})

    def test_unsupported_strategy_raises(self):
        with pytest.raises(ValueError, match="Unsupported encoding strategy"):
            EncodeTransformer({"encodings": {"soil_type": "binary"}})

    def test_invalid_spec_type_raises(self):
        with pytest.raises(TypeError, match="must be a str or dict"):
            EncodeTransformer({"encodings": {"soil_type": 42}})

    def test_valid_label_strategy_accepted(self):
        t = EncodeTransformer({"encodings": {"soil_type": "label"}})
        assert t is not None

    def test_valid_onehot_strategy_accepted(self):
        t = EncodeTransformer({"encodings": {"soil_type": "onehot"}})
        assert t is not None

    def test_valid_dict_spec_accepted(self):
        t = EncodeTransformer(
            {"encodings": {"soil_type": {"strategy": "label", "classes": ["clay", "sand"]}}}
        )
        assert t is not None


# ---------------------------------------------------------------------------
# Label encoding
# ---------------------------------------------------------------------------

class TestLabelEncoding:
    def test_label_encodes_in_encounter_order(self):
        t = EncodeTransformer({"encodings": {"soil": "label"}})
        records = [
            make_record({"soil": "clay"}),
            make_record({"soil": "sand"}),
            make_record({"soil": "clay"}),
        ]
        result = t.transform(records)
        assert result.errors == []
        values = [r.readings["soil"] for r in result.records]
        assert values == [0, 1, 0]

    def test_label_respects_fixed_classes(self):
        t = EncodeTransformer(
            {"encodings": {"soil": {"strategy": "label", "classes": ["sand", "clay", "silt"]}}}
        )
        records = [make_record({"soil": "clay"}), make_record({"soil": "sand"})]
        result = t.transform(records)
        values = [r.readings["soil"] for r in result.records]
        assert values == [1, 0]

    def test_unencoded_fields_pass_through(self):
        t = EncodeTransformer({"encodings": {"soil": "label"}})
        record = make_record({"soil": "clay", "temperature": 22.5})
        result = t.transform([record])
        assert result.records[0].readings["temperature"] == 22.5


# ---------------------------------------------------------------------------
# One-hot encoding
# ---------------------------------------------------------------------------

class TestOneHotEncoding:
    def test_onehot_expands_field(self):
        t = EncodeTransformer(
            {"encodings": {"status": {"strategy": "onehot", "classes": ["ok", "warn", "err"]}}}
        )
        record = make_record({"status": "warn"})
        result = t.transform([record])
        r = result.records[0].readings
        assert r["status_ok"] == 0
        assert r["status_warn"] == 1
        assert r["status_err"] == 0
        assert "status" not in r

    def test_onehot_no_errors_on_valid_input(self):
        t = EncodeTransformer(
            {"encodings": {"zone": {"strategy": "onehot", "classes": ["A", "B"]}}}
        )
        records = [make_record({"zone": "A"}), make_record({"zone": "B"})]
        result = t.transform(records)
        assert result.errors == []
        assert len(result.records) == 2
