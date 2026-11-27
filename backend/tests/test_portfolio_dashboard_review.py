import unittest
from copy import deepcopy
from app.portfolio_dashboard_review import portfolio_dashboard_review

class PortfolioDashboardTests(unittest.TestCase):
    def setUp(self):
        day="2024-05-02"
        now=day+"T17:00:00+05:45"
        def evidence(**kw):
            return dict(status="verified",source_id="synthetic",available_at=now,as_of_session=day,**kw)
        self.args=dict(
            holding=evidence(symbol="AAA",quantity=100,settled_quantity=60,average_cost=90,basis_id="B",horizon="swing",stop=105),
            quote=evidence(symbol="AAA",basis_id="B",close=100,observed_at=now),
            snapshot=evidence(available_cash=10000,peak_equity=20000,positions=[
                evidence(symbol="AAA",sector="Hydro",quantity=100,mark=100,stop=105,basis_id="B")]),
            limits=dict(max_position_pct=.8,max_sector_pct=.8,risk_per_trade_pct=.05,max_drawdown_pct=.2),
            distribution=evidence(symbol="AAA",action="NO_CONFLUENCE_OBSERVED"),
            market=evidence(regime="bull"),sector=evidence(sector="Hydro",classification="Leading"),
            assessment_time=now,reduction_fraction=.3)
    def test_stop_precedence_and_settled_cap(self):
        result=portfolio_dashboard_review(**self.args)
        self.assertEqual(result["action"],"EXIT_REVIEW")
        self.assertEqual(result["adaptive_review"]["settled_share_capped_quantity"],60)
        self.assertFalse(result["execution_eligible"])
    def test_mismatch(self):
        args=deepcopy(self.args)
        args["quote"]["close"]=101
        with self.assertRaisesRegex(ValueError,"holding_snapshot_mismatch"):
            portfolio_dashboard_review(**args)
    def test_unknown_distribution(self):
        args=deepcopy(self.args)
        args["holding"]["stop"]=95
        args["snapshot"]["positions"][0]["stop"]=95
        args["distribution"]["action"]="UNKNOWN"
        self.assertEqual(portfolio_dashboard_review(**args)["action"],"UNKNOWN")

    def test_http_dashboard_contract(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client=TestClient(app)
        response=client.post("/v1/research/portfolio/dashboard",json=self.args)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["action"],"EXIT_REVIEW")
        self.assertFalse(response.json()["production_eligible"])
    def test_http_invalid_evidence(self):
        from fastapi.testclient import TestClient
        from app.main import app
        args=deepcopy(self.args)
        args["quote"]["available_at"]="2024-05-03T17:00:00+05:45"
        response=TestClient(app).post("/v1/research/portfolio/dashboard",json=args)
        self.assertEqual(response.status_code,422,response.text)
    def test_http_missing_required_field(self):
        from fastapi.testclient import TestClient
        from app.main import app
        args=deepcopy(self.args)
        del args["holding"]
        self.assertEqual(TestClient(app).post("/v1/research/portfolio/dashboard",json=args).status_code,422)
