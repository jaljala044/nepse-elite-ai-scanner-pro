import unittest
from app.broker_smc_confluence import broker_smc_confluence

class BrokerSMCTests(unittest.TestCase):
    def fixture(self):
        days=[f"2025-01-{i:02}" for i in range(1,6)]
        rows=[]
        for d in days:
            for side,b in (("buy","B1"),("sell","B2")):
                rows.append(dict(symbol="AAA",trade_date=d,contract_id=d,side=side,
                    amount="1000",quantity="10",identity_status="verified",
                    broker_entity_id=b,source_broker_code=b))
        s={"status":"research_only","as_of":days[-1],"timeframes":{"daily":{"structure":{
            "bias":"bullish","events":[{"type":"bos","direction":"bullish","date":days[-1]}]}}}}
        return s,rows,dict(as_of=days[-1],verified_sessions=days,reconciled_sessions=days,eligible=True)
    def test_valid_balanced(self):
        s,r,k=self.fixture()
        x=broker_smc_confluence("AAA",s,r,**k)
        self.assertEqual(x["status"],"research_only")
        self.assertEqual(x["contract_count"],5)
        self.assertFalse(x["directional_agreement"])
        self.assertEqual(x["action"],"NO TRADE")
    def test_duplicate(self):
        s,r,k=self.fixture()
        self.assertEqual(broker_smc_confluence("AAA",s,r+[r[0]],**k)["reason"],"duplicate_contract_party")
    def test_missing_side(self):
        s,r,k=self.fixture()
        self.assertEqual(broker_smc_confluence("AAA",s,r[1:],**k)["reason"],"unbalanced_contract_parties")
    def test_unreconciled(self):
        s,r,k=self.fixture()
        k["reconciled_sessions"]=k["reconciled_sessions"][:-1]
        self.assertEqual(broker_smc_confluence("AAA",s,r,**k)["reason"],"unreconciled_sessions")
    def test_stale_structure(self):
        s,r,k=self.fixture()
        s["as_of"]="2025-01-04"
        self.assertEqual(broker_smc_confluence("AAA",s,r,**k)["reason"],"structure_cutoff_mismatch")
