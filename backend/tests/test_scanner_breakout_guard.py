import unittest
from datetime import date,timedelta
from app.scanner_breakout_guard import breakout_guard
class BreakoutTests(unittest.TestCase):
    def test_failed(self):
        days=[str(date(2026,10,1)+timedelta(days=i)) for i in range(23)]
        rows=[dict(symbol="API",date=d,open=100,high=105,low=95,close=100,volume=100,status="verified",source_id="synthetic",observed_at=d+"T15:00:00+05:45",available_at=d+"T16:00:00+05:45",price_basis="corporate_action_reviewed",basis_id="synthetic") for d in days]
        rows[-3].update(high=112,close=110,volume=200)
        cutoff=days[-1]+"T17:00:00+05:45"
        result=breakout_guard(symbol="API",rows=rows,sessions=days,decision_time=cutoff,calendar_evidence=dict(status="verified",source_id="synthetic",available_at=cutoff,sessions=days))
        self.assertEqual(result["status"],"FAILED_BREAKOUT")
        self.assertEqual(result["action"],"NO_TRADE")
