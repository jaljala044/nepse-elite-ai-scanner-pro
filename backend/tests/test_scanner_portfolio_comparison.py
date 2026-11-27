import unittest
from unittest.mock import patch
from app.scanner_portfolio_comparison import compare_portfolios
from app.scanner_common_cohort import METHODS
class ComparisonTests(unittest.TestCase):
    @patch("app.scanner_portfolio_comparison.run_portfolio_backtest")
    def test_empty(self,run):
        run.return_value=dict(trade_count=0,withheld_signal_count=0)
        result=compare_portfolios(candidates={m:[] for m in METHODS},common_inputs={"initial_capital":10000})
        self.assertEqual(run.call_count,6)
        self.assertTrue(all(not r["performance_eligible"] for r in result["methods"].values()))
        self.assertIsNone(result["ranking"])
    def test_override(self):
        with self.assertRaises(ValueError):
            compare_portfolios(candidates={m:[] for m in METHODS},common_inputs={"scenario_runner":None})
