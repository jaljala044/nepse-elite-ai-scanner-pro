import csv
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from app.canonical_evidence import load_canonical_evidence_records
from app.canonical_feature_pipeline import build_canonical_feature_snapshot
from app.evidence_store import load_evidence_record_details, persist_evidence_batch
from app.raw_capture import build_capture_manifest
from app.source_trust_registry import (
    SourcePolicy, _validation_signature_payload, append_promotion_event,
    build_promotion_event, build_source_registry, verify_promotion_ledger,
)


class CanonicalScannerBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.raw = root / "raw"
        self.db = root / "evidence.duckdb"
        self.ledger = root / "promotion-ledger.jsonl"
        self.calendar = root / "calendar.csv"
        self.payload = b'{"symbol":"AAA","date":"2026-11-25","close":101}'
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.received = "2026-11-26T00:00:02Z"
        manifest = build_capture_manifest(
            self.payload, source_id="nepse-official-prices",
            source_url="https://nepalstock.com.np/api/prices",
            request_method="GET", request_metadata={"test": True},
            requested_at="2026-11-26T00:00:00Z", received_at=self.received,
            claimed_session_date="2026-11-25", fetch_id="fetch-001",
            parser_version="test-parser-v1", rights_status="research_only",
        )
        record = {
            "source_row_number": 1, "record_type": "ohlcv", "symbol": "AAA",
            "session_date": "2026-11-25", "open": 100, "high": 103,
            "low": 99, "close": 101, "previous_close": 100, "volume": 1000,
            "price_basis_status": "verified_unadjusted_no_actions",
            "corporate_action_status": "clear",
        }
        persist_evidence_batch(self.payload, manifest, [record], storage_root=self.raw, database_path=self.db)
        self.record = load_evidence_record_details(database_path=self.db)[0]
        policy = SourcePolicy(
            source_id="nepse-official-prices", publisher_name="NEPSE",
            trust_tier="exchange_primary", allowed_record_types=("ohlcv",),
            canonical_record_types=("ohlcv",), status="active",
            effective_from="2026-01-01", effective_to=None, reviewer="registry-reviewer",
            reviewed_at="2026-11-25T00:00:00Z", evidence_refs=("official-source-policy",),
        )
        self.registry = build_source_registry([policy])
        self.reviewer_keys = {"reviewer-1": b"unit-test-reviewer-secret"}
        self.decision_time = "2026-11-26T00:02:00Z"
        checks = {
            "payload_integrity", "source_identity", "schema_mapping",
            "instrument_identity", "session_calendar", "point_in_time",
            "corporate_action_basis", "price_integrity", "exchange_finality",
        }
        validation = {
            "validation_id": "validation-001", "reviewer": "reviewer-1",
            "validated_at": "2026-11-26T00:01:00Z", "payload_sha256": self.digest,
            "checks": {key: "passed" for key in checks},
            "evidence_refs": {key: ["independent-evidence-ref"] for key in checks},
        }
        validation["signature"] = hmac.new(
            self.reviewer_keys["reviewer-1"], _validation_signature_payload(validation),
            hashlib.sha256,
        ).hexdigest()
        self.validation = validation
        promoted_record = dict(self.record)
        self.event = build_promotion_event(
            decision_id="decision-promote-001", action="promote",
            record=promoted_record, registry=self.registry,
            raw_payload_sha256=self.digest, validation=validation,
            decision_time=self.decision_time,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys,
        )
        self.assertTrue(self.event["accepted"], self.event["reasons"])
        append_promotion_event(self.ledger, self.event)
        with self.calendar.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date","status","source_id","evidence_uri","raw_evidence_sha256",
                "published_at","retrieved_at_utc","verified_at_utc","scope","notes",
            ])
            writer.writeheader()
            writer.writerow({
                "date":"2026-11-25","status":"verified_open",
                "source_id":"nepse-calendar","evidence_uri":"https://nepalstock.com.np/notices/1",
                "raw_evidence_sha256":"a"*64,"published_at":"2026-11-25T00:00:00Z",
                "retrieved_at_utc":"2026-11-25T12:00:00Z",
                "verified_at_utc":"2026-11-25T12:01:00Z",
                "scope":"all_securities","notes":"verified fixture",
            })
        self.calendar_digest = hashlib.sha256(self.calendar.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return load_canonical_evidence_records(
            database_path=self.db, ledger_path=self.ledger,
            registry=self.registry, trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys, decision_time=self.decision_time,
        )

    def test_promoted_record_reaches_feature_pipeline(self):
        result = build_canonical_feature_snapshot(
            database_path=self.db, ledger_path=self.ledger, registry=self.registry,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys, calendar_path=self.calendar,
            trusted_calendar_sha256=self.calendar_digest,
            decision_time=self.decision_time, expected_symbols=["AAA"],
        )
        self.assertEqual(result["status"], "ready")
        features = result["feature_snapshot"]
        self.assertEqual(features["security_features"]["AAA"]["close"], 101)
        self.assertTrue(features["input_contracts"]["ohlcv"]["score_eligible"])
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertFalse(result["production_source_claim"])

    def test_bronze_provisional_record_without_promotion_is_not_fallback_input(self):
        self.ledger.unlink()
        result = build_canonical_feature_snapshot(
            database_path=self.db, ledger_path=self.ledger, registry=self.registry,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys, calendar_path=self.calendar,
            trusted_calendar_sha256=self.calendar_digest,
            decision_time=self.decision_time, expected_symbols=["AAA"],
        )
        self.assertEqual(result["decision_status"], "UNKNOWN")
        self.assertEqual(result["action"], "PRESERVE_CAPITAL")
        self.assertIsNone(result["feature_snapshot"])

    def test_accepted_signed_revocation_removes_record_from_next_read(self):
        revoke_validation = {
            "validation_id": "validation-revoke-001", "reviewer": "reviewer-1",
            "evidence_refs": {"revocation_basis": ["independent-revocation-evidence"]},
            "validated_at": "2026-11-26T00:03:00Z",
        }
        revoke_validation["signature"] = hmac.new(
            self.reviewer_keys["reviewer-1"], _validation_signature_payload(revoke_validation),
            hashlib.sha256,
        ).hexdigest()
        revoked = build_promotion_event(
            decision_id="decision-revoke-001", action="revoke",
            record=self.record, registry=self.registry, raw_payload_sha256=self.digest,
            validation=revoke_validation, decision_time="2026-11-26T00:04:00Z",
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys,
        )
        self.assertTrue(revoked["accepted"], revoked["reasons"])
        append_promotion_event(self.ledger, revoked)
        self.assertEqual(self.load()["records"], [])

    def test_unsigned_revocation_cannot_remove_active_promotion(self):
        invalid = build_promotion_event(
            decision_id="decision-revoke-invalid", action="revoke",
            record=self.record, registry=self.registry, raw_payload_sha256=self.digest,
            validation={"reviewer":"reviewer-1","validation_id":"bad","evidence_refs":{"basis":["x"]}},
            decision_time="2026-11-26T00:04:00Z",
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys,
        )
        self.assertFalse(invalid["accepted"])
        append_promotion_event(self.ledger, invalid)
        self.assertEqual(len(self.load()["records"]), 1)

    def test_raw_payload_digest_mismatch_fails_closed(self):
        Path(self.record["raw_payload_path"]).write_bytes(b"tampered bytes")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.load()

    def test_missing_calendar_keeps_scanner_unknown(self):
        self.calendar.unlink()
        result = build_canonical_feature_snapshot(
            database_path=self.db, ledger_path=self.ledger, registry=self.registry,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.reviewer_keys, calendar_path=self.calendar,
            trusted_calendar_sha256=self.calendar_digest,
            decision_time=self.decision_time, expected_symbols=["AAA"],
        )
        self.assertEqual(result["decision_status"], "UNKNOWN")
        self.assertEqual(result["action"], "PRESERVE_CAPITAL")
        self.assertIsNone(result["feature_snapshot"])


if __name__ == "__main__":
    unittest.main()
