import unittest
from datetime import date
from app.historical_adjusted_feature_pipeline import build_adjusted_versioned_feature_snapshot
from app.historical_dataset_admission import admit_six_scanner_dataset
from app.historical_pilot_corporate_action_verification import verify_corporate_actions
from app.temporal_registry import SecurityMasterRecord

def verified_event(available_at="2025-01-04T10:00:00Z"):
    rows=[]
    for source,publisher in (("S1","P1"),("S2","P2")):
        rows.append({"symbol":"AAA","action_type":"bonus","ex_date":"2025-01-03","terms_reference":"T1",
            "ratio_numerator":1,"ratio_denominator":1,"cash_amount":None,"rights_issue_price":None,
            "available_at":available_at,"source_id":source,"publisher_id":publisher})
    return verify_corporate_actions(primary_rows=rows[:1],secondary_rows=rows[1:],
        previous_closes={"AAA":100},approved_conventions={"bonus":"THEORETICAL_EX_PRICE_V1"})["events"][0]

class AdjustedFeaturePipelineTests(unittest.TestCase):
    def test_only_known_effective_verified_factor_adjusts_pre_ex_date_prices(self):
        records=[
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2025-01-02","available_at":"2025-01-02T16:00:00Z","open":100,"high":110,"low":90,"close":105,"previous_close":99,"volume":1000},
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2025-01-03","available_at":"2025-01-03T16:00:00Z","open":50,"high":55,"low":45,"close":52,"previous_close":50,"volume":2000}]
        event=verified_event()
        security=SecurityMasterRecord("SEC-A","AAA","equity","active",date(2020,1,1),None,"SEC-E","primary_nepse_notice",True,True)
        out=build_adjusted_versioned_feature_snapshot(records,"2025-01-05T12:00:00Z",[security],[],[event],["AAA"])
        audit=out["corporate_action_adjustment_audit"]
        self.assertTrue(out["ohlcv_adjustment_applied"]); self.assertEqual(audit["adjusted_record_count"],1)
        self.assertEqual(audit["adjustments"][0]["factor"],0.5)
        self.assertEqual(audit["adjustments"][0]["raw_prices"]["close"],105)
        self.assertEqual(audit["adjustments"][0]["adjusted_prices"]["close"],52.5)
        self.assertFalse(audit["volume_and_turnover_adjusted"]); self.assertEqual(out["input_lineage_status"],"incomplete")
    def test_future_event_does_not_adjust(self):
        records=[{"record_type":"ohlcv","symbol":"AAA","session_date":"2025-01-02","available_at":"2025-01-02T16:00:00Z","close":100,"volume":10}]
        event=verified_event("2025-01-06T10:00:00Z")
        out=build_adjusted_versioned_feature_snapshot(records,"2025-01-05T12:00:00Z",[],[],[event],["AAA"])
        self.assertFalse(out["ohlcv_adjustment_applied"])
        self.assertEqual(out["corporate_action_adjustment_audit"]["rejected_or_deferred_events"][0]["reason"],"not_yet_knowable_or_effective_at_cutoff")
    def test_event_hash_tampering_is_rejected(self):
        event=verified_event(); event["adjustment_factor"]=0.9
        records=[{"record_type":"ohlcv","symbol":"AAA","session_date":"2025-01-02","available_at":"2025-01-02T16:00:00Z","close":100,"volume":10}]
        out=build_adjusted_versioned_feature_snapshot(records,"2025-01-05T12:00:00Z",[],[],[event],[])
        self.assertFalse(out["ohlcv_adjustment_applied"])
        self.assertEqual(out["corporate_action_adjustment_audit"]["rejected_or_deferred_events"][0]["reason"],"event_hash_mismatch")

class DatasetAdmissionTests(unittest.TestCase):
    def base(self):
        cutoff="2024-09-30T23:00:00Z"
        return dict(panel_qualification={"status":"PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW","backtest_admission_allowed":False,"dataset_fingerprint":"f"*64},
            dataset_manifest={"dataset_fingerprint":"f"*64,"decision_time":cutoff,"corporate_action_review_status":"verified","input_lineage_status":"complete"},
            records=[{"record_id":"r1","available_at":"2024-09-30T10:00:00Z","feature_available_at":"2024-09-30T10:00:00Z"}],
            decision_time=cutoff,expected_dataset_fingerprint="f"*64,train_end="2024-06-30T00:00:00Z",
            validation_start="2024-07-01T00:00:00Z",validation_end="2024-09-29T00:00:00Z",
            test_start="2024-10-01T00:00:00Z",test_end="2024-12-31T00:00:00Z")
    def test_admits_complete_24_cell_matrix_for_human_review_only(self):
        out=admit_six_scanner_dataset(**self.base())
        self.assertEqual(out["status"],"ADMITTED_FOR_HUMAN_REVIEW"); self.assertEqual(out["strategy_horizon_count"],24)
        self.assertFalse(out["replay_started"]); self.assertFalse(out["production_enabled"])
    def test_future_timestamp_fingerprint_and_window_leakage_block_all_cells(self):
        args=self.base(); args["records"]=[{"record_id":"r1","available_at":"2024-10-01T10:00:00Z"}]
        args["expected_dataset_fingerprint"]="wrong"; args["test_start"]="2024-09-01T00:00:00Z"
        out=admit_six_scanner_dataset(**args)
        self.assertEqual(out["status"],"BLOCKED"); self.assertEqual(out["blocker_count"],4)
        self.assertTrue(all(x["status"]=="BLOCKED" for x in out["matrix"]))
    def test_missing_available_at_and_incomplete_lineage_block(self):
        args=self.base(); args["records"]=[{"record_id":"r1"}]; args["dataset_manifest"]["input_lineage_status"]="incomplete"
        out=admit_six_scanner_dataset(**args); self.assertEqual(out["status"],"BLOCKED")
        reasons={x["reason"] for x in out["issues"]}
        self.assertIn("records_missing_available_at",reasons); self.assertIn("input_lineage_incomplete",reasons)

if __name__=="__main__": unittest.main()
