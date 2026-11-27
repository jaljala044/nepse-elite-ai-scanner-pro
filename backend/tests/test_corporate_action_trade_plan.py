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
