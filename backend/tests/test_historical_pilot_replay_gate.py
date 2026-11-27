import unittest
from app.historical_pilot_replay_gate import build_pilot_replay_preflight

class PilotReplayPreflightTests(unittest.TestCase):
    def args(self):
        row={"symbol":"AAA","session_date":"2025-01-02","open":10,"high":12,"low":9,"close":11,"volume":100,"available_at":"2025-01-02T16:00:00+05:45","source_id":"SRC-1","publisher_id":"PUB-1","raw_sha256":"a"*64,"capture_id":"CAP-1","page_number":1,"source_row_number":2,"row_sha256":"b"*64}
        return dict(cohort_symbols=["AAA"],security_master=[{"symbol":"AAA","security_id":"SEC-1","effective_from":"2025-01-01"}],expected_sessions=[{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL-1","available_at":"2025-01-02T15:00:00+05:45"}],ingestion_reports=[{"status":"INGESTED","all_rows_accepted":True,"rows":[row]}],corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},source_reconciliation_report={"status":"SOURCE_EVIDENCE_RECONCILED","capture_reports":{"first_day":{"status":"CAPTURE_VALIDATED"}},"first_trade_report":{"all_cohort_first_trades_verified":True,"verified_count":1,"cohort_count":1,"unresolved_count":0}},decision_cutoff="2025-01-03T00:00:00+05:45",required_capture_keys=["first_day"])
    def test_ready_preflight_never_auto_admits_backtest(self):
        out=build_pilot_replay_preflight(**self.args())
        self.assertEqual(out["status"],"BOUNDED_PILOT_REPLAY_PREFLIGHT_READY", msg=repr(out.get("gate_diagnostics")))
        self.assertFalse(out["historical_replay_executed"])
        self.assertFalse(out["backtest_admission_allowed"])
        self.assertEqual(len(out["dataset_manifest"]["sha256"]),64)
    def test_missing_official_capture_blocks(self):
        args=self.args(); args["source_reconciliation_report"]={"status":"BLOCKED","capture_reports":{},"first_trade_report":{}}
        out=build_pilot_replay_preflight(**args)
        self.assertEqual(out["status"],"BLOCKED")
    def test_manifest_hash_deterministic(self):
        a=build_pilot_replay_preflight(**self.args())
        b=build_pilot_replay_preflight(**self.args())
        self.assertEqual(a["dataset_manifest"]["sha256"],b["dataset_manifest"]["sha256"])

if __name__=="__main__": unittest.main()
