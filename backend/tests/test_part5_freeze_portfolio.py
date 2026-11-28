import unittest
from datetime import date,timedelta
from app.part5_strategy_freeze import freeze_configuration,verify_configuration
from app.part5_portfolio_retry import replay_portfolio

class FreezeTests(unittest.TestCase):
    def fixture(self):
        return dict(strategy="research",methodology="v1",code_sha="a"*40,parameters={"stop":.05},
                    dataset_sha256="b"*64,frozen_at="2026-11-28T12:00:00Z",holdout_start="2026-12-01T00:00:00Z")
    def test_digest_and_tampering(self):
        frozen=freeze_configuration(**self.fixture())
        digest=frozen["freeze_sha256"]
        self.assertTrue(verify_configuration(frozen,expected_sha256=digest))
        frozen["record"]["parameters"]["stop"]=.1
        self.assertFalse(verify_configuration(frozen,expected_sha256=digest))
    def test_refreeze_not_same_commitment(self):
        a=self.fixture();f=freeze_configuration(**a)
        a["parameters"]["stop"]=.1
        self.assertFalse(verify_configuration(freeze_configuration(**a),expected_sha256=f["freeze_sha256"]))
    def test_holdout_after_freeze(self):
        a=self.fixture();a["holdout_start"]=a["frozen_at"]
        with self.assertRaises(ValueError): freeze_configuration(**a)

class PortfolioTests(unittest.TestCase):
    def test_retry_cash_conservation(self):
        days=[(date(2025,1,1)+timedelta(days=i)).isoformat() for i in range(12)]
        rows=[dict(date=d,open=100,high=102,low=98,close=100,volume=100000+i) for i,d in enumerate(days)]
        rows[2]["low"]=94
        rows[4].update(open=90,low=90,high=91,close=90)
        rows[5].update(open=91,low=90,high=92,close=91)
        costs=dict(buy_broker_rate=0,sell_broker_rate=0,regulatory_rate=0,sell_dp_charge=0,capital_gain_tax_rate=0,slippage_bps=0,min_broker_fee=0)
        result=replay_portfolio({"AAA":rows},days,{days[0]:["AAA"]},costs=costs,initial_capital=10000,allocation=.05,holding=5,retry=2)
        self.assertEqual(len(result["closed"]),1)
        self.assertEqual(result["closed"][0]["exit_date"],days[5])
        self.assertAlmostEqual(result["cash"],10000+result["realized_pnl"])
        self.assertFalse(result["production_eligible"])
    def test_no_signals(self):
        costs={}
        result=replay_portfolio({},["2025-01-01"],{},costs=costs)
        self.assertEqual(result["total_return_pct"],0)
