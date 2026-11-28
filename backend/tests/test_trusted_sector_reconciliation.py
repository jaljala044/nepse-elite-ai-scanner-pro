import json
import tempfile
import unittest
from pathlib import Path

from app.publisher_trust import sign_trust_payload
from app.trusted_sector_reconciliation import (
    publisher_trust_readiness,
    reconcile_trusted_sector_evidence,
)

KEY = "trusted-sector-integration-test-key-32chars"
NOW = "2026-11-28T12:00:00Z"


def attestation(scope):
    row = {"reviewer_id": "reviewer-1", "reviewed_at": "2026-11-28T10:00:00Z",
           "scope": scope, "decision": "approved"}
    row["signature_hmac_sha256"] = sign_trust_payload(row, KEY)
    return row


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def config(root):
    registry = {
        "schema_version": 1, "generated_at": "2026-11-28T11:00:00Z",
        "publishers": [
            {"publisher_id": "brand-a", "ownership_group_id": "group-one",
             "approved_hosts": ["a.example"], "reviewer_attestation": attestation("publisher_identity_and_affiliation")},
            {"publisher_id": "brand-b", "ownership_group_id": "group-one",
             "approved_hosts": ["b.example"], "reviewer_attestation": attestation("publisher_identity_and_affiliation")},
            {"publisher_id": "brand-c", "ownership_group_id": "group-two",
             "approved_hosts": ["c.example"], "reviewer_attestation": attestation("publisher_identity_and_affiliation")},
        ],
    }
    registry["signature_hmac_sha256"] = sign_trust_payload(registry, KEY)
    policy = {
        "schema_version": 1, "generated_at": "2026-11-28T11:00:00Z",
        "max_age_seconds": {"secondary_publisher": 86400},
        "reviewer_attestation": attestation("evidence_freshness_policy"),
    }
    policy["signature_hmac_sha256"] = sign_trust_payload(policy, KEY)
    rp, pp = root / "registry.json", root / "policy.json"
    write_json(rp, registry)
    write_json(pp, policy)
    return rp, pp


def observation(publisher, host, symbol="AAA", sector="BANK"):
    return {
        "symbol": symbol, "sector_code": sector, "source_id": "src-" + publisher,
        "publisher_id": publisher, "source_class": "secondary_publisher",
        "source_url": "https://" + host + "/record/1",
        "payload_sha256": "a" * 64, "source_record_ref": "archive:" + publisher,
        "captured_at": "2026-11-28T11:30:00Z", "available_at": "2026-11-28T11:31:00Z",
        "effective_from": "2026-01-01", "effective_to": None,
    }


class TrustedSectorIntegrationTests(unittest.TestCase):
    def test_related_publisher_brands_count_as_one_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, pp = config(root)
            rows = [observation("brand-a", "a.example"), observation("brand-b", "b.example")]
            result = reconcile_trusted_sector_evidence(
                rows, symbols=["AAA"], allowed_sector_codes={"BANK"},
                as_of_date="2026-11-28", decision_time=NOW,
                registry_path=rp, freshness_policy_path=pp, hmac_key=KEY,
            )
            self.assertEqual(result["results"]["AAA"]["status"], "single_source_only")
            self.assertEqual(result["results"]["AAA"]["independent_ownership_group_count"], 1)

    def test_two_distinct_reviewed_groups_can_corroborate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, pp = config(root)
            rows = [observation("brand-a", "a.example"), observation("brand-c", "c.example")]
            result = reconcile_trusted_sector_evidence(
                rows, symbols=["AAA"], allowed_sector_codes={"BANK"},
                as_of_date="2026-11-28", decision_time=NOW,
                registry_path=rp, freshness_policy_path=pp, hmac_key=KEY,
            )
            self.assertEqual(result["results"]["AAA"]["status"], "corroborated_secondary")
            self.assertEqual(result["results"]["AAA"]["independent_ownership_group_count"], 2)

    def test_unknown_host_rejected_from_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, pp = config(root)
            result = reconcile_trusted_sector_evidence(
                [observation("brand-a", "attacker.example")], symbols=["AAA"],
                allowed_sector_codes={"BANK"}, as_of_date="2026-11-28",
                decision_time=NOW, registry_path=rp, freshness_policy_path=pp, hmac_key=KEY,
            )
            self.assertEqual(result["results"]["AAA"]["status"], "missing_evidence")
            self.assertEqual(result["publisher_trust"]["rejected_observation_count"], 1)

    def test_missing_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, _ = config(root)
            result = reconcile_trusted_sector_evidence(
                [observation("brand-a", "a.example"), observation("brand-c", "c.example")],
                symbols=["AAA"], allowed_sector_codes={"BANK"}, as_of_date="2026-11-28",
                decision_time=NOW, registry_path=rp, freshness_policy_path=None, hmac_key=KEY,
            )
            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertEqual(result["results"]["AAA"]["status"], "missing_evidence")

    def test_stale_source_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, pp = config(root)
            old = observation("brand-a", "a.example")
            old["captured_at"] = "2026-11-25T11:30:00Z"
            result = reconcile_trusted_sector_evidence(
                [old], symbols=["AAA"], allowed_sector_codes={"BANK"},
                as_of_date="2026-11-28", decision_time=NOW,
                registry_path=rp, freshness_policy_path=pp, hmac_key=KEY,
            )
            self.assertEqual(result["results"]["AAA"]["status"], "missing_evidence")

    def test_conflicting_sectors_remain_withheld(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rp, pp = config(root)
            rows = [observation("brand-a", "a.example", sector="BANK"),
                    observation("brand-c", "c.example", sector="HYDRO")]
            result = reconcile_trusted_sector_evidence(
                rows, symbols=["AAA"], allowed_sector_codes={"BANK", "HYDRO"},
                as_of_date="2026-11-28", decision_time=NOW,
                registry_path=rp, freshness_policy_path=pp, hmac_key=KEY,
            )
            self.assertEqual(result["results"]["AAA"]["status"], "conflicting_sources")
            self.assertIsNone(result["results"]["AAA"]["sector_code"])

    def test_readiness_reports_unconfigured_without_secrets(self):
        result = publisher_trust_readiness(
            registry_path=None, freshness_policy_path=None, hmac_key=None,
            decision_time=NOW,
        )
        self.assertEqual(result["status"], "not_configured_or_invalid")
        self.assertFalse(result["production_admission_allowed"])


if __name__ == "__main__":
    unittest.main()
