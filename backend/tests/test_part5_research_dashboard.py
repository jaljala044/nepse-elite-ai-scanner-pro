import unittest
from app.part5_research_dashboard import comparative_readiness, stress_report, journal_dashboard
from app.part5_paper_journal import freeze_paper_outcome, verify_paper_outcome
from app.signal_tracking import freeze_signal

class Part5ResearchDashboardTests(unittest.TestCase):
    def test_empty_manifest_blocks_comparison(self):
        self.assertEqual(comparative_readiness({})["status"],"blocked_no_canonical_rows")
        self.assertFalse(comparative_readiness({("A","2025-01-01"): {}})["backtest_executed"])

    def test_stress_delta_and_missing(self):
        def trade(pnl):
            return {"status":"closed_scenario","net_pnl":pnl}
        result=stress_report({"baseline":[trade(100)],"higher_cost":[trade(50)],"empty":[]},initial_capital=1000)
        self.assertAlmostEqual(result["scenarios"]["higher_cost"]["return_delta_vs_baseline_pct_points"],-5)
        self.assertIsNone(result["scenarios"]["empty"]["return_delta_vs_baseline_pct_points"])

    def test_journal_and_dashboard(self):
        signal=freeze_signal(symbol="TEST",decision_time="2025-01-01T12:00:00Z",
            horizon="swing",action="NO TRADE",methodology="fixture",evidence=[],details={})
        trade={"status":"closed_scenario","horizon":"swing","net_pnl":100}
        envelope=freeze_paper_outcome(signal,trade,observed_at="2025-01-05T12:00:00Z")
        self.assertTrue(verify_paper_outcome(envelope))
        result=journal_dashboard([envelope],initial_capital=1000)
        self.assertEqual(result["horizons"]["swing"]["win_rate_pct"],100)
        self.assertIsNone(result["horizons"]["investment"]["win_rate_pct"])
        self.assertIsNone(result["signal_accuracy"])
        with self.assertRaises(ValueError):
            journal_dashboard([envelope,envelope],initial_capital=1000)
        envelope["record"]["trade"]["net_pnl"]=999
        self.assertFalse(verify_paper_outcome(envelope))

    def test_outcome_before_decision_rejected(self):
        signal=freeze_signal(symbol="TEST",decision_time="2025-01-01T12:00:00Z",
            horizon="swing",action="NO TRADE",methodology="fixture",evidence=[],details={})
        with self.assertRaises(ValueError):
            freeze_paper_outcome(signal,{"status":"open_unresolved","horizon":"swing"},
                observed_at="2024-12-31T12:00:00Z")
