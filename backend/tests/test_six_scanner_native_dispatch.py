import unittest
from unittest.mock import patch
from app.six_scanner_pipeline import run_six_scanners
class DispatchTests(unittest.TestCase):
    @patch("app.six_scanner_pipeline.native_reviews")
    @patch("app.six_scanner_pipeline.review_native")
    def test_complete(self,bridge,native):
        bridge.return_value={"status":"RESEARCH","IDPAT":{"review_id":"synthetic","result":{"plans":{"T+2":{}}}},"MASTER":{}}
        native.return_value={m:{"direction":"UNKNOWN","evidence":({"trend":{}} if m=="MINERVINI_MOMENTUM" else {})} for m in ("WYCKOFF","SMC","BROKER","MINERVINI_MOMENTUM")}
        result=run_six_scanners(symbol="API",rows=[],benchmark_rows=[],sessions=[],decision_time="synthetic",calendar_evidence={},broker_records=[],feature_inputs={},horizon="T+2")
        self.assertEqual(len(result["reviews"]),6)
        self.assertTrue(all(r["action"]=="NO_TRADE" for r in result["reviews"].values()))
