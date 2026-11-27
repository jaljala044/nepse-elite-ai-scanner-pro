import unittest
from app.portfolio_valuation import daily_portfolio

class PortfolioValuationTests(unittest.TestCase):
    def setUp(self):
        self.days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08"]
        self.marks=[dict(date=d,close=p,verified=True,evidence_id="synthetic") for d,p in zip(self.days,[100,95,108,110])]
        self.bench=[dict(date=d,close=p,verified=True,evidence_id="synthetic") for d,p in zip(["2025-01-02"]+self.days,[1000,1010,1000,1020,1030])]
        self.trade=dict(status="closed_scenario",entry_date=self.days[0],exit_date=self.days[2],quantity=10,net_pnl=77.92,costs=dict(buy_cash=1001,sell_cash=1078.92))
        self.sim=dict(status="research_only",classification="hypothetical_research_only",trades=[self.trade])
    def run_case(self, **kwargs):
        args=dict(sessions=self.days,initial_capital=2000,periods_per_year=250)
        args.update(kwargs)
        return daily_portfolio(self.sim,self.marks,self.bench,**args)
    def test_exact_equity_cash_and_shares(self):
        r=self.run_case()
        self.assertEqual([x["shares"] for x in r["equity"]],[10,10,0,0])
        for x,y in zip(r["equity"],[1999,1949,2077.92,2077.92]):
            self.assertAlmostEqual(x["equity"],y)
        self.assertAlmostEqual(r["equity"][0]["cash"],999)
    def test_daily_returns_and_compounding(self):
        r=self.run_case()
        for x,y in zip(r["returns"],[1999/2000-1,1949/1999-1,2077.92/1949-1,0]):
            self.assertAlmostEqual(x["net_return"],y)
        self.assertAlmostEqual(r["performance"]["net_return"],2077.92/2000-1)
    def test_drawdown_includes_open_position(self):
        self.assertAlmostEqual(self.run_case()["performance"]["max_drawdown"],51/2000)
    def test_benchmark_and_excess_return(self):
        r=self.run_case()
        self.assertAlmostEqual(r["benchmark_returns"][0]["net_return"],.01)
        self.assertAlmostEqual(r["performance"]["benchmark_return"],.03)
        self.assertAlmostEqual(r["performance"]["excess_return"],.03896-.03)
    def test_missing_mark(self):
        self.marks.pop(1)
        self.assertEqual(self.run_case()["reason"],"marks_or_benchmark_unverified")
    def test_benchmark_date_mismatch(self):
        self.bench[2]["date"]="2025-01-09"
        self.assertEqual(self.run_case()["reason"],"marks_or_benchmark_unverified")
    def test_missing_prior_benchmark(self):
        self.bench.pop(0)
        self.assertEqual(self.run_case()["reason"],"benchmark_history_missing")
    def test_unresolved_position(self):
        self.trade["status"]="open_unresolved"
        self.assertEqual(self.run_case()["reason"],"unresolved_position")
    def test_overlapping_trades(self):
        self.sim["trades"].append(dict(self.trade,entry_date=self.days[1],exit_date=self.days[3]))
        with self.assertRaises(ValueError): self.run_case()
    def test_cash_flow_mismatch_and_insufficient_capital(self):
        self.trade["net_pnl"]=80
        with self.assertRaises(ValueError): self.run_case()
        self.trade["net_pnl"]=77.92
        with self.assertRaises(ValueError): self.run_case(initial_capital=1000)
