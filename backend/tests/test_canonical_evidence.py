import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from app.canonical_evidence import load_canonical_evidence_records
from app.evidence_store import load_evidence_record_details, persist_evidence_batch
from app.raw_capture import build_capture_manifest
from app.source_trust_registry import (
    REQUIRED_CHECKS, SourcePolicy, append_promotion_event,
    build_promotion_event, build_source_registry,
)


class CanonicalEvidenceReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "raw"
        self.db = Path(self.tmp.name) / "evidence.duckdb"
        self.ledger = Path(self.tmp.name) / "promotion.jsonl"
        self.payload = b"Date,Symbol,Close\n2026-11-25,NABIL,500\n"
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.source_id = "nepse-primary-fixture"
        self.received_at = "2026-11-26T00:00:02Z"
        manifest = build_capture_manifest(
            self.payload, source_id=self.source_id,
            source_url="https://example.invalid/official-fixture.csv",
            request_method="GET", request_metadata={"fixture": True},
            requested_at="2026-11-26T00:00:00Z",
            received_at=self.received_at,
            claimed_session_date="2026-11-25",
            fetch_id="canonical-fixture-001",
            parser_version="ohlcv-csv-v1", rights_status="research_only",
        )
        records = [{
            "source_row_number": 2, "record_type": "ohlcv",
            "symbol": "NABIL", "session_date": "2026-11-25",
            "close": "500", "available_at": self.received_at,
            "source_validation_status": "verified", "finality_status": "final",
        }]
        persist_evidence_batch(
            self.payload, manifest, records,
            storage_root=self.root, database_path=self.db,
        )
        self.record = load_evidence_record_details(database_path=self.db)[0]
        self.key = b"canonical-reader-reviewer-key"
        self.keys = {"reviewer-1": self.key}
        policy = SourcePolicy(
            source_id=self.source_id, publisher_name="NEPSE primary fixture",
            trust_tier="exchange_primary", allowed_record_types=("ohlcv",),
            canonical_record_types=("ohlcv",), status="active",
            effective_from="2020-01-01", effective_to=None,
            reviewer="registry-reviewer", reviewed_at="2026-11-25T10:00:00Z",
            evidence_refs=("evidence://source-identity-review",),
            rights_state="research_only",
        )
        self.registry = build_source_registry([policy])

    def tearDown(self):
        self.tmp.cleanup()

    def validation(self, action="promote", decision_time="2026-11-26T12:00:00Z"):
        checks = {name: "passed" for name in REQUIRED_CHECKS["ohlcv"]}
        refs = {name: [f"evidence://independent/{name}"] for name in REQUIRED_CHECKS["ohlcv"]}
        packet = {
            "validation_id": f"validation-{action}",
            "reviewer": "reviewer-1",
            "validated_at": "2026-11-26T10:00:00Z",
            "payload_sha256": self.digest,
            "checks": checks,
            "evidence_refs": refs,
            "decision_action": action,
            "record_id": self.record["record_id"],
            "source_id": self.record["source_id"],
            "record_type": self.record["record_type"],
            "source_payload_sha256": self.record["source_payload_sha256"],
            "session_date": self.record["session_date"],
            "available_at": self.record["available_at"],
            "registry_sha256": self.registry["registry_sha256"],
            "decision_time": decision_time,
        }
        unsigned = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
        packet["signature"] = hmac.new(self.key, unsigned, hashlib.sha256).hexdigest()
        return packet

    def promote(self):
        decision_time = "2026-11-26T12:00:00Z"
        packet = self.validation("promote", decision_time)
        event = build_promotion_event(
            decision_id="decision-promote-001", action="promote",
            record=self.record, registry=self.registry,
            raw_payload_sha256=self.digest, validation=packet,
            decision_time=decision_time,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )
        self.assertTrue(event["accepted"])
        append_promotion_event(self.ledger, event)
        return event

    def read(self, **kwargs):
        args = dict(
            database_path=self.db, ledger_path=self.ledger,
            registry=self.registry,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )
        args.update(kwargs)
        return load_canonical_evidence_records(**args)

    def test_unpromoted_bronze_record_is_not_canonical(self):
        result = self.read()
        self.assertEqual(result["status"], "no_canonical_records")
        self.assertFalse(result["canonical_eligible"])
        self.assertEqual(result["promoted_record_count"], 0)
        self.assertEqual(result["withheld_record_count"], 1)
        self.assertEqual(result["records"], [])

    def test_signed_promotion_creates_verified_read_view_without_mutating_bronze(self):
        self.promote()
        result = self.read()
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["canonical_eligible"])
        self.assertEqual(result["promoted_record_count"], 1)
        row = result["records"][0]
        self.assertEqual(row["record_id"], self.record["record_id"])
        self.assertEqual(row["source_validation_status"], "verified")
        self.assertEqual(row["finality_status"], "final")
        self.assertEqual(row["bronze_source_validation_status"], "review_required")
        self.assertEqual(row["bronze_finality_status"], "provisional")
        self.assertTrue(row["canonical_eligible"])
        self.assertNotIn("raw_payload_path", row)
        bronze = load_evidence_record_details(database_path=self.db)[0]
        self.assertEqual(bronze["source_validation_status"], "review_required")
        self.assertEqual(bronze["finality_status"], "provisional")

    def test_raw_object_tampering_blocks_canonical_read(self):
        self.promote()
        Path(self.record["raw_payload_path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "raw payload digest mismatch"):
            self.read()

    def test_ledger_tampering_blocks_canonical_read(self):
        self.promote()
        line = self.ledger.read_text()
        self.ledger.write_text(line.replace(self.record["record_id"], "forged-record-id"))
        with self.assertRaisesRegex(ValueError, "ledger integrity check failed"):
            self.read()

    def test_signed_revocation_removes_record_from_canonical_view(self):
        self.promote()
        decision_time = "2026-11-26T12:02:00Z"
        packet = self.validation("revoke", decision_time)
        event = build_promotion_event(
            decision_id="decision-revoke-001", action="revoke",
            record=self.record, registry=self.registry,
            raw_payload_sha256=self.digest, validation=packet,
            decision_time=decision_time,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )
        self.assertTrue(event["accepted"])
        append_promotion_event(self.ledger, event)
        result = self.read()
        self.assertEqual(result["status"], "no_canonical_records")
        self.assertEqual(result["promoted_record_count"], 0)

    def test_invalid_revocation_cannot_remove_promoted_record(self):
        self.promote()
        decision_time = "2026-11-26T12:02:00Z"
        packet = self.validation("revoke", decision_time)
        packet["signature"] = "invalid"
        event = build_promotion_event(
            decision_id="decision-revoke-invalid", action="revoke",
            record=self.record, registry=self.registry,
            raw_payload_sha256=self.digest, validation=packet,
            decision_time=decision_time,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )
        self.assertFalse(event["accepted"])
        append_promotion_event(self.ledger, event)
        self.assertEqual(self.read()["promoted_record_count"], 1)

    def test_record_type_filter_returns_only_matching_canonical_records(self):
        self.promote()
        result = self.read(record_type="index_ohlcv")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["status"], "no_canonical_records")


if __name__ == "__main__":
    unittest.main()
