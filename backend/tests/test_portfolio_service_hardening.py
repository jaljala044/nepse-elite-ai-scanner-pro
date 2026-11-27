import unittest
from app.nepse_settlement_tax_review import review_settlement_tax
from app.portfolio_reconciliation_service import review_owned_portfolio

class ServiceHardeningTests(unittest.TestCase):
    def inputs(self):
        days=["2025-01-05","2025-01-06","2025-01-07"]
        now="2025-01-07T18:00:00+05:45"
        ev=dict(status="verified",source_id="synthetic",available_at=now)
        return dict(trade_date=days[0],settlement_date=days[2],sessions=days,
            calendar_evidence=dict(ev,sessions=days),tax_schedule=dict(ev,effective_from=days[0],effective_to=days[2],investor_category="test",rate=".05"),
            assessment_time=now,net_proceeds=1200,allocated_cost=1000,investor_category="test")
    def test_tax(self):
        self.assertEqual(review_settlement_tax(**self.inputs())["estimated_tax"],"10.00")
    def test_loss(self):
        x=self.inputs(); x["net_proceeds"]=900
        self.assertEqual(float(review_settlement_tax(**x)["estimated_tax"]),0)
    def test_wrong_category(self):
        x=self.inputs(); x["investor_category"]="other"
        with self.assertRaisesRegex(ValueError,"tax_schedule_not_applicable"): review_settlement_tax(**x)
    def test_wrong_settlement(self):
        x=self.inputs(); x["settlement_date"]=x["sessions"][1]
        with self.assertRaisesRegex(ValueError,"invalid_t_plus_two"): review_settlement_tax(**x)
    def test_unauthorized_no_snapshot_read(self):
        def forbidden(_): self.fail("unauthorized snapshot read")
        with self.assertRaises(PermissionError):
            review_owned_portfolio(principal_id="A",portfolio_id="P",ownership_lookup=lambda _:"B",snapshot_lookup=forbidden)
    def test_wrong_snapshot_identity(self):
        with self.assertRaisesRegex(ValueError,"portfolio_snapshot_unavailable"):
            review_owned_portfolio(principal_id="A",portfolio_id="P",ownership_lookup=lambda _:"A",snapshot_lookup=lambda _:{"portfolio_id":"Q"})
