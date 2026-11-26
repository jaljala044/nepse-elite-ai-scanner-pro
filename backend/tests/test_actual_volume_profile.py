import unittest
from decimal import Decimal
from app.floorsheet_contract import FloorsheetContract
from app.actual_volume_profile import actual_volume_profile

class ActualVolumeProfileTests(unittest.TestCase):
    def fixture(self):
        day="2025-01-01"
        rows=[FloorsheetContract("fixture","a"*64,i+1,day,str(i),"AAA","1","2",
                Decimal(q),Decimal(p),Decimal(q*p)) for i,(p,q) in enumerate([(100,10),(101,50),(102,40)])]
        controls={day:dict(reviewed=True,symbol="AAA",evidence_id="fixture-control",
                           contracts=3,quantity=100,amount=10130)}
        return rows,dict(sessions=[day],controls=controls,eligible=True)
    def test_profile(self):
        r,k=self.fixture()
        x=actual_volume_profile("AAA",r,**k)
        self.assertEqual(x["status"],"research_only")
        self.assertEqual((x["poc"],x["val"],x["vah"]),("101","101","102"))
        self.assertEqual(x["total_quantity"],"100")
        self.assertEqual(x["levels"][1]["buyer_broker_quantity"],{"1":"50"})
        self.assertEqual(x["levels"][1]["local_volume_node"],"HVN")
    def test_duplicate(self):
        r,k=self.fixture()
        self.assertEqual(actual_volume_profile("AAA",r+[r[0]],**k)["reason"],"duplicate_contract")
    def test_missing_trade(self):
        r,k=self.fixture()
        self.assertEqual(actual_volume_profile("AAA",r[:-1],**k)["reason"],"daily_control_mismatch")
    def test_gate(self):
        r,k=self.fixture()
        k["eligible"]=False
        self.assertEqual(actual_volume_profile("AAA",r,**k)["status"],"unavailable")
    def test_zero_contracts(self):
        r,k=self.fixture()
        c=k["controls"][k["sessions"][0]]
        c.update(contracts=0,quantity=0,amount=0)
        self.assertEqual(actual_volume_profile("AAA",[],**k)["status"],"verified_zero_contracts")
