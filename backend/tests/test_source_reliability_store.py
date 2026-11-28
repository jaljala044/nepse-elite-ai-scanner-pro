import tempfile
import unittest
from pathlib import Path

from app.source_reliability_store import (
    load_source_reliability_events, persist_source_reliability_batch,
    source_reliability_readiness,
)

CAPTURED = "2026-11-28T10:00:00Z"
RECEIVED = "2026-11-28T10:05:00Z"


def make_event(event_id="evt-1", event_type="source_registered", **extra):
    return {
        "event_id": event_id, "source_id": "sharesansar", "event_type": event_type,
        "effective_date": "2026-11-27", "captured_at": "2026-11-28T10:01:00Z",
        "available_at": "2026-11-28T10:02:00Z", **extra,
    }


class SourceReliabilityStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "evidence.duckdb"
        self.raw = self.root / "raw"

    def tearDown(self):
        self.tmp.cleanup()

    def persist(self, events=None, batch="source-batch-1"):
        return persist_source_reliability_batch(
            events or [make_event()], batch_id=batch, captured_at=CAPTURED,
            received_at=RECEIVED, storage_root=self.raw, database_path=self.db,
        )

    def test_persists_and_loads_provisional_event(self):
        result = self.persist()
        loaded = load_source_reliability_events(database_path=self.db)
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(loaded["events"][0]["event_id"], "evt-1")
        self.assertEqual(loaded["finality_status"], "provisional")
        self.assertFalse(loaded["production_admission_allowed"])

    def test_exact_retry_is_idempotent(self):
        first, second = self.persist(), self.persist()
        self.assertEqual(first["fetch_id"], second["fetch_id"])
        self.assertEqual(load_source_reliability_events(database_path=self.db)["event_count"], 1)

    def test_changed_batch_payload_is_rejected(self):
        self.persist()
        with self.assertRaisesRegex(ValueError, "different immutable"):
            self.persist([make_event(extra_field="changed")])

    def test_duplicate_event_across_batches_is_rejected_by_event_manifest_store(self):
        self.persist()
        # Batch-level IDs differ, so store rejects event identity duplication.
        with self.assertRaisesRegex(ValueError, "different immutable|event_id"):
            self.persist(batch="source-batch-2")

    def test_readiness_does_not_create_missing_database(self):
        missing = self.root / "absent.duckdb"
        result = source_reliability_readiness(database_path=missing,
            decision_time="2026-11-28T12:00:00Z")
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(missing.exists())
        self.assertFalse(result["production_admission_allowed"])

    def test_readiness_replays_persisted_events_without_promoting(self):
        self.persist()
        result = source_reliability_readiness(database_path=self.db,
            decision_time="2026-11-28T12:00:00Z", expected_source_ids=["sharesansar", "punji"])
        self.assertEqual(result["status"], "assessed")
        self.assertEqual(result["persisted_event_count"], 1)
        self.assertEqual(result["missing_expected_sources"], ["punji"])
        self.assertFalse(result["production_admission_allowed"])
        self.assertFalse(result["recommendation_override"])

    def test_verified_calendar_required_for_session_coverage(self):
        self.persist()
        result = source_reliability_readiness(database_path=self.db,
            decision_time="2026-11-28T12:00:00Z")
        self.assertEqual(result["session_calendar_status"], "not_configured")
        self.assertIsNone(result["sources"]["sharesansar"]["session_coverage"])


if __name__ == "__main__":
    unittest.main()
