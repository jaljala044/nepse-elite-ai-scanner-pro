import unittest
from app.scanner_common_cohort import METHODS,run_common_cohort
from app.scanner_cohort_metrics import audit_cohort

class CohortTests(unittest.TestCase):
    def test_master_not_independent_vote(self):
        d=dict(symbol="ABC",horizon="swing",decision_time="2025-01-01T12:00:00Z")
        adapters={m:(lambda x,m=m:dict(symbol=x["symbol"],horizon=x["horizon"],available_at=x["decision_time"],evidence_id=m,direction="BEARISH" if m=="MASTER" else "BULLISH")) for m in METHODS}
        result=run_common_cohort([d],adapters)
        self.assertEqual(result["rows"][0]["confluence"]["state"],"ALIGNED")
        self.assertEqual(audit_cohort(result)["complete_decisions"],1)
        with self.assertRaises(ValueError): run_common_cohort([d,d],adapters)
