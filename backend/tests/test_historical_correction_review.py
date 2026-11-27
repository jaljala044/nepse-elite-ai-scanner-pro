import unittest
from app.historical_correction_review import review_corrections

class HistoricalCorrectionReviewTests(unittest.TestCase):
    def fixture(self):
        return dict(symbol="RAWA",date="2026-04-29",open="610",high="610",low="587",close="610",volume="2840",source_sha256="a"*64,contracts=58,target_errors=0,session_errors=0)
    def test_self_attestation_cannot_release(self):
        row=self.fixture()
        row.update(admission_allowed=True,independent_provider_confirmed=True,execution_order_verified=True)
        result=review_corrections([row])
        self.assertEqual(result["approved_corrections"],[])
        self.assertFalse(result["records"][0]["admission_allowed"])
    def test_duplicates_and_invalid_candles(self):
        row=self.fixture()
        bad=dict(row,open="999",session_errors=1)
        result=review_corrections([row,bad])
        self.assertIn("duplicate_key",result["records"][1]["reasons"])
        self.assertIn("invalid_ohlcv",result["records"][1]["reasons"])
        self.assertIn("session_validation_failed",result["records"][1]["reasons"])
    def test_malformed_and_unknown(self):
        for row in [None,{},dict(self.fixture(),symbol="UNKNOWN"),dict(self.fixture(),volume="NaN")]:
            self.assertFalse(review_corrections([row])["records"][0]["admission_allowed"])
    def test_empty(self):
        self.assertEqual(review_corrections([])["approved_corrections"],[])
