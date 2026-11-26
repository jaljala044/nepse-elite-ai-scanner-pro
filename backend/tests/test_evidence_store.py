import hashlib
import tempfile
import unittest
from pathlib import Path

from app.evidence_store import load_evidence_records, persist_evidence_batch
from app.raw_capture import build_capture_manifest


class EvidenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "raw"
        self.db = Path(self.tmp.name) / "evidence.duckdb"
        self.payload = b"symbol,session_date,close\nNABIL,2026-11-25,500\n"
        self.manifest = build_capture_manifest(
            self.payload,
            source_id="secondary-example",
            source_url="https://example.invalid/ohlcv.csv",
            request_method="GET",
            request_metadata={"fixture": True},
            requested_at="2026-11-26T00:00:00Z",
            received_at="2026-11-26T00:00:02Z",
            claimed_session_date="2026-11-25",
            fetch_id="fixture-fetch-001",
            parser_version="ohlcv-csv-v1",
            rights_status="unknown",
        )
        self.records = [{
            "source_row_number": 2,
            "record_type": "ohlcv",
            "symbol": "NABIL",
            "session_date": "2026-11-25",
            "close": "500",
            # Deliberately hostile claims: the store must overwrite these.
            "source_validation_status": "verified",
            "finality_status": "final",
            "available_at": "2026-11-26T00:00:02Z",
        }]

    def tearDown(self):
        self.tmp.cleanup()

    def persist(self, records=None, manifest=None):
        return persist_evidence_batch(
            self.payload, manifest or self.manifest, self.records if records is None else records,
            storage_root=self.root, database_path=self.db,
        )

    def test_round_trip_preserves_payload_hash_lineage_and_forces_provisional(self):
        result = self.persist()
        rows = load_evidence_records(database_path=self.db)
        self.assertEqual(result["payload_sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_id"], "secondary-example")
        self.assertEqual(rows[0]["source_payload_sha256"], result["payload_sha256"])
        self.assertEqual(rows[0]["source_row_number"], 2)
        self.assertEqual(rows[0]["available_at"], "2026-11-26T00:00:02Z")
        self.assertEqual(rows[0]["source_validation_status"], "review_required")
        self.assertEqual(rows[0]["finality_status"], "provisional")
        self.assertFalse(result["production_eligible"])
        self.assertEqual(Path(result["raw_object_path"]).read_bytes(), self.payload)

    def test_exact_reimport_is_idempotent(self):
        first = self.persist()
        second = self.persist()
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(len(load_evidence_records(database_path=self.db)), 1)

    def test_payload_hash_mismatch_rejected_before_storage(self):
        bad = dict(self.manifest)
        bad["payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match exact payload"):
            self.persist(manifest=bad)

    def test_future_available_at_rejected(self):
        rows = [dict(self.records[0], available_at="2026-11-26T00:00:03Z")]
        with self.assertRaisesRegex(ValueError, "cannot follow capture receipt"):
            self.persist(records=rows)

    def test_duplicate_source_row_number_rejected(self):
        rows = self.records + [dict(self.records[0], symbol="NICA")]
        with self.assertRaisesRegex(ValueError, "duplicate source_row_number"):
            self.persist(records=rows)

    def test_unsupported_record_type_rejected(self):
        rows = [dict(self.records[0], record_type="made_up")]
        with self.assertRaisesRegex(ValueError, "unsupported record_type"):
            self.persist(records=rows)

    def test_verified_only_query_returns_nothing_until_separate_promotion(self):
        self.persist()
        self.assertEqual(load_evidence_records(database_path=self.db, include_provisional=False), [])


if __name__ == "__main__":
    unittest.main()
