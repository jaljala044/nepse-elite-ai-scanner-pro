import tempfile
import unittest
from pathlib import Path

from app.sector_timeline_store import (
    load_sector_timeline_events,
    persist_sector_timeline_batch,
    replay_persisted_sector_timeline,
)

EVENT = {
    "event_id": "sector-event-001",
    "security_id": "SEC-1",
    "symbol": "AAA",
    "event_type": "classify",
    "sector_code": "BANK",
    "effective_from": "2026-01-01",
    "effective_to": None,
    "captured_at": "2026-11-27T10:00:00Z",
    "available_at": "2026-11-27T10:01:00Z",
    "source_id": "source-a",
    "publisher_id": "publisher-a",
    "source_class": "secondary_publisher",
    "evidence_ref": "archive:record-1",
    "payload_sha256": "a" * 64,
}


class SectorTimelineStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "evidence.duckdb"
        self.raw = self.root / "raw"

    def tearDown(self):
        self.tmp.cleanup()

    def persist(self, events=None, batch="batch-001"):
        return persist_sector_timeline_batch(
            events or [EVENT],
            batch_id=batch,
            requested_at_utc="2026-11-28T11:00:00Z",
            received_at_utc="2026-11-28T11:01:00Z",
            storage_root=self.raw,
            database_path=self.db,
        )

    def test_persists_raw_batch_and_provisional_records(self):
        result = self.persist()
        self.assertEqual(result["event_count"], 1)
        loaded = load_sector_timeline_events(database_path=self.db)
        self.assertEqual(loaded["events"], [EVENT])
        self.assertEqual(loaded["finality_status"], "provisional")
        self.assertFalse(result["production_admission_allowed"])

    def test_exact_batch_replay_is_idempotent(self):
        first = self.persist()
        second = self.persist()
        self.assertEqual(first["fetch_id"], second["fetch_id"])
        self.assertEqual(second["status"], "stored_review_required")
        loaded = load_sector_timeline_events(database_path=self.db)
        self.assertEqual(loaded["event_count"], 1)

    def test_duplicate_event_id_in_new_batch_is_rejected(self):
        self.persist()
        with self.assertRaisesRegex(ValueError, "event_id_already_persisted"):
            self.persist(batch="batch-002")

    def test_duplicate_event_id_inside_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_event_id_in_batch"):
            self.persist([EVENT, EVENT])

    def test_batch_id_cannot_be_reused_with_changed_payload(self):
        self.persist()
        changed = {**EVENT, "symbol": "BBB"}
        with self.assertRaisesRegex(ValueError, "different immutable"):
            self.persist([changed])

    def test_replay_uses_point_in_time_timeline_rules(self):
        self.persist()
        result = replay_persisted_sector_timeline(
            as_of_date="2026-11-28",
            decision_time="2026-11-28T12:00:00Z",
            allowed_sector_codes={"BANK"},
            known_security_ids={"SEC-1"},
            database_path=self.db,
        )
        self.assertEqual(result["snapshots"]["SEC-1"]["status"], "single_publisher_only")
        self.assertFalse(result["verified"])
        self.assertFalse(result["production_admission_allowed"])


    def test_invalid_effective_date_is_rejected_before_persistence(self):
        invalid = {**EVENT, "effective_from": "2026-01-01garbage"}
        with self.assertRaisesRegex(ValueError, "effective_from_invalid"):
            self.persist([invalid])

    def test_reversed_effective_interval_is_rejected_before_persistence(self):
        invalid = {**EVENT, "effective_to": "2025-12-31"}
        with self.assertRaisesRegex(ValueError, "effective_to_invalid"):
            self.persist([invalid])

    def test_missing_original_publisher_provenance_is_rejected(self):
        invalid = {**EVENT}
        invalid.pop("publisher_id")
        with self.assertRaisesRegex(ValueError, "publisher_id_required"):
            self.persist([invalid])

    def test_malformed_payload_digest_is_rejected(self):
        invalid = {**EVENT, "payload_sha256": "not-a-digest"}
        with self.assertRaisesRegex(ValueError, "payload_sha256_invalid"):
            self.persist([invalid])

    def test_event_available_after_capture_receipt_is_rejected(self):
        future = {**EVENT, "available_at": "2026-11-29T10:01:00Z"}
        with self.assertRaisesRegex(ValueError, "available_after_batch_receipt"):
            self.persist([future])

    def test_event_available_before_capture_is_rejected(self):
        invalid = {**EVENT, "available_at": "2026-11-27T09:59:00Z"}
        with self.assertRaisesRegex(ValueError, "available_before_capture"):
            self.persist([invalid])

    def test_capture_request_after_receipt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requested_at_after_received_at"):
            persist_sector_timeline_batch(
                [EVENT],
                batch_id="bad-clock",
                requested_at_utc="2026-11-28T11:02:00Z",
                received_at_utc="2026-11-28T11:01:00Z",
                storage_root=self.raw,
                database_path=self.db,
            )

    def test_batch_filter_is_explicit(self):
        self.persist()
        loaded = load_sector_timeline_events(database_path=self.db, batch_id="missing")
        self.assertEqual(loaded["event_count"], 0)


if __name__ == "__main__":
    unittest.main()
