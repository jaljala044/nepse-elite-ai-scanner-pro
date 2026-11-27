import unittest
from decimal import Decimal
from app.corporate_action_lot_adjustment import adjust_record_date_lots

class CorporateActionLotTests(unittest.TestCase):
    def setUp(self):
        self.now="2024-05-07T17:00:00+05:45"
        self.e=dict(status="verified",source_id="synthetic",available_at=self.now)
        self.lots=[dict(self.e,lot_id="A",symbol="AAA",quantity=1000,total_cost=200000,
            settlement_date="2024-05-01",snapshot_date="2024-05-02",unchanged_through_effective_date=True)]
    def run_action(self,kind,**terms):
        action=dict(self.e,action_id="X",symbol="AAA",action_type=kind,record_date="2024-05-02",
            listing_date="2024-05-07",payment_date="2024-05-07",**terms)
        return adjust_record_date_lots(lots=self.lots,action=action,assessment_time=self.now,available_cash=30000)
    def test_bonus(self):
        r=self.run_action("bonus",ratio=".2")
        self.assertEqual(r["lots"][0]["quantity"],1200)
        self.assertEqual(Decimal(r["lots"][0]["total_cost"]),200000)
    def test_split(self):
        self.assertEqual(self.run_action("split",ratio=2)["lots"][0]["quantity"],2000)
    def test_dividend(self):
        self.assertEqual(Decimal(self.run_action("dividend",cash_per_share=10)["available_cash"]),40000)
    def test_rights(self):
        r=self.run_action("rights",ratio=".2",subscription_price=100,subscriptions={"A":200},subscription_payment_date="2024-05-05")
        self.assertEqual(r["lots"][0]["quantity"],1200)
        self.assertEqual(Decimal(r["lots"][0]["total_cost"]),220000)
        self.assertEqual(Decimal(r["available_cash"]),10000)
    def test_intervening_trade(self):
        self.lots[0]["unchanged_through_effective_date"]=False
        with self.assertRaisesRegex(ValueError,"intervening_lot_events"): self.run_action("bonus",ratio=".2")
    def test_duplicate_action(self):
        self.lots[0]["applied_action_ids"]=["X"]
        with self.assertRaisesRegex(ValueError,"action_already_applied"): self.run_action("bonus",ratio=".2")
    def test_fractional(self):
        with self.assertRaisesRegex(ValueError,"fractional_entitlement"): self.run_action("bonus",ratio=".0005")
