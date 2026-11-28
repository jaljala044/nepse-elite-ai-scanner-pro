import json
import tempfile
import unittest
from pathlib import Path

from app.source_quality_review import (
    load_source_quality_review_registry,
    sign_review_attestation,
    sign_review_registry,
    validate_review_attestation,
)

KEY = "unit-test-review-key-with-at-least-32-characters"
NOW = "2026-11-28T12:00:00Z"
REVIEWED = "2026-11-28T10:00:00Z"


def registry_payload(generated_at=REVIEWED):
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "reviewers": [{
            "reviewer_id": "reviewer-1",
            "allowed_scopes": ["calendar_session", "capture_policy"],
            "status": "approved",
        }],
    }


def reviewed_evidence(scope="calendar_session"):
    row = {"date": "2026-11-27", "status": "confirmed_open",
           "review_status": "reviewed", "source_id": "calendar",
           "source_payload_sha256": "a" * 64}
    row["review_attestation"] = sign_review_attestation(
        row, reviewer_id="reviewer-1", scope=scope,
        reviewed_at=REVIEWED, key=KEY,
    )
    return row


class SourceQualityReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "review-registry.json"
        signed = sign_review_registry(registry_payload(), KEY)
        self.path.write_text(json.dumps(signed), encoding="utf-8")
        self.registry = load_source_quality_review_registry(
            self.path, KEY, decision_time=NOW,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_loads_signed_server_owned_reviewer_registry(self):
        self.assertEqual(self.registry["status"], "review_registry_loaded")
        self.assertFalse(self.registry["verified"])

    def test_valid_evidence_attestation_passes(self):
        result = validate_review_attestation(
            reviewed_evidence(), scope="calendar_session",
            registry=self.registry, hmac_key=KEY, decision_time=NOW,
        )
        self.assertTrue(result["eligible"])

    def test_tampered_registry_signature_is_rejected(self):
        self.path.write_text(json.dumps({**registry_payload(), "signature_hmac_sha256": "0" * 64}))
        result = load_source_quality_review_registry(self.path, KEY, decision_time=NOW)
        self.assertEqual(result["status"], "rejected")

    def test_future_registry_is_rejected_for_historical_cutoff(self):
        future = sign_review_registry(registry_payload("2026-11-29T00:00:00Z"), KEY)
        self.path.write_text(json.dumps(future))
        result = load_source_quality_review_registry(self.path, KEY, decision_time=NOW)
        self.assertEqual(result["status"], "rejected")

    def test_missing_registry_fails_closed(self):
        result = load_source_quality_review_registry(None, KEY, decision_time=NOW)
        self.assertEqual(result["status"], "not_configured")

    def test_reviewer_scope_is_enforced(self):
        restricted = dict(self.registry)
        restricted["reviewers"] = {"reviewer-1": {
            "allowed_scopes": ["calendar_session"], "status": "approved",
        }}
        result = validate_review_attestation(
            reviewed_evidence("capture_policy"), scope="capture_policy",
            registry=restricted, hmac_key=KEY, decision_time=NOW,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "reviewer_scope_not_approved")

    def test_future_review_attestation_is_rejected(self):
        row = {"date": "2026-11-27"}
        row["review_attestation"] = sign_review_attestation(
            row, reviewer_id="reviewer-1", scope="calendar_session",
            reviewed_at="2026-11-29T00:00:00Z", key=KEY,
        )
        result = validate_review_attestation(
            row, scope="calendar_session", registry=self.registry,
            hmac_key=KEY, decision_time=NOW,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "review_attestation_after_decision_time")

    def test_evidence_mutation_invalidates_attestation(self):
        row = reviewed_evidence()
        row["source_id"] = "tampered"
        result = validate_review_attestation(
            row, scope="calendar_session", registry=self.registry,
            hmac_key=KEY, decision_time=NOW,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "reviewed_evidence_payload_hash_mismatch")

    def test_attestation_signature_is_verified(self):
        row = reviewed_evidence()
        row["review_attestation"]["signature_hmac_sha256"] = "0" * 64
        result = validate_review_attestation(
            row, scope="calendar_session", registry=self.registry,
            hmac_key=KEY, decision_time=NOW,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "review_attestation_signature_invalid")

    def test_registry_requires_long_hmac_key(self):
        result = load_source_quality_review_registry(self.path, "short", decision_time=NOW)
        self.assertEqual(result["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
