import unittest
from unittest.mock import patch
from app.scanner_trap_confluence import trap_confluence
class TrapTests(unittest.TestCase):
    @patch("app.scanner_trap_confluence.review_liquidity_trap")
    @patch("app.scanner_trap_confluence.breakout_guard")
    def test_guard(self,guard,trap):
        args=dict(symbol="API",rows=[],benchmark_rows=[],sessions=[],decision_time="",calendar_evidence={},broker_records=[],broker_numbers=[])
        guard.return_value={"status":"UNKNOWN"}
        self.assertEqual(trap_confluence(**args)["status"],"UNKNOWN")
        trap.assert_not_called()
        guard.return_value={"status":"FAILED_BREAKOUT"}
        trap.return_value=dict(flags={"persistent_broker_selling":True},action="UNKNOWN",complete_evidence=False)
        self.assertEqual(trap_confluence(**args)["status"],"HIGH_RISK_REVIEW")
