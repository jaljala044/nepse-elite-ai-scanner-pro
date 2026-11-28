import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from app.part5_execution_sweep import run_execution_sweep
from app.part5_paper_store import store_paper, list_paper
from app.signal_tracking import freeze_signal
from app.part5_research_dashboard import journal_dashboard

class Part5IntegrationTests(unittest.TestCase):
    def test_sweep_calls_simulator_and_preserves_baseline(self):
        def replay(symbol, rows, observations, **cfg):
            return {"trades":[{"status":"closed_scenario","net_pnl":100-cfg["costs"]["slippage_bps"]}]}
        base={"initial_capital":1000,"costs":{"slippage_bps":10}}
        with patch("app.part5_execution_sweep.simulate",side_effect=replay) as mock:
            result=run_execution_sweep("TEST",[],[],base=base,variants={"high_cost":{"costs":{"slippage_bps":50}}})
        self.assertEqual(mock.call_count,2)
        self.assertAlmostEqual(result["scenarios"]["high_cost"]["return_delta_vs_baseline_pct_points"],-4)
        self.assertEqual(base["costs"]["slippage_bps"],10)

    def test_sweep_cannot_override_evidence(self):
        with self.assertRaises(ValueError):
            run_execution_sweep("TEST",[],[],base={},variants={"bad":{"reviewed":{}}})

    def test_persistence_and_isolation(self):
        signal=freeze_signal(symbol="TEST",decision_time="2025-01-01T12:00:00Z",horizon="swing",
            action="NO TRADE",methodology="fixture",evidence=[],details={})
        trade={"status":"closed_scenario","horizon":"swing","net_pnl":100}
        with TemporaryDirectory() as tmp, patch.dict("os.environ",{"NEPSE_PRIVATE_DB":tmp+"/accounts.sqlite3"}):
            args={"observed_at":"2025-01-05T12:00:00Z"}
            self.assertEqual(store_paper("alice",signal,trade,**args)["status"],"stored")
            self.assertEqual(store_paper("alice",signal,trade,**args)["status"],"already_stored")
            self.assertEqual(list_paper("bob"),[])
            self.assertEqual(journal_dashboard(list_paper("alice"),initial_capital=1000)["horizons"]["swing"]["sample_size"],1)
            with self.assertRaises(ValueError):
                store_paper("alice",signal,{**trade,"net_pnl":500},**args)
