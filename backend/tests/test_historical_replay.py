import unittest
from datetime import date, timedelta
from app.historical_replay import replay, calendar_as_of

def fixture():
    rows=[]; reviewed={}
    for i in range(25):
        day=date(2025,1,1)+timedelta(days=i)
        row=dict(date=day,open=100+i,high=102+i,low=99+i,close=101+i,volume=100)
        rows.append(row)
        reviewed[("TEST",str(day))]=dict(row,symbol="TEST",date=str(day),security_id="fixture-security",
            instrument_type="equity",security_status="active",lifecycle_evidence_id="fixture-lifecycle",
            session_status="verified_open",session_evidence_id=f"fixture-session-{i}",
            source_id="sharehub",evidence_id=f"synthetic-{i}",source_payload_sha256="a"*64,
            price_basis_reviewed=True,price_basis_status="verified_unadjusted_no_actions",
            corporate_action_status="clear",corporate_action_evidence_id="fixture-action-review",
            available_at=f"{day}T11:00:00Z")
    return rows,reviewed

class ReplayTests(unittest.TestCase):
    def test_unreviewed_rows_excluded(self):
        rows,_=fixture()
        result=replay("TEST",rows,reviewed={})
        self.assertEqual(result["status"],"no_eligible_observations")
        self.assertEqual(len(result["excluded"]),25)
        self.assertIsNone(result["performance"])
    def test_prefix_invariance(self):
        rows,reviewed=fixture()
        day=rows[21]["date"]
        full=replay("TEST",rows,reviewed=reviewed,decision_dates=[day])
        short=replay("TEST",rows[:22],reviewed=reviewed,decision_dates=[day])
        self.assertEqual(full,short)
        self.assertEqual(full["observations"][0]["input_count"],22)
        self.assertEqual(full["observations"][0]["action"],"NO TRADE")
    def test_late_evidence_excluded(self):
        rows,reviewed=fixture()
        day=rows[3]["date"]
        reviewed[("TEST",str(day))]["available_at"]="2025-01-20T11:00:00Z"
        result=replay("TEST",rows,reviewed=reviewed,decision_dates=[day])
        self.assertFalse(result["observations"])
        self.assertTrue(any("availability_unverified_or_future" in reason for reason in result["excluded"][0]["reasons"]))
    def test_invalid_bar_rejected(self):
        rows,reviewed=fixture()
        rows[0]["high"]=1
        self.assertEqual(replay("TEST",rows,reviewed=reviewed)["status"],"unavailable")

class CalendarReplayTests(unittest.TestCase):
    def setUp(self):
        self.rows,self.reviewed=fixture()
        self.day=self.rows[-1]["date"]
        self.cutoff=f"{self.day}T23:59:59+05:45"
        start=date(2024,12,26)
        self.calendar=[]
        for i in range((self.day-start).days+1):
            d=start+timedelta(days=i)
            self.calendar.append(dict(date=str(d),status="verified_open" if d>=date(2025,1,1) else "verified_closed",evidence_id=f"synthetic-calendar-{i}",available_at=f"{d}T11:00:00Z"))
    def evaluate(self, calendar):
        return replay("TEST",self.rows,reviewed=self.reviewed,decision_dates=[self.day],calendar_records=calendar)["observations"][0]
    def test_complete_calendar(self):
        obs=self.evaluate(self.calendar)
        self.assertEqual(obs["multitimeframe"]["status"],"research_only")
        self.assertEqual(obs["multitimeframe"]["timeframes"]["daily"]["bars"],25)
        self.assertEqual(obs["action"],"NO TRADE")
        self.assertIsNone(obs["multitimeframe"]["production_score"])
    def test_missing_calendar(self):
        self.assertEqual(self.evaluate(None)["multitimeframe"]["status"],"unavailable")
    def test_missing_civil_day(self):
        self.assertEqual(self.evaluate(self.calendar[:8]+self.calendar[9:])["multitimeframe"]["status"],"unavailable")
    def test_duplicate_calendar(self):
        self.assertEqual(self.evaluate(self.calendar+[self.calendar[8]])["multitimeframe"]["status"],"unavailable")
    def test_late_calendar_evidence(self):
        rows=list(self.calendar)
        rows[8]=dict(rows[8],available_at="2025-02-01T00:00:00Z")
        self.assertEqual(self.evaluate(rows)["multitimeframe"]["status"],"unavailable")
    def test_missing_calendar_evidence(self):
        rows=list(self.calendar)
        rows[8]=dict(rows[8],evidence_id="")
        self.assertEqual(self.evaluate(rows)["multitimeframe"]["status"],"unavailable")
    def test_future_calendar_invariance(self):
        extra=dict(date="2025-01-26",status="verified_open",evidence_id="future",available_at="2025-01-26T11:00:00Z")
        self.assertEqual(self.evaluate(self.calendar),self.evaluate(self.calendar+[extra]))
    def test_incomplete_initial_calendar(self):
        self.assertEqual(self.evaluate(self.calendar[1:])["multitimeframe"]["status"],"unavailable")
    def test_exceptional_open(self):
        rows=list(self.calendar)
        rows[8]=dict(rows[8],status="verified_exceptional_open")
        self.assertIn(date.fromisoformat(rows[8]["date"]),calendar_as_of(rows,self.day,self.cutoff))
    def test_closed_day_with_bar(self):
        rows=list(self.calendar)
        rows[8]=dict(rows[8],status="verified_closed")
        self.assertEqual(self.evaluate(rows)["multitimeframe"]["reason"],"non_calendar_rows")
