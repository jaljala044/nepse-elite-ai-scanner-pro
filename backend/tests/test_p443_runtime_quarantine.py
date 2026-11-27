import unittest
from datetime import date,timedelta
from app.historical_quarantine import QUARANTINE,window_errors
from app.scanner_eligibility import assess
from app.structure_timeframes import evaluate_timeframes
from app.historical_replay import replay

def bar(day):
    return dict(date=str(day),open=100,high=102,low=99,close=101,volume=100)

class QuarantineTests(unittest.TestCase):
    def test_all_keys(self):
        self.assertEqual(len(QUARANTINE),1329)
        for symbol,day in sorted(QUARANTINE):
            with self.subTest(symbol=symbol,day=day):
                self.assertIn("historical_quarantine:"+day,window_errors(symbol,[bar(day)],[day]))
                self.assertIn("historical_quarantine:"+day,assess(symbol,[bar(day)],day+"T23:59:59+05:45",{}))
                self.assertEqual(evaluate_timeframes([bar(day)],eligible=True,verified_sessions=[day],symbol=symbol)["status"],"unavailable")
    def test_omitted_key(self):
        symbol,day=next(iter(sorted(QUARANTINE)))
        d=date.fromisoformat(day)
        before=str(d-timedelta(days=1)); after=str(d+timedelta(days=1))
        self.assertIn("historical_quarantine:"+day,window_errors(symbol.lower(),[bar(before),bar(after)],[before,after]))
    def test_continuity(self):
        days=["2025-01-01","2025-01-02","2025-01-03"]
        rows=[bar(days[0]),bar(days[2])]
        self.assertIn("session_continuity_failed",window_errors("TEST",rows,days))
        self.assertIn("verified_session_calendar_required",window_errors("TEST",rows))
        self.assertIn("invalid_session_calendar",window_errors("TEST",rows,days[::-1]))
        self.assertTrue(window_errors("TEST",[rows[0],rows[0]],days))
        self.assertEqual(window_errors("TEST",[bar(d) for d in days],days),[])
    def test_replay(self):
        symbol,day=next(iter(sorted(QUARANTINE)))
        r=replay(symbol,[bar(day)],reviewed={},verified_sessions=[day])
        self.assertEqual(r["observations"],[])
        self.assertIn("historical_quarantine:"+day,r["excluded"][0]["reasons"])
if __name__=="__main__":unittest.main()
