import csv, json, tempfile, unittest
from pathlib import Path
from scripts.validate_ohlcv_exception_ledger import validate

USER_KEYS=[("BGWT","2025-07-28"),("MEHL","2025-07-28"),("RAWA","2025-07-28"),("RHGCL","2025-07-28"),("ULHC","2025-07-28")]
OTHER_KEYS=[("API","2026-11-19"),("HRL","2026-11-19"),("RHGCL","2026-11-19")]

def record(kind, number):
    common={"exception_id":f"{kind}:{number}","exception_type":kind,"symbol":f"S{number}","trade_date":"2026-01-01","source_repository":"jaljala044/nepse-smc-data","disposition":"quarantined_unresolved","reviewer_rationale":"Fixture only; retain unresolved.","evidence_pointer":"fixture://source"}
    if kind=="invalid_ohlc":
        common.update({"source_commit_sha":"a"*40,"source_path":f"data/S{number}.csv","source_file_sha256":"b"*64,"source_csv_line":2,"raw_source_row":{"open":"10","high":"9","low":"8","close":"9"},"validation_rule_violated":"high below close"})
    else:
        symbol,day=(USER_KEYS+OTHER_KEYS)[number]
        common.update({"symbol":symbol,"trade_date":day,"source_repository":"multiple_pinned_sources","source_evidence":{
            "jaljala044/nepse-smc-data":{"commit_sha":"a"*40,"path":"data/example.csv","file_sha256":"b"*64,"row":{"close":"10"}},
            "jaljala044/nepse-history-starter":{"commit_sha":"c"*40,"path":"data/example.csv","file_sha256":"d"*64,"row":{"close":"11"}}}})
        if number<5:
            common.update({"disposition":"resolved_with_user_authoritative_evidence","evidence_pointer":"conversation-memory://user-final-authoritative-2025-07-28-records"})
    return common

def write_fixture(root, records):
    jp,cp=root/"ledger.json",root/"ledger.csv"
    counts={"total_exception_records":1339,"invalid_ohlc_rows":1331,"cross_source_conflict_keys":8}
    jp.write_text(json.dumps({"counts":counts,"exceptions":records}),encoding="utf-8")
    fields=sorted({k for row in records for k in row})
    with cp.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in records:
            writer.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    return jp,cp

class LedgerValidationTests(unittest.TestCase):
    def fixture(self):
        return [record("invalid_ohlc",i) for i in range(1331)]+[record("cross_source_ohlcv_conflict",i) for i in range(8)]

    def test_expected_ledger_passes_with_user_authority_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),self.fixture())
            self.assertEqual(validate(jp,cp),[])

    def test_invalid_ohlc_cannot_be_resolved_by_conflict_policy(self):
        records=self.fixture();records[0]["disposition"]="resolved_with_user_authoritative_evidence"
        records[0]["evidence_pointer"]="conversation-memory://user-final-authoritative-2025-07-28-records"
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            self.assertTrue(any("invalid OHLC record" in e for e in validate(jp,cp)))

    def test_unapproved_conflict_cannot_use_user_authority_disposition(self):
        records=self.fixture();records[-1]["disposition"]="resolved_with_user_authoritative_evidence"
        records[-1]["evidence_pointer"]="conversation-memory://user-final-authoritative-2025-07-28-records"
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            self.assertTrue(any("outside approved" in e for e in validate(jp,cp)))

if __name__=="__main__": unittest.main()
