import unittest
from app.corporate_action_risk import assess_post_action_risk

class CorporateActionRiskTests(unittest.TestCase):
    def setUp(self):
        self.evidence = dict(status="verified",source_id="synthetic",
                             available_at="2025-01-01T15:00:00+05:45")
        self.position = dict(self.evidence,symbol="AAA",sector="Hydropower",
                             quantity=100,mark=100,stop=95)
        self.snapshot = dict(self.evidence,available_cash=40000,receivables=0,
                             peak_equity=50000,positions=[self.position])
        self.limits = dict(max_position_pct=.25,max_sector_pct=.4,
                           risk_per_trade_pct=.02,max_drawdown_pct=.15)
    def assess(self, **changes):
        return assess_post_action_risk(snapshot=dict(self.snapshot,**changes),
            limits=self.limits,assessment_time="2025-01-02T15:00:00+05:45")
    def test_hold(self):
        result=self.assess()
        self.assertEqual(result["alerts"][0]["action"],"HOLD_REVIEW")
        self.assertTrue(result["new_entries_allowed_by_risk_gate"])
    def test_concentration(self):
        result=self.assess(positions=[dict(self.position,quantity=300)])
        self.assertEqual(result["alerts"][0]["action"],"REDUCE_REVIEW")
        self.assertIn("stock_concentration",result["alerts"][0]["reasons"])
    def test_stop_breach(self):
        self.assertEqual(self.assess(positions=[dict(self.position,mark=90)])["alerts"][0]["action"],"EXIT_REVIEW")
    def test_receivables_not_funding(self):
        result=self.assess(pending_rights_payment=45000,receivables=10000)
        self.assertEqual(result["rights_funding_shortfall"],5000)
        self.assertFalse(result["new_entries_allowed_by_risk_gate"])
    def test_drawdown(self):
        self.assertTrue(self.assess(peak_equity=60000)["circuit_breaker"])
    def test_missing_stop(self):
        self.assertEqual(self.assess(positions=[dict(self.position,stop=None)])["alerts"][0]["action"],"WAIT")
    def test_future_evidence(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            self.assess(positions=[dict(self.position,available_at="2025-01-03T15:00:00+05:45")])
