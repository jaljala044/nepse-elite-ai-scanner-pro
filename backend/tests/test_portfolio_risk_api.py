import unittest
from fastapi.testclient import TestClient
from app.main import app

class PortfolioRiskApiTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.evidence=dict(status="verified",source_id="synthetic",available_at="2025-01-01T15:00:00+05:45")
    def test_risk_review(self):
        response=self.client.post("/v1/research/portfolio/risk-review",json={
            "snapshot":dict(self.evidence,available_cash=40000,peak_equity=50000,
                positions=[dict(self.evidence,symbol="AAA",sector="Hydropower",quantity=100,mark=100,stop=95)]),
            "limits":dict(max_position_pct=.25,max_sector_pct=.4,risk_per_trade_pct=.02,max_drawdown_pct=.15),
            "assessment_time":"2025-01-02T15:00:00+05:45"})
        self.assertEqual(response.status_code,200)
        result=response.json()
        self.assertEqual(result["alerts"][0]["action"],"HOLD_REVIEW")
        self.assertEqual(result["broker_intelligence_status"],"UNKNOWN")
        self.assertFalse(result["live_notifications_enabled"])
    def test_invalid_snapshot(self):
        response=self.client.post("/v1/research/portfolio/risk-review",json={
            "snapshot":{},"limits":{},"assessment_time":"2025-01-02T15:00:00+05:45"})
        self.assertEqual(response.status_code,422)
    def test_bonus_plan(self):
        response=self.client.post("/v1/research/portfolio/adjust-plan",json={
            "signal":dict(symbol="AAA",decision_time="2025-01-01T15:00:00+05:45",
                details={"plan":{"entry":"400","stop":"360","targets":["480"]}}),
            "action":dict(self.evidence,symbol="AAA",action_id="B",action_type="bonus",ratio=.25,
                price_basis_effective_at="2025-01-02T10:00:00+05:45"),
            "adjustment_time":"2025-01-02T15:00:00+05:45","quantity":100,"cost_basis":40000})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["theoretical_quantity"],125)
        self.assertFalse(response.json()["execution_eligible"])
