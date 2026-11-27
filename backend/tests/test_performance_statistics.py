import unittest
from app.performance_statistics import summarize

class PerformanceTests(unittest.TestCase):
    def test_empty(self):
        r=summarize([],initial_capital=1000,synthetic=True)
        self.assertEqual(r["sample_size"],0)
        self.assertIsNone(r["win_rate_pct"])
        self.assertIsNone(r["profit_factor"])
    def test_closed_trade_metrics(self):
        trades=[{"status":"closed_scenario","net_pnl":p} for p in (100,-50,25,0)]
        r=summarize(trades,initial_capital=1000,synthetic=True)
        self.assertEqual(r["sample_size"],4)
        self.assertEqual(r["win_rate_pct"],50)
        self.assertAlmostEqual(r["profit_factor"],2.5)
        self.assertAlmostEqual(r["expectancy"],18.75)
        self.assertAlmostEqual(r["max_closed_trade_drawdown_pct"],100*50/1100)
        self.assertAlmostEqual(r["net_return_pct"],7.5)
    def test_excludes_unfinished(self):
        r=summarize([{"status":"open"},{"status":"closed_scenario","net_pnl":10}],initial_capital=100,synthetic=True)
        self.assertEqual(r["excluded_count"],1)
        self.assertIsNone(r["profit_factor"])
    def test_invalid_pnl(self):
        with self.assertRaises(ValueError):
            summarize([{"status":"closed_scenario","net_pnl":float("nan")}],initial_capital=100,synthetic=True)

    def test_quarantine_and_missing_lineage_excluded(self):
        from app.historical_quarantine import QUARANTINE
        from datetime import date, timedelta
        symbol, day = sorted(QUARANTINE)[0]
        d = date.fromisoformat(day)
        trade = {"status":"closed_scenario","net_pnl":100,"symbol":symbol,
                 "history_start":str(d-timedelta(days=1)),"history_end":str(d+timedelta(days=1))}
        result = summarize([trade, {"status":"closed_scenario","net_pnl":10}],
                           initial_capital=1000)
        self.assertEqual(result["sample_size"],0)
        self.assertEqual(result["excluded_count"],2)
        self.assertFalse(result["production_eligible"])
