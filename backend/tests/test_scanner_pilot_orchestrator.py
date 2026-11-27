import unittest
from unittest.mock import patch
from app.scanner_pilot_orchestrator import run_pilot
class OrchestratorTests(unittest.TestCase):
    @patch("app.scanner_pilot_orchestrator.pilot_inputs")
    @patch("app.scanner_pilot_orchestrator.run_six_scanners")
    def test_block(self,run,gate):
        gate.return_value={"coverage":{"T+2":{"date_coverage_complete":False,"action_basis_verified":False}}}
        r=run_pilot(inputs={},calendar_evidence={},feature_inputs={},horizon="T+2")
        self.assertEqual(len(r["reviews"]),6)
        run.assert_not_called()
    @patch("app.scanner_pilot_orchestrator.pilot_inputs")
    @patch("app.scanner_pilot_orchestrator.run_six_scanners")
    def test_dispatch(self,run,gate):
        gate.return_value={"coverage":{"T+2":{"date_coverage_complete":True,"action_basis_verified":True}}}
        run.return_value={"status":"RESEARCH"}
        r=run_pilot(inputs=dict(symbol="API",sessions=[],stocks=[],benchmark=[],brokers=[],decision_time="t"),calendar_evidence={},feature_inputs={},horizon="T+2")
        run.assert_called_once()
        self.assertFalse(r["backtest_eligible"])
