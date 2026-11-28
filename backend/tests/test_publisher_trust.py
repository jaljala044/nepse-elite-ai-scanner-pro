import json
import tempfile
import unittest
from pathlib import Path

from app.publisher_trust import (
    assess_publisher_evidence,
    load_evidence_freshness_policy,
    load_publisher_trust_registry,
    sign_trust_payload,
)

KEY = "publisher-trust-test-key-32-characters-minimum"
NOW = "2026-11-28T12:00:00Z"


def signed_attestation(scope, reviewer="reviewer-1"):
    value = {"reviewer_id": reviewer, "reviewed_at": "2026-11-28T10:00:00Z",
             "scope": scope, "decision": "approved"}
    value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
    return value


def registry_fixture():
    entries = [
        {"publisher_id": "pub-a", "ownership_group_id": "group-1",
         "approved_hosts": ["a.example"], "reviewer_attestation": signed_attestation("publisher_identity_and_affiliation")},
        {"publisher_id": "pub-b", "ownership_group_id": "group-1",
         "approved_hosts": ["b.example"], "reviewer_attestation": signed_attestation("publisher_identity_and_affiliation")},
        {"publisher_id": "pub-c", "ownership_group_id": "group-2",
         "approved_hosts": ["c.example"], "reviewer_attestation": signed_attestation("publisher_identity_and_affiliation")},
    ]
    value = {"schema_version": 1, "generated_at": "2026-11-28T11:00:00Z", "publishers": entries}
    value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
    return value


def policy_fixture():
    value = {
        "schema_version": 1, "generated_at": "2026-11-28T11:00:00Z",
        "max_age_seconds": {"secondary_publisher": 86400, "primary_nepse": 3600},
        "reviewer_attestation": signed_attestation("evidence_freshness_policy"),
    }
    value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
    return value


class PublisherTrustTests(unittest.TestCase):
    def load(self, value, loader, filename):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / filename
            path.write_text(json.dumps(value), encoding="utf-8")
            return loader(path, KEY, decision_time=NOW)

    def test_registry_requires_reviewed_publisher_entries(self):
        result = self.load(registry_fixture(), load_publisher_trust_registry, "registry.json")
        self.assertEqual(result["status"], "reviewed_registry_loaded")
        self.assertEqual(result["publishers"]["pub-a"]["ownership_group_id"], "group-1")

    def test_tampered_registry_rejected(self):
        value = registry_fixture()
        value["publishers"][0]["ownership_group_id"] = "fake"
        result = self.load(value, load_publisher_trust_registry, "registry.json")
        self.assertEqual(result["reason"], "registry_signature_invalid")

    def test_duplicate_publisher_id_rejected(self):
        value = registry_fixture()
        value["publishers"].append(value["publishers"][0])
        value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
        result = self.load(value, load_publisher_trust_registry, "registry.json")
        self.assertEqual(result["reason"], "duplicate_publisher_id")

    def test_bad_host_rejected(self):
        value = registry_fixture()
        value["publishers"][0]["approved_hosts"] = ["https://a.example/path"]
        value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
        result = self.load(value, load_publisher_trust_registry, "registry.json")
        self.assertIn("host_invalid", result["reason"])

    def test_future_registry_rejected(self):
        value = registry_fixture()
        value["generated_at"] = "2026-11-29T00:00:00Z"
        value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
        result = self.load(value, load_publisher_trust_registry, "registry.json")
        self.assertEqual(result["reason"], "registry_generated_after_decision_time")

    def test_missing_registry_is_not_configured(self):
        result = load_publisher_trust_registry(None, None, decision_time=NOW)
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(result["independence_assessment_allowed"])

    def test_freshness_policy_requires_review_and_positive_limits(self):
        result = self.load(policy_fixture(), load_evidence_freshness_policy, "policy.json")
        self.assertEqual(result["status"], "reviewed_policy_loaded")
        self.assertEqual(result["max_age_seconds"]["secondary_publisher"], 86400)

    def test_invalid_freshness_policy_rejected(self):
        value = policy_fixture()
        value["max_age_seconds"]["secondary_publisher"] = 0
        value["signature_hmac_sha256"] = sign_trust_payload(value, KEY)
        result = self.load(value, load_evidence_freshness_policy, "policy.json")
        self.assertEqual(result["reason"], "freshness_limit_invalid")

    def test_unconfigured_policy_does_not_call_evidence_fresh(self):
        result = assess_publisher_evidence([], registry={"status": "reviewed_registry_loaded", "publishers": {}},
            freshness_policy={"status": "unconfigured"}, decision_time=NOW)
        self.assertEqual(result["status"], "insufficient_configuration")
        self.assertFalse(result["freshness_assessment_allowed"])

    def test_same_ownership_group_counts_once(self):
        registry = self.load(registry_fixture(), load_publisher_trust_registry, "registry.json")
        policy = self.load(policy_fixture(), load_evidence_freshness_policy, "policy.json")
        rows = [
            {"publisher_id": "pub-a", "source_url": "https://a.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-28T11:30:00Z"},
            {"publisher_id": "pub-b", "source_url": "https://b.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-28T11:30:00Z"},
            {"publisher_id": "pub-c", "source_url": "https://c.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-28T11:30:00Z"},
        ]
        result = assess_publisher_evidence(rows, registry=registry, freshness_policy=policy, decision_time=NOW)
        self.assertEqual(result["eligible_independent_ownership_group_count"], 2)

    def test_unapproved_host_does_not_count(self):
        registry = self.load(registry_fixture(), load_publisher_trust_registry, "registry.json")
        policy = self.load(policy_fixture(), load_evidence_freshness_policy, "policy.json")
        row = {"publisher_id": "pub-a", "source_url": "https://evil.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-28T11:30:00Z"}
        result = assess_publisher_evidence([row], registry=registry, freshness_policy=policy, decision_time=NOW)
        self.assertEqual(result["eligible_independent_ownership_group_count"], 0)

    def test_stale_or_future_capture_is_not_eligible(self):
        registry = self.load(registry_fixture(), load_publisher_trust_registry, "registry.json")
        policy = self.load(policy_fixture(), load_evidence_freshness_policy, "policy.json")
        rows = [
            {"publisher_id": "pub-a", "source_url": "https://a.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-26T00:00:00Z"},
            {"publisher_id": "pub-c", "source_url": "https://c.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-29T00:00:00Z"},
        ]
        result = assess_publisher_evidence(rows, registry=registry, freshness_policy=policy, decision_time=NOW)
        self.assertEqual(result["eligible_independent_ownership_group_count"], 0)

    def test_missing_policy_never_assumes_freshness(self):
        registry = self.load(registry_fixture(), load_publisher_trust_registry, "registry.json")
        row = {"publisher_id": "pub-a", "source_url": "https://a.example/item", "source_class": "secondary_publisher", "captured_at": "2026-11-28T11:30:00Z"}
        result = assess_publisher_evidence([row], registry=registry, freshness_policy={"status": "unconfigured"}, decision_time=NOW)
        self.assertEqual(result["observations"][0]["freshness_status"], "unconfigured")
        self.assertEqual(result["eligible_independent_ownership_group_count"], 0)


if __name__ == "__main__":
    unittest.main()
