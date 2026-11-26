import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from app.source_trust_registry import (
    REQUIRED_CHECKS, SourcePolicy, active_promoted_record_ids,
    append_promotion_event, build_promotion_event, build_source_registry,
    verify_promotion_ledger, verify_reviewer_signature, verify_source_registry,
)


class SourceTrustPromotionTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"official-market-record-fixture"
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.key = b"server-held-reviewer-secret-for-tests"
        self.keys = {"reviewer-1": self.key}
        policy = SourcePolicy(
            source_id="nepse-primary-fixture",
            publisher_name="NEPSE primary fixture",
            trust_tier="exchange_primary",
            allowed_record_types=("ohlcv",),
            canonical_record_types=("ohlcv",),
            status="active",
            effective_from="2020-01-01",
            effective_to=None,
            reviewer="registry-reviewer",
            reviewed_at="2026-11-25T10:00:00Z",
            evidence_refs=("evidence://source-identity-review",),
            rights_state="research_only",
        )
        self.registry = build_source_registry([policy])
        self.record = {
            "record_id": "record-001",
            "source_id": "nepse-primary-fixture",
            "record_type": "ohlcv",
            "source_payload_sha256": self.digest,
            "source_row_number": 7,
            "session_date": "2026-11-25",
            "available_at": "2026-11-25T11:00:00Z",
        }
        checks = {name: "passed" for name in REQUIRED_CHECKS["ohlcv"]}
        refs = {name: [f"evidence://independent/{name}"] for name in REQUIRED_CHECKS["ohlcv"]}
        self.validation = {
            "validation_id": "validation-001",
            "reviewer": "reviewer-1",
            "validated_at": "2026-11-26T10:00:00Z",
            "payload_sha256": self.digest,
            "checks": checks,
            "evidence_refs": refs,
            "decision_action": "promote",
            "record_id": self.record["record_id"],
            "source_id": self.record["source_id"],
            "record_type": self.record["record_type"],
            "source_payload_sha256": self.record["source_payload_sha256"],
            "session_date": self.record["session_date"],
            "available_at": self.record["available_at"],
            "registry_sha256": self.registry["registry_sha256"],
            "decision_time": "2026-11-26T12:00:00Z",
        }
        self.sign(self.validation)

    def sign(self, validation):
        unsigned = {key: value for key, value in validation.items() if key != "signature"}
        message = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        validation["signature"] = hmac.new(self.key, message, hashlib.sha256).hexdigest()
        return validation

    def active(self, path):
        return active_promoted_record_ids(
            path, registry=self.registry,
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )

    def event(self, **changes):
        args = dict(
            decision_id="decision-001", action="promote", record=self.record,
            registry=self.registry, raw_payload_sha256=self.digest,
            validation=self.validation, decision_time="2026-11-26T12:00:00Z",
            trusted_registry_sha256=self.registry["registry_sha256"],
            reviewer_keys=self.keys,
        )
        args.update(changes)
        return build_promotion_event(**args)


    def test_checked_in_runtime_registry_is_valid_and_has_no_approved_sources(self):
        registry_path = Path(__file__).resolve().parents[2] / "data" / "reference" / "source-trust-registry.v1.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(registry["sources"], [])
        self.assertTrue(verify_source_registry(
            registry, "8f6a17cf87aa05150ade5c6cc510b72e5d2a5098130021f6a2d2be53762e91fc"
        ))


    def test_registry_digest_cannot_bypass_invalid_policy_schema(self):
        malformed = {
            "schema_version": 1,
            "sources": [{
                "source_id": "untrusted",
                "publisher_name": "Untrusted",
                "trust_tier": "secondary_publisher",
                "allowed_record_types": ["ohlcv"],
                "canonical_record_types": ["ohlcv"],
                "status": "active",
                "effective_from": "2020-01-01",
                "effective_to": None,
                "reviewer": "reviewer",
                "reviewed_at": "2026-11-25T00:00:00Z",
                "evidence_refs": ["evidence://review"],
            }],
        }
        body = json.dumps(malformed, sort_keys=True, separators=(",", ":"))
        malformed["registry_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        self.assertFalse(verify_source_registry(
            malformed, malformed["registry_sha256"]
        ))

    def test_registry_verification_rejects_duplicate_source_ids(self):
        duplicate = json.loads(json.dumps(self.registry))
        duplicate["sources"].append(dict(duplicate["sources"][0]))
        body = {
            "schema_version": duplicate["schema_version"],
            "sources": duplicate["sources"],
        }
        duplicate["registry_sha256"] = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertFalse(verify_source_registry(
            duplicate, duplicate["registry_sha256"]
        ))

    def test_valid_signed_primary_evidence_can_be_promoted(self):
        event = self.event()
        self.assertTrue(event["accepted"])
        self.assertEqual(event["reasons"], [])
        self.assertTrue(verify_source_registry(
            self.registry, self.registry["registry_sha256"]
        ))
        self.assertTrue(verify_reviewer_signature(self.validation, self.keys))

    def test_redistribution_requires_dedicated_rights_evidence(self):
        with self.assertRaisesRegex(ValueError, "dedicated rights_evidence_ref"):
            SourcePolicy(
                source_id="licensed", publisher_name="Licensed",
                trust_tier="official_registry", allowed_record_types=("corporate_action",),
                canonical_record_types=("corporate_action",), status="active",
                effective_from="2020-01-01", effective_to=None,
                reviewer="reviewer", reviewed_at="2026-11-25T00:00:00Z",
                evidence_refs=("evidence://source-review",),
                rights_state="redistribution_permitted", redistribution_allowed=True,
            )

    def test_secondary_publisher_cannot_be_configured_as_canonical(self):
        with self.assertRaisesRegex(ValueError, "only exchange_primary"):
            SourcePolicy(
                source_id="secondary", publisher_name="Secondary",
                trust_tier="secondary_publisher", allowed_record_types=("ohlcv",),
                canonical_record_types=("ohlcv",), status="active",
                effective_from="2020-01-01", effective_to=None,
                reviewer="reviewer", reviewed_at="2026-11-25T00:00:00Z",
                evidence_refs=("evidence://review",),
            )

    def test_unregistered_source_is_rejected(self):
        record = dict(self.record, source_id="unknown-source")
        event = self.event(record=record)
        self.assertFalse(event["accepted"])
        self.assertIn("source_not_registered_or_ambiguous", event["reasons"])

    def test_registry_digest_must_be_pinned(self):
        event = self.event(trusted_registry_sha256="0" * 64)
        self.assertFalse(event["accepted"])
        self.assertIn("source_registry_digest_not_trusted", event["reasons"])

    def test_mutated_registry_fails_digest_check(self):
        changed = dict(self.registry)
        changed["sources"] = list(self.registry["sources"])
        changed["sources"][0] = dict(changed["sources"][0], status="revoked")
        self.assertFalse(verify_source_registry(changed, self.registry["registry_sha256"]))

    def test_unsigned_or_tampered_review_is_rejected(self):
        changed = dict(self.validation)
        changed["checks"] = dict(changed["checks"], price_integrity="failed")
        event = self.event(validation=changed)
        self.assertFalse(event["accepted"])
        self.assertIn("reviewer_signature_invalid_or_untrusted", event["reasons"])

    def test_untrusted_reviewer_key_is_rejected(self):
        event = self.event(reviewer_keys={"other-reviewer": b"other"})
        self.assertFalse(event["accepted"])
        self.assertIn("reviewer_signature_invalid_or_untrusted", event["reasons"])

    def test_missing_independent_check_blocks_promotion(self):
        changed = dict(self.validation)
        changed["checks"] = dict(changed["checks"])
        changed["checks"]["corporate_action_basis"] = "missing"
        self.sign(changed)
        event = self.event(validation=changed)
        self.assertFalse(event["accepted"])
        self.assertIn("required_check_not_passed:corporate_action_basis", event["reasons"])

    def test_missing_check_evidence_reference_blocks_promotion(self):
        changed = dict(self.validation)
        changed["evidence_refs"] = dict(changed["evidence_refs"])
        changed["evidence_refs"]["price_integrity"] = []
        self.sign(changed)
        event = self.event(validation=changed)
        self.assertFalse(event["accepted"])
        self.assertIn("independent_evidence_reference_missing:price_integrity", event["reasons"])

    def test_future_availability_and_validation_are_rejected(self):
        future_record = dict(self.record, available_at="2026-11-26T13:00:00Z")
        event = self.event(record=future_record)
        self.assertFalse(event["accepted"])
        self.assertIn("record_not_available_at_decision_time", event["reasons"])
        future_validation = dict(self.validation, validated_at="2026-11-26T13:00:01Z")
        self.sign(future_validation)
        event = self.event(validation=future_validation)
        self.assertFalse(event["accepted"])
        self.assertIn("validation_occurs_after_decision_time", event["reasons"])

    def test_source_policy_effective_date_is_enforced(self):
        future_record = dict(self.record, session_date="2019-12-31")
        event = self.event(record=future_record)
        self.assertFalse(event["accepted"])
        self.assertIn("source_policy_not_yet_effective_for_session", event["reasons"])

    def test_payload_hash_mismatch_is_rejected(self):
        event = self.event(raw_payload_sha256="0" * 64)
        self.assertFalse(event["accepted"])
        self.assertIn("record_payload_digest_mismatch", event["reasons"])


    def test_invalid_revocation_signature_cannot_revoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "promotion.jsonl"
            append_promotion_event(path, self.event())
            revoke_validation = {
                "validation_id": "revocation-invalid", "reviewer": "reviewer-1",
                "validated_at": "2026-11-26T12:01:00Z",
                "evidence_refs": {"revocation": ["evidence://revocation-case"]},
                "signature": "invalid",
                "decision_action": "revoke",
                "record_id": self.record["record_id"],
                "source_id": self.record["source_id"],
                "record_type": self.record["record_type"],
                "source_payload_sha256": self.record["source_payload_sha256"],
                "session_date": self.record["session_date"],
                "available_at": self.record["available_at"],
                "registry_sha256": self.registry["registry_sha256"],
                "decision_time": "2026-11-26T12:02:00Z",
            }
            revoked = build_promotion_event(
                decision_id="decision-revoke-invalid", action="revoke", record=self.record,
                registry=self.registry, raw_payload_sha256=self.digest,
                validation=revoke_validation, decision_time="2026-11-26T12:02:00Z",
                trusted_registry_sha256=self.registry["registry_sha256"],
                reviewer_keys=self.keys,
            )
            self.assertFalse(revoked["accepted"])
            append_promotion_event(path, revoked)
            self.assertEqual(self.active(path), {"record-001"})

    def test_ledger_chain_append_idempotency_revocation_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "promotion.jsonl"
            promoted = self.event()
            first = append_promotion_event(path, promoted)
            self.assertFalse(first["idempotent"])
            self.assertTrue(append_promotion_event(path, promoted)["idempotent"])
            self.assertEqual(self.active(path), {"record-001"})
            audit = verify_promotion_ledger(path)
            self.assertTrue(audit["valid"])
            revoke_validation = {
                "validation_id": "revocation-001", "reviewer": "reviewer-1",
                "validated_at": "2026-11-26T12:01:00Z",
                "evidence_refs": {"revocation": ["evidence://revocation-case"]},
                "decision_action": "revoke",
                "record_id": self.record["record_id"],
                "source_id": self.record["source_id"],
                "record_type": self.record["record_type"],
                "source_payload_sha256": self.record["source_payload_sha256"],
                "session_date": self.record["session_date"],
                "available_at": self.record["available_at"],
                "registry_sha256": self.registry["registry_sha256"],
                "decision_time": "2026-11-26T12:02:00Z",
            }
            self.sign(revoke_validation)
            revoked = build_promotion_event(
                decision_id="decision-002", action="revoke", record=self.record,
                registry=self.registry, raw_payload_sha256=self.digest,
                validation=revoke_validation, decision_time="2026-11-26T12:02:00Z",
                trusted_registry_sha256=self.registry["registry_sha256"],
                reviewer_keys=self.keys,
            )
            self.assertTrue(revoked["accepted"])
            append_promotion_event(path, revoked)
            self.assertEqual(self.active(path), set())
            lines = path.read_text().splitlines()
            lines[0] = lines[0].replace("record-001", "record-999")
            path.write_text("\n".join(lines) + "\n")
            self.assertFalse(verify_promotion_ledger(path)["valid"])
            with self.assertRaisesRegex(ValueError, "integrity check"):
                self.active(path)


if __name__ == "__main__":
    unittest.main()
