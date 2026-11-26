import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.temporal_registry import SecurityMasterRecord, CorporateActionRecord
from app.versioned_feature_store import build_versioned_feature_snapshot, persist_versioned_snapshot


class VersionedFeatureStoreTests(unittest.TestCase):
    def test_as_of_security_and_action_join_and_immutable_persistence(self):
        records = [{"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
                    "available_at":"2026-11-23T16:00:00Z","close":11,
                    "previous_close":10,"volume":100}]
        securities = [SecurityMasterRecord("SEC-A","AAA","equity","active",
                                           date(2020,1,1),None,"security-registry-v1",
                                           "primary_nepse_notice", True, True)]
        actions = [
            CorporateActionRecord("CA1","SEC-A","bonus",date(2026,11,20),
                                  "2026-11-18T09:00:00Z","2026-11-18T09:00:00Z",1.1,"action-e1",
                                  "primary_nepse_notice","verified_primary",True),
            CorporateActionRecord("CA2","SEC-A","right",date(2026,11,21),
                                  "2026-11-25T09:00:00Z","2026-11-25T09:00:00Z",1.2,"action-e2",
                                  "primary_nepse_notice","verified_primary",True),
        ]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, actions, ["AAA"])
        joined = snapshot["security_and_action_joins"]["AAA"]
        self.assertEqual(joined["security_id"], "SEC-A")
        self.assertTrue(joined["security_identity_verified"])
        self.assertEqual(joined["corporate_action_count"], 1)
        self.assertEqual(joined["corporate_action_adjustment_eligible_count"], 1)
        self.assertEqual(len(joined["corporate_action_adjustment_actions"]), 1)
        self.assertFalse(joined["corporate_action_source_universe_completeness_verified"])
        self.assertEqual(snapshot["features"]["trend_features"]["AAA"]["status"], "insufficient_evidence")
        self.assertIsNone(snapshot["features"]["trend_features"]["AAA"]["score"])
        self.assertFalse(snapshot["ohlcv_adjustment_applied"])
        with tempfile.TemporaryDirectory() as tmp:
            first = persist_versioned_snapshot(tmp, snapshot)
            second = persist_versioned_snapshot(tmp, snapshot)
            self.assertFalse(first["idempotent"])
            self.assertTrue(second["idempotent"])
            self.assertTrue(Path(first["path"]).exists())
            saved = json.loads(Path(first["path"]).read_text())
            self.assertEqual(saved["snapshot_sha256"], snapshot["snapshot_sha256"])

    def test_snapshot_reports_incomplete_input_lineage(self):
        records = [{"record_id":"r1","record_type":"ohlcv","symbol":"AAA",
                    "session_date":"2026-11-23","available_at":"2026-11-23T16:00:00Z",
                    "close":11,"previous_close":10,"volume":100}]
        securities = [SecurityMasterRecord("SEC-A","AAA","equity","active",
                                           date(2020,1,1),None,"security-registry-v1")]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, [], ["AAA"])
        self.assertEqual(snapshot["input_lineage_status"], "incomplete")
        self.assertEqual(snapshot["input_lineage"][0]["record_id"], "r1")

    def test_snapshot_reports_complete_input_lineage(self):
        records = [{"record_id":"r1","source_id":"official-eod","source_payload_sha256":"a"*64,
                    "source_row_number":2,"record_type":"ohlcv","symbol":"AAA",
                    "session_date":"2026-11-23","available_at":"2026-11-23T16:00:00Z",
                    "close":11,"previous_close":10,"volume":100}]
        securities = [SecurityMasterRecord("SEC-A","AAA","equity","active",
                                           date(2020,1,1),None,"security-registry-v1")]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, [], ["AAA"])
        self.assertEqual(snapshot["input_lineage_status"], "complete")
        self.assertEqual(snapshot["input_lineage"][0]["payload_sha256"], "a"*64)

    def test_ambiguous_security_does_not_join_actions(self):
        records = [{"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
                    "available_at":"2026-11-23T16:00:00Z","close":11,
                    "previous_close":10,"volume":100}]
        securities = [
            SecurityMasterRecord("SEC-A","AAA","equity","active",date(2020,1,1),None,"e1"),
            SecurityMasterRecord("SEC-B","AAA","equity","active",date(2020,1,1),None,"e2"),
        ]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, [], ["AAA"])
        self.assertEqual(snapshot["security_and_action_joins"]["AAA"]["security_status"], "ambiguous")

    def test_current_snapshot_only_identity_does_not_join_actions(self):
        records = [{"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
                    "available_at":"2026-11-23T16:00:00Z","close":11,
                    "previous_close":10,"volume":100}]
        securities = [SecurityMasterRecord("SEC-A","AAA","equity","active",
                                           date(2020,1,1),None,"current-snapshot",
                                           "current_snapshot_only",False,False)]
        actions = [CorporateActionRecord(
            "CA1","SEC-A","bonus",date(2026,11,20),
            "2026-11-18T09:00:00Z","2026-11-18T09:00:00Z",1.1,"action-e1",
            "primary_nepse_notice","verified_primary",True
        )]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, actions, ["AAA"])
        joined = snapshot["security_and_action_joins"]["AAA"]
        self.assertEqual(joined["security_status"], "unverified_identity")
        self.assertFalse(joined["security_identity_verified"])
        self.assertEqual(joined["corporate_actions"], [])

    def test_unverified_corporate_action_is_not_joined_as_adjustment(self):
        records = [{"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
                    "available_at":"2026-11-23T16:00:00Z","close":11,
                    "previous_close":10,"volume":100}]
        securities = [SecurityMasterRecord("SEC-A","AAA","equity","active",
                                           date(2020,1,1),None,"security-registry-v1",
                                           "primary_nepse_notice",True,True)]
        actions = [CorporateActionRecord(
            "CA1","SEC-A","bonus",date(2026,11,20),
            "2026-11-18T09:00:00Z","2026-11-18T09:00:00Z",1.1,"unverified-action",
            "unverified","unverified",False
        )]
        snapshot = build_versioned_feature_snapshot(records, "2026-11-24T12:00:00Z",
                                                     securities, actions, ["AAA"])
        joined = snapshot["security_and_action_joins"]["AAA"]
        self.assertEqual(joined["corporate_action_count"], 0)
        self.assertEqual(joined["corporate_action_adjustment_eligible_count"], 0)
        self.assertEqual(joined["corporate_action_excluded_unverified_count"], 1)
        self.assertFalse(joined["corporate_action_point_in_time_eligible"])
        self.assertFalse(joined["corporate_action_source_universe_completeness_verified"])
        self.assertFalse(snapshot["ohlcv_adjustment_applied"])

    def test_hash_tampering_rejected(self):
        with self.assertRaises(ValueError):
            persist_versioned_snapshot(tempfile.gettempdir(), {"snapshot_sha256":"bad"})


if __name__ == "__main__":
    unittest.main()
