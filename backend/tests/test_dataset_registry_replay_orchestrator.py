import unittest
from app.nepse_dataset_registry import build_dataset_registry, REQUIRED_DATASETS
from app.scanner_replay_orchestrator import run_six_strategy_replay

def report(kind):
    rows = [{"sample":"row"}]
    return {"dataset_kind":kind,"status":"validated_for_research","captured_at":"2025-01-02T10:00:00+05:45",
        "source_envelope":{"source_id":"SRC-"+kind,"publisher":"Publisher "+kind,"evidence_id":"EV-"+kind,
            "raw_sha256":"a"*64,"available_at":"2025-01-02T10:00:00+05:45",
            "rights_status":"approved","source_validation_status":"verified","finality_status":"final",
            "registry_review_id":"REVIEW-"+kind},
        "validation":{"research_review_allowed":True,"accepted_rows":rows}}

class DatasetRegistryTests(unittest.TestCase):
    def test_all_required_sources_admit(self):
        out=build_dataset_registry(intake_reports={k:report(k) for k in REQUIRED_DATASETS},
            decision_cutoff="2025-01-03T10:00:00+05:45")
        self.assertEqual(out["status"],"ready_for_panel_assembly")
        self.assertEqual(out["required_dataset_coverage_pct"],"100.0")
        self.assertEqual(out["data_quality"],"MEDIUM")
    def test_missing_required_dataset_blocks(self):
        out=build_dataset_registry(intake_reports={"ohlcv":report("ohlcv")},
            decision_cutoff="2025-01-03T10:00:00+05:45")
        self.assertEqual(out["status"],"blocked")
        self.assertTrue(any("required_dataset_missing" in e for e in out["errors"]))
    def test_future_source_blocks(self):
        r=report("ohlcv"); r["source_envelope"]["available_at"]="2025-01-04T10:00:00+05:45"
        out=build_dataset_registry(intake_reports={"ohlcv":r},
            decision_cutoff="2025-01-03T10:00:00+05:45")
        self.assertEqual(out["status"],"blocked")
    def test_unapproved_rights_blocks(self):
        r=report("ohlcv"); r["source_envelope"]["rights_status"]="unknown"
        out=build_dataset_registry(intake_reports={"ohlcv":r},
            decision_cutoff="2025-01-03T10:00:00+05:45")
        self.assertEqual(out["status"],"blocked")
    def test_invalid_hash_blocks(self):
        r=report("ohlcv"); r["source_envelope"]["raw_sha256"]="bad"
        out=build_dataset_registry(intake_reports={"ohlcv":r},
            decision_cutoff="2025-01-03T10:00:00+05:45")
        self.assertEqual(out["status"],"blocked")

class ReplayOrchestratorTests(unittest.TestCase):
    def test_unvalidated_panel_fails_closed(self):
        out=run_six_strategy_replay(historical_panel={"status":"blocked","eligible_symbols":[]},
            signals_by_strategy_horizon={},bars_by_symbol={},round_trip_cost_pct="1",
            round_trip_slippage_pct="1")
        self.assertEqual(out["status"],"blocked")
        self.assertFalse(out["performance_claimed"])
    def test_empty_batches_are_explicit_not_fabricated(self):
        panel={"status":"validated_for_research","eligible_symbols":["ABC"],"strategy_eligibility":{name:{"eligible":True,"missing_datasets":[]} for name in ("trend_momentum","idpat_smart_money","broker_footprint","smc_ict_liquidity","hybrid_consensus","fundamental_investment")}}
        out=run_six_strategy_replay(historical_panel=panel,signals_by_strategy_horizon={},
            bars_by_symbol={},round_trip_cost_pct="1",round_trip_slippage_pct="1")
        self.assertEqual(out["expected_run_count"],72)
        self.assertEqual(out["completed_run_count"],72)
        self.assertTrue(all(r["status"]=="no_eligible_trades" for r in out["runs"]))
        self.assertFalse(out["performance_claimed"])

if __name__=="__main__": unittest.main()
