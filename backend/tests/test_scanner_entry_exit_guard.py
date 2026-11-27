import unittest
from unittest.mock import patch
from app.scanner_entry_exit_guard import review_entry_exit
class EntryExitTests(unittest.TestCase):
    @patch("app.scanner_entry_exit_guard.dynamic_exit_plan")
    @patch("app.scanner_entry_exit_guard.trap_confluence")
    def test_unknown(self,trap,exit_plan):
        trap.return_value={"status":"UNKNOWN"}
        result=review_entry_exit(trap_inputs={},exit_inputs={})
        self.assertEqual(result["entry_action"],"NO_TRADE")
        exit_plan.assert_not_called()
    @patch("app.scanner_entry_exit_guard.trap_confluence")
    def test_mismatch(self,trap):
        trap.return_value={"status":"WAIT"}
        with self.assertRaises(ValueError):
            review_entry_exit(trap_inputs={"symbol":"API"},exit_inputs={"symbol":"CFCL"})
