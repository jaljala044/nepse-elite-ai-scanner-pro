import unittest
from app.scanner_performance_review import performance_review
from app.scanner_common_cohort import METHODS
class PerformanceTests(unittest.TestCase):
    def test_purge(self):
        key=("API","T+2","2026-11-16T17:00:00+05:45")
        reviews={m:dict(direction="UNKNOWN") for m in METHODS}
        reviews["BROKER"]=dict(direction="BULLISH",candidate_decision=dict(action="BUY_REVIEW"))
        reviews["SMC"]=dict(direction="NEUTRAL")
        scenario=dict(status="scenario_completed",symbol="API",horizon="T+2",outcome_available_at="2026-11-20T17:00:00+05:45",net_pnl=10,net_return_pct=1)
        r=performance_review(dict(rows=[dict(key=key,reviews=reviews)]),{("BROKER",key):scenario},test_start="2026-11-19T17:00:00+05:45",assessment_time="2026-11-21T17:00:00+05:45")
        self.assertEqual(r["methods"]["BROKER"]["purged"],1)
        self.assertEqual(r["methods"]["SMC"]["abstained"],1)
        self.assertEqual(r["methods"]["IDPAT"]["unknown"],1)
        self.assertIsNone(r["ranking"])
