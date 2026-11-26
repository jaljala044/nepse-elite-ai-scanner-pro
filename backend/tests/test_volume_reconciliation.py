import unittest
from app.volume_reconciliation import reconcile_volume

class VolumeReconciliationTests(unittest.TestCase):
    def compare(self, **kwargs):
        return reconcile_volume("BNL", "2026-07-24", **kwargs)

    def test_zero_is_not_missing_or_replaced(self):
        r=self.compare(chart_volume=0,floorsheet_volume=10,chart_evidence="chart",floorsheet_evidence="floor")
        self.assertEqual(r["chart_volume"],0)
        self.assertEqual(r["volume_difference"],10)
        self.assertEqual(r["reconciliation_status"],"volume_conflict")

    def test_missing_is_not_zero(self):
        r=self.compare(floorsheet_volume=10,floorsheet_evidence="floor")
        self.assertIsNone(r["chart_volume"])
        self.assertIsNone(r["volume_difference"])

    def test_numeric_match_does_not_promote(self):
        r=self.compare(chart_volume="10.0",floorsheet_volume=10,chart_evidence="chart",floorsheet_evidence="floor")
        self.assertEqual(r["reconciliation_status"],"numeric_match")
        self.assertIsNone(r["verified_market_volume"])
        self.assertFalse(r["canonical_promotion_allowed"])
        self.assertFalse(r["backtest_promotion_allowed"])

    def test_external_corroboration_retained_separately(self):
        r=self.compare(chart_volume=0,floorsheet_volume=10,corroborated_volume=10,chart_evidence="chart",floorsheet_evidence="floor",corroboration_evidence="report")
        self.assertTrue(r["external_matches_floorsheet"])
        self.assertIsNone(r["verified_market_volume"])
        self.assertEqual(r["chart_volume"],0)

    def test_evidence_required(self):
        with self.assertRaises(ValueError):
            self.compare(chart_volume=10)

    def test_invalid_volume(self):
        for v in [-1,"NaN","Infinity","1.5",True]:
            with self.subTest(v=v), self.assertRaises(ValueError):
                self.compare(chart_volume=v,chart_evidence="chart")

    def test_external_disagreement(self):
        r=self.compare(floorsheet_volume=10,corroborated_volume=11,floorsheet_evidence="floor",corroboration_evidence="report")
        self.assertFalse(r["external_matches_floorsheet"])
        self.assertFalse(r["canonical_promotion_allowed"])
