import unittest
from datetime import date, timedelta
from app.horizon_outcomes import evaluate_outcomes, HORIZONS

def fixture():
    days=[date(2025,1,1)+timedelta(days=i) for i in range(25)]
    rows=[dict(date=d,open=100+i,high=102+i,low=99+i,close=100+i,volume=100) for i,d in enumerate(days)]
    reviewed={("TEST",str(r["date"])):dict(r,date=str(r["date"]),instrument_type="equity",
        security_status="active",session_status="verified_open",source_id="sharehub",
        evidence_id="synthetic",available_at=f'{r["date"]}T11:00:00Z') for r in rows}
    return days,rows,reviewed

class HorizonTests(unittest.TestCase):
    def run_case(self, days,rows,reviewed,calendar=True):
        return evaluate_outcomes("TEST",rows,{"decision_date":str(days[0])},
            verified_sessions=days if calendar else None,evaluation_date=days[-1],reviewed=reviewed)
    def test_reference_returns(self):
        days,rows,reviewed=fixture()
        r=self.run_case(days,rows,reviewed)
        self.assertAlmostEqual(r["horizons"]["t_plus_2"][0]["return_pct"],3)
        self.assertAlmostEqual(r["horizons"]["swing"][1]["return_pct"],20)
        self.assertIsNone(r["horizons"]["investment"][0]["return_pct"])
    def test_missing_session(self):
        days,rows,reviewed=fixture()
        r=self.run_case(days,rows[:2]+rows[3:],reviewed)
        self.assertEqual(r["horizons"]["t_plus_2"][0]["status"],"missing_session")
    def test_unverified_calendar(self):
        days,rows,reviewed=fixture()
        self.assertEqual(self.run_case(days,rows,reviewed,False)["status"],"data_unavailable")
    def test_late_outcome(self):
        days,rows,reviewed=fixture()
        reviewed[("TEST",str(days[3]))]["available_at"]="2025-02-01T11:00:00Z"
        r=self.run_case(days,rows,reviewed)
        self.assertEqual(r["horizons"]["t_plus_2"][0]["status"],"outcome_evidence_unverified")
