import unittest
from app.scanner_date_reconciliation import reconcile_dates

class DateReconciliationTests(unittest.TestCase):
    def test_missing(self):
        result=reconcile_dates([dict(symbol="ABC",date="2026-07-25")],{},"2026-11-27T00:00:00Z")
        self.assertEqual(result["accepted"],[])
        self.assertEqual(result["quarantined"][0]["date"],"2026-07-25")
        self.assertFalse(result["production_eligible"])
