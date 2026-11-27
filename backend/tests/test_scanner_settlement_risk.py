import unittest
from app.scanner_settlement_risk import review_locked_stop
from app.independent_scanner_review import resolve_reviews

class ScannerRiskTests(unittest.TestCase):
    def test_locked_breach(self):
        days=["2025-01-01","2025-01-02","2025-01-05"]
        rows=[dict(date=d,low=470,close=475,status="verified",source_id="synthetic",available_at=d+"T12:00:00Z") for d in days]
        result=review_locked_stop(entry_date=days[0],entry_price=490,stop=480,rows=rows,sessions=days,assessment_time="2025-01-06T00:00:00Z")
        self.assertEqual(result["status"],"LOCKED_STOP_RISK")
        self.assertEqual(result["subsequent_session_breaches"],[days[1]])
        self.assertIsNone(result["exit_fill"])
    def test_conflict(self):
        self.assertEqual(resolve_reviews({"IDPAT":"BULLISH","Wyckoff":"BEARISH"})["state"],"CONFLICTING")
    def test_missing(self):
        self.assertEqual(resolve_reviews({"IDPAT":"UNKNOWN"})["state"],"INCOMPLETE")
