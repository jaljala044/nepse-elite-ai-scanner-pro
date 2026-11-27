import unittest
from fastapi.testclient import TestClient
from app.main import app

class IntegratedResearchTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.timestamp="2025-01-06T17:00:00+05:45"
        e=dict(status="verified",source_id="synthetic",coverage=1,available_at=self.timestamp)
        self.snapshot=dict(symbol="AAA",as_of_date="2025-01-06",available_at=self.timestamp,
            market=dict(e,regime="bull"),sector=dict(e,alignment="leading_or_improving",excess_return_1m=.05),
            liquidity=dict(e,median_turnover=2000000,median_spread_pct=1,median_trade_count=50,median_displayed_depth=200000),
            broker=dict(e,net_amount=100000,positive_net_session_ratio=.8),
            price_volume=e,candidate=dict(e,classification="early_accumulation_candidate"),
            plans={"swing":dict(setup="momentum_breakout",entry_type="confirmed_breakout",confirmation="confirmed",
                entry=100,stop=95,targets=[110,115],invalidation_condition="close_below_stop",
                level_status="inferred_chart_level",evidence_dates=["2025-01-06"])})
        self.confirmation=dict(e,symbol="AAA",wyckoff="BULLISH",smc="BULLISH",volume="BULLISH",
                               relative_strength="BULLISH",sector="BULLISH")
    def request(self,confirmation):
        return self.client.post("/v1/research/integrated",json=dict(snapshot=self.snapshot,
            as_of_date="2025-01-06",as_of_timestamp=self.timestamp,confirmation=confirmation))
    def test_frozen_buy(self):
        response=self.request(self.confirmation)
        self.assertEqual(response.status_code,200,response.text)
        result=response.json()
        self.assertEqual(result["actions"]["swing"],"BUY_RESEARCH")
        self.assertEqual(result["actions"]["investment"],"UNKNOWN")
        self.assertEqual(len(result["frozen_signals"]),1)
        self.assertFalse(result["production_eligible"])
    def test_missing_confirmation(self):
        result=self.request(None).json()
        self.assertEqual(result["actions"]["swing"],"UNKNOWN")
        self.assertEqual(result["frozen_signals"],[])
    def test_future_confirmation(self):
        self.assertEqual(self.request(dict(self.confirmation,available_at="2025-01-07T17:00:00+05:45")).status_code,422)
    def test_weak_market(self):
        self.snapshot["market"]["regime"]="markdown"
        result=self.request(self.confirmation).json()
        self.assertEqual(result["frozen_signals"],[])
