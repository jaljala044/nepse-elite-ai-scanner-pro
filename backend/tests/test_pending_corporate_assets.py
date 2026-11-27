import unittest
from decimal import Decimal
from app.pending_corporate_assets import review_pending_assets

class PendingAssetsTests(unittest.TestCase):
    def setUp(self):
        self.now="2024-05-07T17:00:00+05:45"
        self.e=dict(status="verified",source_id="synthetic",available_at=self.now)
        base=dict(self.e,symbol="AAA",record_date="2024-05-01",due_date="2024-05-06")
        self.assets=[dict(base,action_id="D",action_type="dividend",gross_amount=6000),
            dict(base,action_id="B",action_type="bonus",quantity=200),
            dict(base,action_id="R",action_type="rights",quantity=200,payment_evidence=dict(self.e,action_id="R",symbol="AAA",payment_date="2024-05-05",amount=20000))]
    def review(self,confirmations):
        return review_pending_assets(entitlements=self.assets,confirmations=confirmations,assessment_time=self.now)
    def test_pending(self):
        r=self.review([])
        self.assertEqual(Decimal(r["confirmed_cash_receipt_delta"]),0)
        self.assertEqual(Decimal(r["pending_gross_dividends"]),6000)
        self.assertEqual(Decimal(r["pending_paid_rights_at_cost"]),20000)
        self.assertEqual(r["unknown_valuation_action_ids"],["B"])
        self.assertIsNone(r["complete_fair_value"])
    def test_confirmed(self):
        c=dict(self.e,symbol="AAA",effective_date="2024-05-06")
        r=self.review([dict(c,action_id="D",event_type="cash_received",net_amount=5700),
            dict(c,action_id="R",event_type="shares_credited",quantity=200)])
        self.assertEqual(Decimal(r["confirmed_cash_receipt_delta"]),5700)
        self.assertEqual(r["confirmed_share_credit_delta"],{"AAA":200})
        self.assertEqual(Decimal(r["pending_paid_rights_at_cost"]),0)
        self.assertEqual(Decimal(r["pending_gross_dividends"]),0)
    def test_excess_receipt(self):
        with self.assertRaisesRegex(ValueError,"receipt_exceeds_entitlement"):
            self.review([dict(self.e,action_id="D",symbol="AAA",effective_date="2024-05-06",event_type="cash_received",net_amount=6001)])
    def test_duplicate(self):
        self.assets.append(self.assets[0])
        with self.assertRaisesRegex(ValueError,"duplicate_entitlement"): self.review([])
    def test_future_confirmation(self):
        with self.assertRaisesRegex(ValueError,"confirmation_lookahead"):
            self.review([dict(self.e,action_id="D",available_at="2024-05-08T17:00:00+05:45")])
