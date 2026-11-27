import unittest
from datetime import date,timedelta
from app.liquidity_trap_review import review_liquidity_trap
from app.dynamic_exit_plan import dynamic_exit_plan

class LiquidityTrapIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.days=[str(date(2024,1,1)+timedelta(days=i)) for i in range(60)]
        def bars(symbol):
            return [dict(symbol=symbol,date=d,open=100,high=102,low=98,close=100,volume=1000,
                status="verified",source_id="synthetic",basis_id="B",price_basis="corporate_action_reviewed",
                available_at=d+"T16:00:00+05:45") for d in self.days]
        self.rows=bars("AAA")
        self.rows[-1].update(open=102,high=110,low=98,close=99,volume=3000)
        self.args=dict(symbol="AAA",rows=self.rows,benchmark_rows=bars("NEPSE"),sessions=self.days,
                       assessment_time=self.days[-1]+"T17:00:00+05:45")
        self.brokers=[dict(symbol="AAA",date=d,broker_numbers=[1],complete=True,buy_turnover=20,
            sell_turnover=80,close=r["close"],status="verified",source_id="synthetic-broker",
            available_at=d+"T16:00:00+05:45") for d,r in zip(self.days,self.rows)]
    def test_distribution_confluence(self):
        result=review_liquidity_trap(**self.args,broker_records=self.brokers,broker_numbers=[1])
        self.assertEqual(result["action"],"DISTRIBUTION_RISK_REVIEW")
        self.assertTrue(result["flags"]["upthrust"])
        self.assertFalse(result["execution_eligible"])
    def test_missing_broker_history(self):
        result=review_liquidity_trap(**self.args,broker_records=self.brokers[:-1],broker_numbers=[1])
        self.assertEqual(result["action"],"STRUCTURAL_WARNING")
        self.assertIsNone(result["flags"]["persistent_broker_selling"])
    def test_trailing_profit_booking(self):
        result=dynamic_exit_plan(**self.args,original_quantity=100,remaining_quantity=80,
            previous_stop=90,targets=[95,105,115],cumulative_fractions=[.3,.6,1],horizon="swing")
        self.assertEqual(result["suggested_sale_quantity"],10)
        self.assertGreaterEqual(float(result["next_stop"]),90)
        self.assertFalse(result["execution_eligible"])
