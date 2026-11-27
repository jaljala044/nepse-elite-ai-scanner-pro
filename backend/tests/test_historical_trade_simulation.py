import unittest
from unittest.mock import patch
from app.historical_trade_simulation import simulate

class HistoricalTradeSimulationTests(unittest.TestCase):
    def setUp(self):
        self.days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08","2025-01-09"]
        self.rows=[dict(date=d,open=100,high=104,low=96,close=100,volume=10000) for d in self.days]
        self.rows[-1].update(high=109,close=108)
        self.controls={d:dict(verified=True,evidence_id="synthetic-control",ordinary_session=True,previous_close=100) for d in self.days}
        self.obs=[dict(decision_date=self.days[0],strategy_research=dict(as_of=self.days[0],status="research_only",alignment="aligned",
            biases={k:"bullish" for k in ("daily","weekly","monthly")},
            breakouts=[dict(confirmed_breakout=True,direction="bullish",retest_date=self.days[0])]))]
        self.costs=dict(buy_broker_rate=.001,sell_broker_rate=.001,regulatory_rate=0,sell_dp_charge=0,
                        capital_gain_tax_rate=0,slippage_bps=0,min_broker_fee=0)
    def run_case(self, **overrides):
        kwargs=dict(reviewed={},sessions=self.days,settlement_days=self.days,session_controls=self.controls,
            costs=self.costs,horizon="swing",holding_sessions=3,quantity=10,initial_capital=2000,
            max_participation=.01,stop_fraction=.05,target_fraction=.08)
        kwargs.update(overrides)
        # Evidence gate is isolated here; no assertion of historical source validity.
        with patch("app.historical_trade_simulation.assess",return_value=[]):
            return simulate("TEST",self.rows,self.obs,**kwargs)
    def test_next_session_entry_and_settlement(self):
        t=self.run_case()["trades"][0]
        self.assertEqual((t["entry_date"],t["exit_date"]),(self.days[1],self.days[4]))
        self.assertEqual(t["status"],"closed_scenario")
    def test_cost_integration(self):
        r=self.run_case()
        self.assertAlmostEqual(r["trades"][0]["net_pnl"],80-1-1.08)
        self.assertAlmostEqual(r["statistics"]["net_pnl"],77.92)
        self.assertFalse(r["production_approved"])
    def test_t2_unresolved(self):
        r=self.run_case(horizon="t_plus_2",holding_sessions=2)
        self.assertEqual(r["trades"][0]["status"],"open_unresolved")
        self.assertEqual(r["statistics"]["sample_size"],0)
    def test_insufficient_capital(self):
        r=self.run_case(initial_capital=999)
        self.assertEqual(r["excluded"][0]["reason"],"costs_or_capital_unavailable")
        self.assertFalse(r["trades"])
    def test_low_volume(self):
        self.rows[1]["volume"]=100
        self.assertEqual(self.run_case()["excluded"][0]["reason"],"entry_liquidity_or_band_unverified")
    def test_upper_band(self):
        self.rows[1].update(open=110,high=110,close=110)
        self.assertFalse(self.run_case()["trades"])
    def test_missing_control(self):
        del self.controls[self.days[1]]
        self.assertFalse(self.run_case()["trades"])
    def test_ambiguous_stop_first(self):
        self.rows[-1].update(low=94,high=109)
        t=self.run_case()["trades"][0]
        self.assertEqual((t["exit_reason"],t["exit_price"]),("ambiguous_stop_first",95))
    def test_missing_exit_bar(self):
        self.rows.pop()
        self.assertEqual(self.run_case()["trades"][0]["status"],"open_unresolved")
    def test_missing_cost_assumptions(self):
        self.assertEqual(self.run_case(costs=None)["status"],"missing_execution_evidence")
