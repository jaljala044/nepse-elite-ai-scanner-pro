import unittest
from app.scanner_historical_evidence import validate_history
from app.scanner_delayed_exit import delayed_exit_reference

class HistoricalTests(unittest.TestCase):
    def test_missing(self):
        sessions=["2025-01-01"]
        calendar=dict(status="verified",source_id="synthetic",available_at="2025-01-01T12:00:00Z",sessions=sessions)
        self.assertEqual(validate_history([],sessions,"ABC","2025-01-02T00:00:00Z",calendar)["status"],"UNKNOWN")
    def test_delayed(self):
        days=["2025-01-01","2025-01-02","2025-01-05","2025-01-06"]
        rows=[dict(date=d,status="verified",source_id="synthetic",available_at=d+"T12:00:00Z",open=p,high=p,low=p,close=p,volume=100) for d,p in zip(days,[490,470,423,430])]
        result=delayed_exit_reference(entry_date=days[0],entry_price=490,stop=480,rows=rows,sessions=days,assessment_time="2025-01-07T00:00:00Z",price_bands={days[2]:dict(lower=423,upper=517),days[3]:dict(lower=381,upper=465)})
        self.assertEqual(result["locked_sessions"],[days[2]])
        self.assertEqual(result["exit_reference_date"],days[3])
        self.assertIsNone(result["exit_fill"])
