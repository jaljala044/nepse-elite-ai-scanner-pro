import json
import unittest
from datetime import date
from pathlib import Path

from app.temporal_registry import SecurityMasterRecord, security_as_of


class HistoricalIdentitySecurityIdGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        evidence_path = root / "data" / "reference" / "nepse_historical_identity_evidence_2026-11-26.json"
        with evidence_path.open(encoding="utf-8") as handle:
            cls.evidence = json.load(handle)

    def test_predecessor_ids_remain_unresolved_without_dated_evidence(self):
        recovery = self.evidence["security_id_recovery"]
        self.assertEqual(recovery["historical_predecessor_ids"]["status"], "unresolved")
        self.assertEqual(
            set(recovery["historical_predecessor_ids"]["symbols"]),
            {"BPW", "JALPA", "KLBSL", "MKLB", "MMFDB", "NLBBL",
             "SABSL", "SDLBSL", "SAMAJ", "SFCL"},
        )
        for record in self.evidence["records"]:
            if record["symbol"] in recovery["historical_predecessor_ids"]["symbols"]:
                self.assertIsNone(record["stable_id"])

    def test_successor_snapshot_is_explicitly_date_scoped(self):
        snapshot = self.evidence["security_id_recovery"]["successor_snapshot"]
        self.assertEqual(snapshot["snapshot_date"], "2026-11-25")
        self.assertEqual(snapshot["scope"], "current snapshot observation only; not a historical validity interval")
        self.assertTrue(snapshot["source_blob_sha"])

    def test_no_unauthorized_identity_or_history_promotion(self):
        promotion = self.evidence["security_id_recovery"]["promotion"]
        self.assertFalse(promotion["stable_ids_assigned"])
        self.assertFalse(promotion["predecessor_ids_assigned"])
        self.assertFalse(promotion["history_splicing_authorized"])
        self.assertFalse(promotion["canonical_universe_promotion_authorized"])
        self.assertFalse(promotion["training_promotion_authorized"])

    def test_current_snapshot_id_cannot_resolve_historical_identity(self):
        row = SecurityMasterRecord(
            "9356", "BENH", "equity", "active", date(2026, 11, 25), None,
            "current-security-snapshot-2026-11-25",
            "current_snapshot_only", False, False,
        )
        result = security_as_of([row], date(2026, 10, 15))
        self.assertEqual(result["status"], "unverified_identity")
        self.assertIsNone(result["record"])
        self.assertFalse(result["stable_id_verified"])
        self.assertFalse(result["effective_date_verified"])

    def test_secondary_first_trade_date_does_not_prove_historical_security_id(self):
        row = SecurityMasterRecord(
            "9356", "BENH", "equity", "active", date(2026, 10, 15), None,
            "secondary-first-trade-archive-match",
            "secondary_first_trade_archive_match", False, False,
        )
        result = security_as_of([row], date(2026, 10, 15))
        self.assertEqual(result["status"], "unverified_identity")
        self.assertEqual(result["evidence_tiers"], ["secondary_first_trade_archive_match"])

    def test_sharehub_schema_lead_is_not_misrepresented_as_acquired_data(self):
        lead = self.evidence["security_id_recovery"]["provider_lead"]
        self.assertEqual(lead["public_retrieval_status"], "not_acquired")
        self.assertIsNone(lead["response_body_sha256"])
        self.assertIsNone(lead["retrieval_http_status"])


if __name__ == "__main__":
    unittest.main()
