import unittest
from app.performance_statistics import summarize, risk_adjusted

class PerformanceTests(unittest.TestCase):
    def test_empty(self):
        r=summarize([],initial_capital=1000)
        self.assertEqual(r["sample_size"],0)
        self.assertIsNone(r["win_rate_pct"])
        self.assertIsNone(r["profit_factor"])
    def test_closed_trade_metrics(self):
        trades=[{"status":"closed_scenario","net_pnl":p} for p in (100,-50,25,0)]
        r=summarize(trades,initial_capital=1000)
        self.assertEqual(r["sample_size"],4)
        self.assertEqual(r["win_rate_pct"],50)
        self.assertAlmostEqual(r["profit_factor"],2.5)
        self.assertAlmostEqual(r["expectancy"],18.75)
        self.assertAlmostEqual(r["max_closed_trade_drawdown_pct"],100*50/1100)
        self.assertAlmostEqual(r["net_return_pct"],7.5)
    def test_excludes_unfinished(self):
        r=summarize([{"status":"open"},{"status":"closed_scenario","net_pnl":10}],initial_capital=100)
        self.assertEqual(r["excluded_count"],1)
        self.assertIsNone(r["profit_factor"])
    def test_invalid_pnl(self):
        with self.assertRaises(ValueError):
            summarize([{"status":"closed_scenario","net_pnl":float("nan")}],initial_capital=100)


class RiskAdjustedTests(unittest.TestCase):
    def evaluate(self, a=(0.1,-0.05,0.02), b=(0.01,0.01,0.01)):
        days=["2025-01-05","2025-01-06","2025-01-07"][:len(a)]
        return risk_adjusted([dict(date=d,net_return=v) for d,v in zip(days,a)],
            [dict(date=d,net_return=v) for d,v in zip(days,b)],
            expected_sessions=days,periods_per_year=250)
    def test_compounding(self):
        r=self.evaluate()
        self.assertAlmostEqual(r["net_return"],1.1*.95*1.02-1)
        self.assertAlmostEqual(r["benchmark_return"],1.01**3-1)
        self.assertAlmostEqual(r["excess_return"],1.1*.95*1.02-1.01**3)
        self.assertAlmostEqual(r["max_drawdown"],.05)
        self.assertFalse(r["production_approved"])
    def test_ratios(self):
        from statistics import mean,stdev
        from math import sqrt
        r=self.evaluate()
        a=[.1,-.05,.02]; active=[x-.01 for x in a]
        self.assertAlmostEqual(r["sharpe"],mean(a)/stdev(a)*sqrt(250))
        self.assertAlmostEqual(r["sortino"],mean(a)/sqrt(.05**2/3)*sqrt(250))
        self.assertAlmostEqual(r["information_ratio"],mean(active)/stdev(active)*sqrt(250))
    def test_missing_benchmark(self):
        with self.assertRaises(ValueError): self.evaluate(b=(.01,.02))
    def test_invalid_return(self):
        for v in (float("nan"),float("inf"),-1.1,True):
            with self.assertRaises(ValueError): self.evaluate(a=(.1,v,.02))
    def test_insufficient_history(self):
        self.assertEqual(self.evaluate(a=(.01,),b=(.01,))["status"],"insufficient_history")
    def test_no_downside(self):
        self.assertIsNone(self.evaluate(a=(.01,.02,.03))["sortino"])
    def test_duplicate_calendar(self):
        with self.assertRaises(ValueError):
            risk_adjusted([],[],expected_sessions=["2025-01-05"]*2,periods_per_year=250)
