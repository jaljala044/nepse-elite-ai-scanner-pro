import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.idpat_trusted_gate_bridge import (
    REQUIRED_ARTIFACTS, derive_idpat_gates_from_trusted_store,
)
from app.trusted_artifact_store import TrustedArtifactStore


CUTOFF_DATE = "2026-11-27"
CUTOFF_TIME = "2026-11-27T16:00:00+05:45"


def artifact_payload(module):
    fields = {
        "market_health": {"calendar_status": "verified", "market_summary_finality_verified": True},
        "index_intelligence": {"index_integrity_status": "passed"},
        "sector_rotation": {"membership_status": "verified", "sector_data_status": "verified",
                            "price_coverage_ratio": 0.99},
        "broker_profiles": {"reconciliation_status": "passed", "verified_amount_coverage": 0.97},
        "broker_sector_rotation": {"identity_policy_status": "passed"},
        "ohlcv_quality": {"ohlcv_integrity_status": "passed", "per_security_coverage_ratio": 0.99},
        "turnover_quality": {"turnover_status": "verified"},
        "execution_readiness": {"session_calendar_status": "verified",
                                "execution_constraints_status": "verified",
                                "next_session_history_complete": True},
        "corporate_actions": {"registry_status": "verified",
                              "source_universe_completeness_verified": True,
                              "point_in_time_eligible": True},
        "source_quality": {"raw_hashes_verified": True, "lineage_complete": True,
                           "rights_clearance": True, "unresolved_conflict_count": 0},
    }
    return fields[module]


class IDPATTrustedGateBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = {}
        for module in REQUIRED_ARTIFACTS:
            payload = json.dumps(artifact_payload(module), sort_keys=True).encode()
            path = self.root / (module + ".json")
            path.write_bytes(payload)
            entry = {
                "source_id": "SRC-" + module,
                "payload_path": path.name,
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "evidence_ids": ["EV-" + module],
                "as_of_date": CUTOFF_DATE,
                "available_at": "2026-11-27T15:00:00+05:45",
                "status": "research_only",
                "coverage_ratio": 0.99,
                "source_validation_status": "verified",
                "finality_status": "final",
                "session_calendar_id": "NEPSE-CALENDAR-REVIEW-v1",
                "corporate_action_status": "verified",
                "sector_membership_status": "verified",
                "sector_membership_version": "sector-membership-review-v1",
                "broker_code_mapping_status": "verified",
                "broker_identity_coverage_ratio": 0.97,
            }
            self.registry[module] = entry
        self.store = TrustedArtifactStore(self.root, self.registry, max_age_days=7)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_seven_gates_derive_from_pinned_server_artifacts(self):
        result = derive_idpat_gates_from_trusted_store(
            self.store, decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)
        self.assertEqual(result["status"], "ready_for_research_review")
        self.assertEqual(len(result["gate_evidence"]), 7)
        self.assertFalse(result["production_enabled"])
        self.assertEqual(len(result["lineage"]), 7)

    def test_missing_broker_artifact_blocks_only_broker_gate(self):
        del self.registry["broker_profiles"]
        result = derive_idpat_gates_from_trusted_store(
            self.store, decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("broker", result["artifact_rejections"])
        self.assertNotIn("broker", result["gate_evidence"])

    def test_payload_hash_mismatch_blocks_market_gate(self):
        self.registry["market_health"]["payload_sha256"] = "0" * 64
        result = derive_idpat_gates_from_trusted_store(
            self.store, decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)
        self.assertIn("market", result["artifact_rejections"])
        self.assertNotIn("market", result["gate_evidence"])

    def test_late_artifact_blocks_its_gate(self):
        self.registry["execution_readiness"]["available_at"] = "2026-11-27T16:01:00+05:45"
        result = derive_idpat_gates_from_trusted_store(
            self.store, decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)
        self.assertIn("execution", result["artifact_rejections"])
        self.assertNotIn("execution", result["gate_evidence"])

    def test_failed_gate_field_blocks_gate_even_with_valid_hash(self):
        payload = json.dumps({"ohlcv_integrity_status": "failed",
                               "per_security_coverage_ratio": 1.0}, sort_keys=True).encode()
        path = self.root / "ohlcv_quality.json"
        path.write_bytes(payload)
        self.registry["ohlcv_quality"]["payload_sha256"] = hashlib.sha256(payload).hexdigest()
        result = derive_idpat_gates_from_trusted_store(
            self.store, decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)
        self.assertIn("liquidity", result["blocked_gates"][0] if result["blocked_gates"] else "")
        self.assertNotIn("liquidity", result["gate_evidence"])

    def test_client_mapping_is_not_accepted_as_store(self):
        with self.assertRaises(TypeError):
            derive_idpat_gates_from_trusted_store(
                {"market": {"status": "verified"}},
                decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME)


if __name__ == "__main__":
    unittest.main()
