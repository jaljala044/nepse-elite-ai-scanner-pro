import unittest
from app.scanner_calendar_audit import candidate,audit_dates

class CalendarAuditTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertTrue(candidate("2026-04-05"))
        self.assertFalse(candidate("2026-04-12"))
        self.assertTrue(candidate("2026-04-10"))
        self.assertTrue(candidate("2022-09-16"))
        self.assertFalse(candidate("2022-09-17"))
    def test_gate(self):
        self.assertFalse(audit_dates(["2026-04-10"],["2026-04-10"])["backtest_eligible"])
