import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.trusted_artifact_store import TrustedArtifactStore, build_trusted_market_snapshot
from app.market_intelligence_snapshot import REQUIRED_MODULES


class TrustedArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = b'{"metric": 12, "basis": "verified-close"}'
        (self.root / "index.json").write_bytes(self.payload)
        self.entry = {
            "source_id": "NEPSE_PRIMARY_EOD_01",
            "payload_path": "index.json",
            "payload_sha256": hashlib.sha256(self.payload).hexdigest(),
            "evidence_ids": ["eod:2026-11-27:index"],
            "as_of_date": "2026-11-27",
            "available_at": "2026-11-27T15:15:00+05:45",
            "status": "research_only",
            "coverage_ratio": 1.0,
            "source_validation_status": "verified",
            "finality_status": "final",
            "session_calendar_id": "NEPSE-CALENDAR-v1",
            "corporate_action_status": "verified",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def store(self, entry=None, module="index_intelligence"):
        return TrustedArtifactStore(self.root, {module: entry or self.entry})

    def test_admits_pinned_server_side_payload(self):
        result = self.store().load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertEqual(result["index_intelligence"]["data"]["metric"], 12)
        self.assertEqual(result["index_intelligence"]["source_ids"], ["NEPSE_PRIMARY_EOD_01"])

    def test_hash_mismatch_is_not_admitted(self):
        entry = dict(self.entry, payload_sha256="0" * 64)
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertNotIn("data", result["index_intelligence"])
        self.assertIn("payload_sha256_mismatch", result["index_intelligence"]["rejection_reason"])

    def test_future_availability_is_rejected(self):
        entry = dict(self.entry, available_at="2026-11-27T17:00:00+05:45")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("artifact_available_after_decision_time",
                      result["index_intelligence"]["rejection_reason"])

    def test_stale_artifact_is_rejected(self):
        entry = dict(self.entry, as_of_date="2026-11-01")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("artifact_stale", result["index_intelligence"]["rejection_reason"])

    def test_unverified_finality_is_rejected(self):
        entry = dict(self.entry, finality_status="provisional")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("source_finality_not_verified",
                      result["index_intelligence"]["rejection_reason"])

    def test_path_traversal_is_rejected(self):
        entry = dict(self.entry, payload_path="../outside.json")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("payload_path_unsafe", result["index_intelligence"]["rejection_reason"])

    def test_missing_modules_remain_unknown_in_snapshot(self):
        snapshot = build_trusted_market_snapshot(
            self.store(), decision_date="2026-11-27",
            decision_time="2026-11-27T16:00:00+05:45",
        )
        self.assertEqual(snapshot["status"], "partial_evidence")
        self.assertIsNone(snapshot["production_score"])
        self.assertFalse(snapshot["signals_enabled"])
        self.assertIn("market_health", snapshot["missing_modules"])


    def test_unverified_corporate_action_status_is_rejected(self):
        entry = dict(self.entry, corporate_action_status="unknown")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("corporate_action_status_unverified",
                      result["index_intelligence"]["rejection_reason"])

    def test_sector_membership_must_be_effective_versioned_and_verified(self):
        entry = dict(self.entry, sector_membership_status="unverified",
                     sector_membership_version="sector-map-v1")
        result = self.store(entry, module="sector_rotation").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("sector_rotation",),
        )
        self.assertIn("sector_membership_version_unverified",
                      result["sector_rotation"]["rejection_reason"])

    def test_broker_code_identity_coverage_is_required(self):
        entry = dict(self.entry, broker_code_mapping_status="verified",
                     broker_identity_coverage_ratio=0.0)
        result = self.store(entry, module="broker_profiles").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("broker_profiles",),
        )
        self.assertIn("broker_identity_coverage_invalid",
                      result["broker_profiles"]["rejection_reason"])

    def test_broker_code_mapping_must_be_verified(self):
        entry = dict(self.entry, broker_code_mapping_status="unverified",
                     broker_identity_coverage_ratio=0.95)
        result = self.store(entry, module="broker_profiles").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("broker_profiles",),
        )
        self.assertIn("broker_code_mapping_unverified",
                      result["broker_profiles"]["rejection_reason"])

    def test_duplicate_evidence_ids_rejected(self):
        entry = dict(self.entry, evidence_ids=["same", "same"])
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("evidence_ids_missing_or_duplicate",
                      result["index_intelligence"]["rejection_reason"])


if __name__ == "__main__":
    unittest.main()
