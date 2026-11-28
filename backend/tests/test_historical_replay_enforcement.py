import unittest
from app.historical_replay_enforcement import (
    audit_point_in_time_replay_observations, enforce_and_run_six_scanner_replay,
)
from app.historical_pilot_replay_admission import STRATEGIES, HORIZONS


class PointInTimeLeakageAuditTests(unittest.TestCase):
    def clean(self):
        return [{"observation_id":"OBS-1","decision_at":"2025-01-10T10:00:00Z",
                 "features":[{"feature_id":"F1","available_at":"2025-01-10T09:00:00Z",
                              "source_available_at":"2025-01-10T08:55:00Z","value":12.5}],
                 "label":0.04,"outcome_end_at":"2025-01-15T10:00:00Z",
                 "label_available_at":"2025-01-15T16:00:00Z"}]
    def test_clean_observation_and_delayed_label_pass(self):
        out=audit_point_in_time_replay_observations(self.clean())
        self.assertEqual(out["status"],"POINT_IN_TIME_CLEAN")
        self.assertFalse(out["labels_used_as_features"])
    def test_future_feature_source_and_early_label_block(self):
        row=self.clean()[0]
        row["features"][0]["available_at"]="2025-01-11T10:00:00Z"
        row["features"][0]["source_available_at"]="2025-01-11T10:00:00Z"
        row["label_available_at"]="2025-01-12T10:00:00Z"
        out=audit_point_in_time_replay_observations([row])
        reasons={x["reason"] for x in out["issues"]}
        self.assertIn("feature_available_after_decision",reasons)
        self.assertIn("source_available_after_decision",reasons)
        self.assertIn("label_available_before_outcome_complete",reasons)
    def test_outcome_embedded_in_feature_and_duplicate_ids_block(self):
        row=self.clean()[0]
        row["features"][0]["future_return"]=0.2
        out=audit_point_in_time_replay_observations([row,row])
        reasons={x["reason"] for x in out["issues"]}
        self.assertIn("outcome_field_embedded_in_features",reasons)
        self.assertIn("duplicate_observation_id",reasons)
    def test_missing_feature_timestamps_block(self):
        row=self.clean()[0]
        row["features"][0].pop("source_available_at")
        self.assertEqual(audit_point_in_time_replay_observations([row])["status"],"LEAKAGE_BLOCKED")


class ReplayEnforcementTests(unittest.TestCase):
    def args(self):
        fp="f"*64; manifest="a"*64; cutoff="2024-09-30T23:00:00Z"
        dataset=dict(
            panel_qualification={"status":"PANEL_EVIDENCE_QUALIFIED_FOR_HUMAN_REVIEW","backtest_admission_allowed":False,"dataset_fingerprint":fp},
            dataset_manifest={"dataset_fingerprint":fp,"decision_time":cutoff,"corporate_action_review_status":"verified","input_lineage_status":"complete"},
            records=[{"record_id":"R1","available_at":"2024-09-30T10:00:00Z","feature_available_at":"2024-09-30T10:00:00Z"}],
            decision_time=cutoff,expected_dataset_fingerprint=fp,train_end="2024-06-30T00:00:00Z",
            validation_start="2024-07-01T00:00:00Z",validation_end="2024-09-29T00:00:00Z",
            test_start="2024-10-01T00:00:00Z",test_end="2024-12-31T00:00:00Z")
        preflight={"status":"BOUNDED_PILOT_REPLAY_PREFLIGHT_READY","historical_replay_executed":False,"dataset_manifest":{"sha256":manifest}}
        return dict(dataset_admission_kwargs=dataset,quality_dashboard={"status":"QUALITY_REVIEW_READY"},
            replay_preflight=preflight,strategy_ids=list(STRATEGIES),horizons=list(HORIZONS),
            dataset_manifest_sha256=manifest,partition="untouched_out_of_sample",
            cost_model={"commission":1,"regulatory_fees":1,"taxes":1,"slippage":1},
            execution_model={"next_session_execution":True,"liquidity_cap":0.05,"settlement_delay":"T+2","stop_first":True,"circuit_and_no_bid_handling":True},
            human_review={"reviewed":True,"approved":True,"reviewer_id":"reviewer-1","reviewed_at":"2026-11-28T09:00:00Z"},
            observations=PointInTimeLeakageAuditTests().clean(),panel_rows=[{"symbol":"AAA"}])
    def test_gate_calls_runner_only_after_all_admissions(self):
        args=self.args(); calls=[]
        def runner(**kw):
            calls.append((kw["strategy_id"],kw["horizon"]))
            return {k:kw[k] for k in ("strategy_id","horizon","dataset_manifest_sha256","partition")}
        args["run_one"]=runner
        # Use same fingerprint in dataset gate and replay manifest for a successful path.
        args["dataset_admission_kwargs"]["dataset_manifest"]["dataset_fingerprint"]="a"*64
        args["dataset_admission_kwargs"]["panel_qualification"]["dataset_fingerprint"]="a"*64
        args["dataset_admission_kwargs"]["expected_dataset_fingerprint"]="a"*64
        out=enforce_and_run_six_scanner_replay(**args)
        self.assertEqual(out["status"],"RESEARCH_REPLAY_COMPLETED")
        self.assertEqual(len(calls),24); self.assertEqual(out["run_count"],24)
    def test_dataset_or_leakage_block_never_calls_runner(self):
        args=self.args(); calls=[]
        args["observations"][0]["features"][0]["available_at"]="2025-02-01T00:00:00Z"
        args["run_one"]=lambda **kw:calls.append(kw)
        out=enforce_and_run_six_scanner_replay(**args)
        self.assertEqual(out["status"],"BLOCKED"); self.assertEqual(calls,[])
    def test_missing_human_approval_blocks_before_runner(self):
        args=self.args(); args["human_review"]={"reviewed":True,"approved":False}
        calls=[]; args["run_one"]=lambda **kw:calls.append(kw)
        out=enforce_and_run_six_scanner_replay(**args)
        self.assertEqual(out["status"],"BLOCKED"); self.assertEqual(calls,[])


if __name__=="__main__": unittest.main()
