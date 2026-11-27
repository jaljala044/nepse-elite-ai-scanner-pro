import unittest
from app.corporate_action_trade_plan import rebase_trade_plan

class CorporateActionTradePlanTests(unittest.TestCase):
    def setUp(self):
        self.signal = dict(symbol="AAA", decision_time="2025-01-01T15:00:00+05:45",
            details={"plan":{"entry":"400","stop":"360","targets":["480","520","560"]}})
        self.action = dict(symbol="AAA", action_id="A", action_type="bonus", ratio="0.25",
            status="verified", source_id="synthetic",
            available_at="2025-01-02T10:00:00+05:45",
            price_basis_effective_at="2025-01-03T10:00:00+05:45")
    def run_plan(self, **overrides):
        args = dict(signal=self.signal, action=self.action, quantity=100,
            cost_basis=40000, adjustment_time="2025-01-03T15:00:00+05:45")
        args.update(overrides)
        return rebase_trade_plan(**args)
    def test_bonus(self):
        result = self.run_plan()
        self.assertEqual(result["theoretical_quantity"],125)
        self.assertEqual(result["adjusted_signal"]["details"]["plan"]["entry"],"3.2E+2")
        self.assertEqual(result["reward_risk"],["2","3","4"])
        self.assertEqual(self.signal["details"]["plan"]["entry"],"400")
        self.assertFalse(result["execution_eligible"])
    def test_split(self):
        result = self.run_plan(action=dict(self.action,action_type="split",ratio="2"))
        self.assertEqual(result["theoretical_quantity"],200)
    def test_future_evidence(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            self.run_plan(adjustment_time="2025-01-01T16:00:00+05:45")
    def test_rights_rejected(self):
        with self.assertRaisesRegex(ValueError,"separate_valuation"):
            self.run_plan(action=dict(self.action,action_type="rights"))
    def test_fractional_entitlement(self):
        with self.assertRaisesRegex(ValueError,"fractional_entitlement"):
            self.run_plan(quantity=101)

    def cash_plan(self, **overrides):
        from app.corporate_action_trade_plan import rebase_cash_action_plan
        args = dict(signal=self.signal, action=dict(self.action,action_type="rights",
                    ratio="0.5",subscription_price="100"), quantity=100,
                    cost_basis=40000, available_cash=5000, subscribed_quantity=50,
                    reference=dict(symbol="AAA",status="verified",source_id="synthetic-close",
                        close=400, observed_at="2025-01-02T15:00:00+05:45",
                        available_at="2025-01-02T16:00:00+05:45"),
                    adjustment_time="2025-01-03T15:00:00+05:45")
        args.update(overrides)
        return rebase_cash_action_plan(**args)
    def test_rights_terp(self):
        result = self.cash_plan()
        self.assertEqual(float(result["theoretical_ex_price"]),300)
        self.assertEqual(result["theoretical_quantity"],150)
        self.assertEqual(float(result["subscription_cash"]),5000)
        self.assertEqual(float(result["theoretical_cost_basis"]),45000)
        self.assertEqual(float(result["cash_after_subscription"]),0)
        self.assertEqual(result["reward_risk"],["2","3","4"])
    def test_insufficient_funding(self):
        with self.assertRaisesRegex(ValueError,"insufficient_subscription_cash"):
            self.cash_plan(available_cash=4999)
    def test_excess_entitlement(self):
        with self.assertRaisesRegex(ValueError,"subscription_exceeds"):
            self.cash_plan(subscribed_quantity=51)
    def test_dividend_receivable_not_cash(self):
        result = self.cash_plan(action=dict(self.action,action_type="cash_dividend",
                                cash_per_share=10),subscribed_quantity=0)
        self.assertEqual(float(result["theoretical_ex_price"]),390)
        self.assertEqual(float(result["gross_dividend_receivable"]),1000)
        self.assertEqual(float(result["cash_after_subscription"]),5000)
        self.assertEqual(result["theoretical_quantity"],100)
