import unittest
from datetime import date, timedelta
from app.smc_multitimeframe import evaluate_multitimeframe, week_key

class MultiTimeframeTests(unittest.TestCase):
    def fixture(self):
        start=date(2026,3,1)
        days=[start+timedelta(days=i) for i in range(100)]
        days=[d for d in days if (d.weekday() in (6,0,1,2,3) if d<date(2026,4,6) else d.weekday()<5)]
        rows=[dict(date=str(d),open=100+i,high=102+i,low=99+i,close=101+i,volume=100) for i,d in enumerate(days)]
        return rows,[str(d) for d in days]
    def test_transition(self):
        self.assertEqual(week_key(date(2026,4,2)),date(2026,3,29))
        self.assertEqual(week_key(date(2026,4,10)),date(2026,4,6))
    def test_gate(self):
        rows,days=self.fixture()
        self.assertEqual(evaluate_multitimeframe(rows)["status"],"unavailable")
    def test_frames(self):
        rows,days=self.fixture()
        result=evaluate_multitimeframe(rows,eligible=True,verified_sessions=days,as_of=days[-1])
        self.assertEqual(result["status"],"research_only")
        self.assertGreater(result["timeframes"]["weekly"]["bars"],5)
        self.assertEqual(result["timeframes"]["monthly"]["bars"],3)
        self.assertIsNone(result["production_score"])
    def test_missing_session(self):
        rows,days=self.fixture()
        result=evaluate_multitimeframe(rows[:-3]+rows[-2:],eligible=True,verified_sessions=days,as_of=days[-1])
        self.assertEqual(result["timeframes"]["daily"]["bars"],2)
        self.assertEqual(result["missing_daily_sessions"],1)
    def test_cutoff(self):
        rows,days=self.fixture()
        a=evaluate_multitimeframe(rows,eligible=True,verified_sessions=days,as_of=days[-5])
        b=evaluate_multitimeframe(rows[:-4],eligible=True,verified_sessions=days,as_of=days[-5])
        self.assertEqual(a,b)
