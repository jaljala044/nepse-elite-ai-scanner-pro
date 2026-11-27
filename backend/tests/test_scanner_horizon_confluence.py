import unittest
from app.scanner_horizon_confluence import horizon_confluence,HORIZONS
from app.scanner_common_cohort import METHODS
class HorizonTests(unittest.TestCase):
    def test_conflict(self):
        reviews={h:{m:dict(direction="BULLISH") for m in METHODS} for h in HORIZONS}
        reviews["positional"]["BROKER"]["direction"]="BEARISH"
        reviews["investment"]["IDPAT"]["direction"]="UNKNOWN"
        result=horizon_confluence(reviews)["methods"]
        self.assertEqual(result["BROKER"]["gates"]["T+2"]["status"],"CONFLICT")
        self.assertEqual(result["IDPAT"]["gates"]["swing"]["status"],"UNKNOWN")
        self.assertTrue(result["SMC"]["gates"]["T+2"]["bullish_alignment"])
