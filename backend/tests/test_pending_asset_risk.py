import unittest
from app.pending_asset_risk import review_pending_asset_risk

class PendingAssetRiskTests(unittest.TestCase):
    def setUp(self):
        self.now="2024-05-07T17:00:00+05:45"
        self.e=dict(status="verified",source_id="synthetic",available_at=self.now)
        self.snapshot=dict(self.e,available_cash=10000,peak_equity=20000,
            corporate_asset_balance_basis="confirmed_receipts_and_payments_included_pending_assets_excluded",
            positions=[dict(self.e,symbol="AAA",sector="Hydro",quantity=100,mark=100,stop=95)])
        self.limits=dict(max_position_pct=.8,max_sector_pct=.8,risk_per_trade_pct=.1,max_drawdown_pct=.2)
        self.assets=[dict(self.e,action_id="D",symbol="AAA",action_type="dividend",record_date="2024-05-01",due_date="2024-05-06",gross_amount=1000)]
    def review(self,assets=None):
        return review_pending_asset_risk(snapshot=self.snapshot,limits=self.limits,
            entitlements=self.assets if assets is None else assets,confirmations=[],assessment_time=self.now)
    def test_pending_blocks(self):
        r=self.review()
        self.assertFalse(r["new_entries_allowed_by_risk_gate"])
        self.assertEqual(r["conservative_risk_equity"],20000)
        self.assertIsNone(r["complete_portfolio_fair_value"])
    def test_clear(self):
        self.assertTrue(self.review([])["new_entries_allowed_by_risk_gate"])
    def test_funding(self):
        self.snapshot["pending_rights_payment"]=12000
        r=self.review([])
        self.assertEqual(r["spendable_cash_after_commitments"],"0")
        self.assertFalse(r["new_entries_allowed_by_risk_gate"])
    def test_exit_preserved(self):
        self.snapshot["positions"][0]["stop"]=105
        self.assertEqual(self.review()["base_risk"]["alerts"][0]["action"],"EXIT_REVIEW")
    def test_basis_required(self):
        del self.snapshot["corporate_asset_balance_basis"]
        with self.assertRaisesRegex(ValueError,"corporate_asset_balance_basis_required"): self.review()
