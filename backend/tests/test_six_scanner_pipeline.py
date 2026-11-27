import unittest
from app.six_scanner_pipeline import run_six_scanners
from app.scanner_common_cohort import METHODS

class SixScannerTests(unittest.TestCase):
    def test_missing(self):
        days=["2025-01-01"]
        result=run_six_scanners(symbol="ABC",rows=[],benchmark_rows=[],sessions=days,decision_time="2025-01-02T00:00:00Z",calendar_evidence=dict(status="verified",source_id="synthetic",available_at="2025-01-01T12:00:00Z",sessions=days),broker_records=[],feature_inputs={},horizon="swing")
        self.assertEqual(set(result["reviews"]),set(METHODS))
        self.assertTrue(all(r["action"]=="NO_TRADE" for r in result["reviews"].values()))
