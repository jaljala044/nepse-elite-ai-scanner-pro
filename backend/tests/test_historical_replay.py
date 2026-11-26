import unittest
from datetime import date, timedelta
from app.historical_replay import replay

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
