import unittest
from datetime import date, timedelta
from app.structure_timeframes import evaluate_timeframes, completed_months

def fixture():
    start = date(2025,1,5)
    return [dict(date=start+timedelta(days=7*w+d),open=100+w,
                 high=102+w,low=98+w,close=101+w,volume=100)
            for w in range(6) for d in range(5)]

class TimeframeTests(unittest.TestCase):
    def test_unverified_rows_are_blocked(self):
        self.assertEqual(evaluate_timeframes(fixture())["status"],"unavailable")
    def test_missing_calendar_blocks_weekly(self):
        result=evaluate_timeframes(fixture(),eligible=True)
        self.assertEqual(result["weekly_completed_bars"],0)
        self.assertIsNone(result["score"])
    def test_current_week_excluded(self):
        rows=fixture()
        result=evaluate_timeframes(rows,eligible=True,verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["weekly_completed_bars"],5)
        self.assertEqual(result["t_plus_2"]["action"],"NO TRADE")
    def test_missing_week_resets_history(self):
        rows=fixture()
        observed=rows[:10]+rows[15:]
        result=evaluate_timeframes(observed,eligible=True,verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["weekly_completed_bars"],2)
    def test_incomplete_week_resets_history(self):
        rows=fixture()
        result=evaluate_timeframes(rows[:19]+rows[20:],eligible=True,verified_sessions=[r["date"] for r in rows])
        self.assertEqual(result["weekly_completed_bars"],1)

class MonthlyTests(unittest.TestCase):
    def fixture(self):
        return [dict(date=date(2025,m,d),open=100+d,high=110+d,low=90+d,close=105+d,volume=10*d)
                for m in range(1,5) for d in (5,6,7)]
    def test_aggregation(self):
        rows=self.fixture()
        bars=completed_months(rows,[r["date"] for r in rows])
        self.assertEqual(len(bars),3)
        self.assertEqual(bars[0],dict(date=date(2025,1,7),open=105,high=117,low=95,close=112,volume=180))
    def test_missing_calendar(self):
        self.assertEqual(completed_months(self.fixture(),None),[])
    def test_missing_session(self):
        rows=self.fixture()
        self.assertEqual(len(completed_months(rows[:4]+rows[5:],[r["date"] for r in rows])),1)
    def test_missing_month(self):
        rows=self.fixture()
        self.assertEqual(len(completed_months(rows[:3]+rows[6:],[r["date"] for r in rows])),1)
    def test_duplicate(self):
        rows=self.fixture()
        self.assertEqual(len(completed_months(rows[:4]+[rows[3]]+rows[4:],[r["date"] for r in rows])),1)
