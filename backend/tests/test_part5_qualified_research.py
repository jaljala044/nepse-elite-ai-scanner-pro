import unittest
from unittest.mock import patch
from app.part5_qualified_research import reconcile_field, qualified_segment
from app.part5_replay_journal_bridge import record_replay_outcome
from app.part5_reference_comparison import compare_reference_paths
from datetime import date,timedelta

class Part5AdmissionRegression(unittest.TestCase):
    def vote(self,p,lineage,value=100,**kw):
        return dict(provider=p,symbol="TEST",date="2025-01-01",field="close",semantics="official_close",
            status="captured",sha256="a"*64,evidence_uri="https://example.invalid",retrieved_at="2025-01-02T00:00:00Z",
            value=value,lineage=lineage,lineage_reviewed=True,**kw)
    def reconcile(self,rows):
        return reconcile_field(rows,symbol="TEST",session_date="2025-01-01",field="close",semantics="official_close")
    def test_consensus_and_conflict(self):
        rows=[self.vote(p,l) for p,l in zip(("sharehub","chukul","sharesansar","punji"),("a","a","b","b"))]
        self.assertEqual(self.reconcile(rows)["status"],"verified_secondary_consensus")
        self.assertEqual(self.reconcile(rows[:3])["status"],"qualified_single_or_partial_source")
        self.assertEqual(self.reconcile(rows+[self.vote("nepse_trading","c",101)])["status"],"conflict")
    def test_semantic_mismatch_not_a_vote(self):
        row=self.vote("sharehub","a")
        self.assertEqual(self.reconcile([dict(row,semantics="ltp")])["status"],"missing")
    def test_single_source_qualified_not_canonical(self):
        row=dict(date="2025-01-01",open=100,high=105,low=95,close=102,volume=100)
        args=dict(expected_sessions=["2025-01-01"],source_id="punji",source_uri="https://example.invalid",
                  source_sha256="a"*64,price_basis="provider_reported_unknown",availability_assumption="EOD assumption")
        result=qualified_segment([row],**args)
        self.assertTrue(result["qualified_research_eligible"])
        self.assertFalse(result["production_eligible"])
        self.assertFalse(qualified_segment([],**args)["qualified_research_eligible"])
    def test_reference_no_gap_fill(self):
        days=[(date(2025,1,1)+timedelta(days=i)).isoformat() for i in range(26)]
        rows=[dict(date=d,open=100+i,high=101+i,low=99+i,close=100+i,volume=100) for i,d in enumerate(days)]
        args=dict(start=days[0],end=days[-1],holding_sessions=5)
        self.assertEqual(compare_reference_paths(rows,days,**args)["results"]["unconditional"]["n"],1)
        self.assertEqual(compare_reference_paths(rows[1:],days,**args)["results"]["unconditional"]["n"],0)
    def test_bridge_rejects_wrong_identity(self):
        original=dict(symbol="TEST",methodology="v1",horizon="swing",decision_time="2025-01-01T12:00:00Z")
        trade=dict(decision_date="2025-01-01",horizon="swing",status="closed_scenario",exit_date="2025-01-10")
        replay=dict(classification="hypothetical_research_only",production_approved=False,symbol="OTHER",methodology="v1",trades=[trade])
        with patch("app.part5_replay_journal_bridge.get_signal",return_value=original):
            with self.assertRaises(ValueError):
                record_replay_outcome("owner","id",replay,observed_at="2025-01-11T00:00:00Z")
