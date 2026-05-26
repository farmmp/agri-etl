from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from agri_etl.ingestion.base_reader import SensorRecord
from agri_etl.transform.hash_transformer import HashTransformer


def make_record(readings: dict) -> SensorRecord:
    return SensorRecord(
        sensor_id="s1",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        readings=readings,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Init / validation
# ---------------------------------------------------------------------------

class TestHashTransformerInit:
    def test_missing_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty 'fields'"):
            HashTransformer({})

    def test_empty_fields_raises(self):
        with pytest.raises(ValueError, match="non-empty 'fields'"):
            HashTransformer({"fields": {}})

    def test_invalid_fields_type_raises(self):
        with pytest.raises(TypeError, match="must be a dict"):
            HashTransformer({"fields": ["device_id"]})

    def test_unsupported_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            HashTransformer({"fields": {"device_id": "crc32"}})

    def test_valid_config_accepted(self):
        ht = HashTransformer({"fields": {"device_id": "sha256"}})
        assert ht is not None


# ---------------------------------------------------------------------------
# Transform behaviour
# ---------------------------------------------------------------------------

class TestHashTransformerBehaviour:
    def test_md5_hash_applied(self):
        ht = HashTransformer({"fields": {"device_id": "md5"}})
        record = make_record({"device_id": "sensor-42", "temp": 22.5})
        result = ht.transform([record])
        assert len(result.transformed) == 1
        assert len(result.errors) == 0
        expected = hashlib.md5(b"sensor-42").hexdigest()
        assert result.transformed[0].readings["device_id"] == expected

    def test_sha1_hash_applied(self):
        ht = HashTransformer({"fields": {"device_id": "sha1"}})
        record = make_record({"device_id": "abc"})
        result = ht.transform([record])
        expected = hashlib.sha1(b"abc").hexdigest()
        assert result.transformed[0].readings["device_id"] == expected

    def test_sha256_hash_applied(self):
        ht = HashTransformer({"fields": {"device_id": "sha256"}})
        record = make_record({"device_id": "xyz"})
        result = ht.transform([record])
        expected = hashlib.sha256(b"xyz").hexdigest()
        assert result.transformed[0].readings["device_id"] == expected

    def test_prefix_creates_new_field(self):
        ht = HashTransformer({"fields": {"device_id": "md5"}, "prefix": "hashed_"})
        record = make_record({"device_id": "sensor-1", "temp": 10.0})
        result = ht.transform([record])
        r = result.transformed[0].readings
        assert "hashed_device_id" in r
        assert "device_id" not in r
        assert "temp" in r

    def test_missing_field_skipped_gracefully(self):
        ht = HashTransformer({"fields": {"missing_field": "sha256"}})
        record = make_record({"temp": 5.0})
        result = ht.transform([record])
        assert len(result.transformed) == 1
        assert "missing_field" not in result.transformed[0].readings

    def test_non_hashed_fields_preserved(self):
        ht = HashTransformer({"fields": {"device_id": "md5"}})
        record = make_record({"device_id": "s1", "humidity": 60.0, "temp": 25.0})
        result = ht.transform([record])
        r = result.transformed[0].readings
        assert r["humidity"] == 60.0
        assert r["temp"] == 25.0

    def test_multiple_fields_hashed(self):
        ht = HashTransformer({"fields": {"device_id": "md5", "user": "sha1"}})
        record = make_record({"device_id": "d1", "user": "alice", "val": 1})
        result = ht.transform([record])
        r = result.transformed[0].readings
        assert r["device_id"] == hashlib.md5(b"d1").hexdigest()
        assert r["user"] == hashlib.sha1(b"alice").hexdigest()
        assert r["val"] == 1

    def test_empty_batch_returns_empty(self):
        ht = HashTransformer({"fields": {"device_id": "sha256"}})
        result = ht.transform([])
        assert result.transformed == []
        assert result.errors == []
