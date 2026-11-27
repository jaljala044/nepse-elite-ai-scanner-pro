import unittest
from app.broker_context_integration import build_context,POLICY

class BrokerContextTests(unittest.TestCase):
    def fixture(self):
        days=["2026-04-"+str(i) for i in range(20,25)]
        ts="2026-04-24T18:00:00+05:45"
        evidence={"status":"verified","source_id":"synthetic-test","source_payload_sha256":"a"*64,"available_at":ts}
        daily=[dict(session_date=d,buy_amount="100",sell_amount="20",net_amount="80",gross_amount="120",broker_participation=".2") for d in days]
        snapshot={"policy":POLICY,"as_of_timestamp":ts,"as_of_date":days[-1],"profiles":[dict(security_id="S1",broker_id="B1",requested_sessions=5,expected_sessions=5,complete_source_sessions=5,status="descriptive_only",coverage_ratio="1",daily=daily,buy_amount="500",sell_amount="100")]}
        prices=[dict(evidence,security_id="S1",symbol="TEST",session_date=d,open=100+i,high=102+i,low=99+i,close=101+i,volume=100+i*10) for i,d in enumerate(days)]
        memberships=[dict(evidence,security_id="S1",symbol="TEST",sector_code="H",effective_from=days[0],effective_to=None)]
        sector=[dict(evidence,sector_code="H",session_date=d,close=1000+i) for i,d in enumerate(days)]
        return [snapshot,prices,memberships,sector],dict(decision_time=ts,expected_sessions=days,quarantine_keys=[])
    def test_research_classification_and_determinism(self):
        a,k=self.fixture()
        result=build_context(*a,**k)
        self.assertEqual(result,build_context(*a,**k))
        self.assertEqual(result["profiles"][0]["classification"],"accumulation_research_candidate")
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["source_authentication_performed"])
    def test_late_price(self):
        a,k=self.fixture()
        a[1][0]["available_at"]="2026-04-25T00:00:00+05:45"
        self.assertEqual(build_context(*a,**k)["profiles"][0]["status"],"insufficient_evidence")
    def test_missing_and_ambiguous_membership(self):
        a,k=self.fixture()
        a[2].append(dict(a[2][0]))
        self.assertEqual(build_context(*a,**k)["profiles"][0]["classification"],"UNKNOWN")
    def test_quarantine(self):
        a,k=self.fixture()
        k["quarantine_keys"]=[("TEST",k["expected_sessions"][2])]
        self.assertEqual(build_context(*a,**k)["profiles"][0]["classification"],"UNKNOWN")
    def test_incomplete_coverage_and_accounting(self):
        a,k=self.fixture()
        a[0]["profiles"][0]["complete_source_sessions"]=4
        self.assertEqual(build_context(*a,**k)["profiles"][0]["classification"],"UNKNOWN")
        a,k=self.fixture()
        a[0]["profiles"][0]["daily"][0]["gross_amount"]="999"
        self.assertEqual(build_context(*a,**k)["profiles"][0]["classification"],"UNKNOWN")
