import unittest
from app.scanner_personalized_guard import personalized_guard
class HoldingGuardTests(unittest.TestCase):
    def test_stop_without_brokers(self):
        now="2026-11-19T16:00:00+05:45"
        evidence=dict(status="verified",source_id="synthetic",available_at=now,symbol="CFCL",basis_id="reviewed")
        holding=dict(evidence,horizon="swing",quantity=2500,average_cost=490,stop=480)
        quote=dict(evidence,close=470,observed_at=now)
        result=personalized_guard(holding=holding,quote=quote,assessment_time=now)
        self.assertEqual(result["action"],"EXIT_REVIEW")
        self.assertEqual(result["trap_status"],"UNKNOWN")
        self.assertFalse(result["execution_eligible"])
