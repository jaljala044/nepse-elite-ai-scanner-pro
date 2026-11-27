import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.idpat_deployment_readiness import load_deployment_idpat_gate_readiness
from app.idpat_trusted_gate_bridge import REQUIRED_ARTIFACTS


CUTOFF_DATE = "2026-11-27"
CUTOFF_TIME = "2026-11-27T16:00:00+05:45"


def payload_for(module):
    fields = {
        "market_health": {"calendar_status": "verified", "market_summary_finality_verified": True},
        "index_intelligence": {"index_integrity_status": "passed"},
        "sector_rotation": {"membership_status": "verified", "sector_data_status": "verified", "price_coverage_ratio": 0.99},
        "broker_profiles": {"reconciliation_status": "passed", "verified_amount_coverage": 0.97},
        "broker_sector_rotation": {"identity_policy_status": "passed"},
        "ohlcv_quality": {"ohlcv_integrity_status": "passed", "per_security_coverage_ratio": 0.99},
        "turnover_quality": {"turnover_status": "verified"},
        "execution_readiness": {"session_calendar_status": "verified", "execution_constraints_status": "verified", "next_session_history_complete": True},
        "corporate_actions": {"registry_status": "verified", "source_universe_completeness_verified": True, "point_in_time_eligible": True},
        "source_quality": {"raw_hashes_verified": True, "lineage_complete": True, "rights_clearance": True, "unresolved_conflict_count": 0},
    }
    return fields[module]


class DeploymentReadinessTests(unittest.TestCase):
    def test_missing_configuration_blocks_all_gates(self):
        result = load_deployment_idpat_gate_readiness(
            decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME, environ={})
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(result["missing_configuration"]), 3)
        self.assertFalse(result["production_enabled"])

    def test_valid_pinned_registry_derives_all_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "artifacts"
            root.mkdir()
            registry = {}
            for module in REQUIRED_ARTIFACTS:
                raw = json.dumps(payload_for(module), sort_keys=True).encode()
                (root / (module + ".json")).write_bytes(raw)
                registry[module] = {
                    "source_id": "SRC-" + module,
                    "payload_path": module + ".json",
                    "payload_sha256": hashlib.sha256(raw).hexdigest(),
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
                    "sector_membership_version": "sector-map-v1",
                    "broker_code_mapping_status": "verified",
                    "broker_identity_coverage_ratio": 0.97,
                }
            registry_raw = json.dumps(registry, sort_keys=True).encode()
            registry_path = Path(temp) / "registry.json"
            registry_path.write_bytes(registry_raw)
            env = {
                "NEPSE_TRUSTED_ARTIFACT_ROOT": str(root),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY": str(registry_path),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256": hashlib.sha256(registry_raw).hexdigest(),
            }
            result = load_deployment_idpat_gate_readiness(
                decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME, environ=env)
            self.assertEqual(result["status"], "ready_for_research_review")
            self.assertEqual(len(result["gate_evidence"]), 7)
            self.assertFalse(result["production_enabled"])

    def test_registry_hash_mismatch_blocks_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "artifacts"
            root.mkdir()
            path = Path(temp) / "registry.json"
            path.write_text("{}")
            env = {
                "NEPSE_TRUSTED_ARTIFACT_ROOT": str(root),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY": str(path),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256": "0" * 64,
            }
            result = load_deployment_idpat_gate_readiness(
                decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME, environ=env)
            self.assertEqual(result["reason"], "trusted_artifact_registry_sha256_mismatch")

    def test_malformed_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "artifacts"
            root.mkdir()
            path = Path(temp) / "registry.json"
            path.write_text("[]")
            raw = path.read_bytes()
            env = {
                "NEPSE_TRUSTED_ARTIFACT_ROOT": str(root),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY": str(path),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY_SHA256": hashlib.sha256(raw).hexdigest(),
            }
            result = load_deployment_idpat_gate_readiness(
                decision_date=CUTOFF_DATE, decision_time=CUTOFF_TIME, environ=env)
            self.assertEqual(result["reason"], "trusted_artifact_registry_must_be_object")


if __name__ == "__main__":
    unittest.main()
