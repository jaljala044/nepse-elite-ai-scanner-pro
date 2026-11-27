import unittest
from app.historical_pilot_ingest import calculate_pilot_row_sha256
from app.historical_pilot_replay_gate import build_pilot_replay_preflight

class PilotReplayPreflightTests(unittest.TestCase):
    def args(self):
        row={"symbol":"AAA","session_date":"2025-01-02","open":10,"high":12,"low":9,"close":11,"volume":100,"available_at":"2025-01-02T16:00:00+05:45","source_id":"SRC-1","publisher_id":"PUB-1","raw_sha256":"a"*64,"capture_id":"CAP-1","payload_id":"PAGE-1","capture_manifest_sha256":"c"*64,"page_number":1,"source_row_number":2}
        row["row_sha256"]=calculate_pilot_row_sha256(row)
        return dict(cohort_symbols=["AAA"],security_master=[{"symbol":"AAA","security_id":"SEC-1","effective_from":"2025-01-01"}],expected_sessions=[{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL-1","available_at":"2025-01-02T15:00:00+05:45"}],ingestion_reports=[{"status":"INGESTED","all_rows_accepted":True,"rows":[row],"source_id":"SRC-1","publisher_id":"PUB-1","capture_id":"CAP-1","capture_manifest_sha256":"c"*64}],corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},source_reconciliation_report={"status":"SOURCE_EVIDENCE_RECONCILED","capture_reports":{"first_day":{"status":"CAPTURE_VALIDATED"}},"first_trade_report":{"all_cohort_first_trades_verified":True,"verified_count":1,"cohort_count":1,"unresolved_count":0}},decision_cutoff="2025-01-03T00:00:00+05:45",required_capture_keys=["first_day"])
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
        self.assertEqual(a["dataset_manifest"]["sha256"], a["dataset_manifest"]["input_manifest_sha256"])
        self.assertEqual(len(a["dataset_manifest"]["panel_output_sha256"]), 64)

    def test_expected_session_evidence_is_bound_into_manifest(self):
        args=self.args()
        baseline=build_pilot_replay_preflight(**args)
        args["expected_sessions"][0]["evidence_id"]="CAL-2"
        changed=build_pilot_replay_preflight(**args)
        self.assertNotEqual(baseline["dataset_manifest"]["sha256"], changed["dataset_manifest"]["sha256"])

    def test_raw_capture_page_hash_is_bound_into_manifest(self):
        args=self.args()
        baseline=build_pilot_replay_preflight(**args)
        args["source_reconciliation_report"]["capture_reports"]["first_day"]["verified_pages"]=[{"page_number":1,"payload_id":"PAGE-1","raw_sha256":"d"*64}]
        changed=build_pilot_replay_preflight(**args)
        self.assertNotEqual(baseline["dataset_manifest"]["sha256"], changed["dataset_manifest"]["sha256"])

if __name__=="__main__": unittest.main()
