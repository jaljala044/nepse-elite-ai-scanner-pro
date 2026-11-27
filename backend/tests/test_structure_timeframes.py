import unittest
from datetime import date, timedelta
from app.structure_timeframes import evaluate_timeframes

def fixture():
    start = date(2025,1,5)
    return [dict(date=start+timedelta(days=7*w+d),open=100+w,
                 high=102+w,low=98+w,close=101+w,volume=100)
            for w in range(6) for d in range(5)]

class TimeframeTests(unittest.TestCase):
    def test_unverified_rows_are_blocked(self):
        self.assertEqual(evaluate_timeframes(fixture())["status"],"unavailable")
    def test_missing_calendar_blocks_weekly(self):
        result=evaluate_timeframes(fixture(),eligible=True,symbol="TEST")
        self.assertEqual(result["status"],"unavailable")
        self.assertIsNone(result["score"])
    def test_current_week_excluded(self):
        rows=fixture()
        result=evaluate_timeframes(rows,eligible=True,symbol="TEST",verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["weekly_completed_bars"],5)
        self.assertEqual(result["t_plus_2"]["action"],"NO TRADE")
    def test_missing_week_resets_history(self):
        rows=fixture()
        observed=rows[:10]+rows[15:]
        result=evaluate_timeframes(observed,eligible=True,symbol="TEST",verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["status"],"unavailable")
    def test_incomplete_week_resets_history(self):
        rows=fixture()
        result=evaluate_timeframes(rows[:19]+rows[20:],eligible=True,symbol="TEST",verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["status"],"unavailable")
