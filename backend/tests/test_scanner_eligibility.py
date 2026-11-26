import unittest
from datetime import date
from app.scanner_eligibility import assess, load_reviewed_rows
import tempfile, json
from pathlib import Path
from app.storage import DATA, IMPORTS, store_rows

class EligibilityTests(unittest.TestCase):
    def test_evidence(self):
        row = dict(date=date(2025,1,1),open=10,high=12,low=9,close=11,volume=100)
        record = dict(row,instrument_type="equity",security_status="active",session_status="verified_open",source_id="sharehub",evidence_id="fixture",available_at="2025-01-01T12:00:00Z")
        cutoff="2025-01-02T00:00:00Z"
        key=("TEST","2025-01-01")
        self.assertFalse(assess("TEST",[row],cutoff,{key:record}))
        self.assertTrue(assess("TEST",[row],cutoff,{}))
        for field,value in [("instrument_type","mutual_fund"),("session_status","candidate"),("source_id","unknown"),("available_at","2025-01-03T00:00:00Z"),("close",10)]:
            self.assertTrue(assess("TEST",[row],cutoff,{key:dict(record,**{field:value})}))
    def test_ingest(self):
        original=dict(DATA); imports=list(IMPORTS)
        try:
            DATA.clear()
            header="symbol,date,open,high,low,close,volume\n"
            for data in ["TEST,2025-01-01,nan,12,9,11,100","TEST,2025-01-01,10,12,9,11,1.5"]:
                with self.assertRaises(ValueError):
                    store_rows(header+data,"fixture")
            store_rows(header+"TEST,2025-01-01,10,12,9,11,100","fixture")
            with self.assertRaises(ValueError):
                store_rows(header+"TEST,2025-01-01,10,12,9,10,100","fixture")
            self.assertEqual(DATA["TEST"][0]["close"],11)
        finally:
            DATA.clear(); DATA.update(original); IMPORTS[:]=imports

    def test_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"review.json"
            row = dict(symbol="TEST",date="2025-01-01",open=10,high=12,low=9,close=11,volume=100,instrument_type="equity",security_status="active",session_status="verified_open",source_id="chukul",evidence_id="fixture",available_at="2025-01-01T12:00:00Z",security_id="1",lifecycle_evidence_id="l",session_evidence_id="s",price_basis_reviewed=True,canonical_promotion_allowed=True)
            path.write_text(json.dumps({"schema_version":1,"records":[row,{"canonical_promotion_allowed":False}]}))
            self.assertEqual(len(load_reviewed_rows(path)),1)
            path.write_text(json.dumps({"schema_version":1,"records":[row,row]}))
            with self.assertRaises(ValueError):
                load_reviewed_rows(path)
