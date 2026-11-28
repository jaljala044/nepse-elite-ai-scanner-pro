import csv, json, tempfile, unittest
from pathlib import Path
from scripts.validate_ohlcv_exception_ledger import validate

USER_KEYS=[("BGWT","2025-07-28"),("MEHL","2025-07-28"),("RAWA","2025-07-28"),("RHGCL","2025-07-28"),("ULHC","2025-07-28")]
NEPSE_KEYS=[("API","2026-11-19"),("RHGCL","2026-11-19")]
OTHER_KEYS=NEPSE_KEYS+[("HRL","2026-11-19")]

def record(kind, number):
    common={"exception_id":f"{kind}:{number}","exception_type":kind,"symbol":f"S{number}","trade_date":"2026-01-01","source_repository":"jaljala044/nepse-smc-data","disposition":"quarantined_unresolved","reviewer_rationale":"Fixture only; retain unresolved.","evidence_pointer":"fixture://source"}
    if kind=="invalid_ohlc":
        common.update({"source_commit_sha":"a"*40,"source_path":f"data/S{number}.csv","source_file_sha256":"b"*64,"source_csv_line":2,"raw_source_row":{"open":"10","high":"9","low":"8","close":"9"},"validation_rule_violated":"high below close"})
    else:
        symbol,day=(USER_KEYS+OTHER_KEYS)[number]
        common.update({"symbol":symbol,"trade_date":day,"source_repository":"multiple_pinned_sources","source_evidence":{
            "jaljala044/nepse-smc-data":{"commit_sha":"a"*40,"path":"data/example.csv","file_sha256":"b"*64,"source_csv_line":2,"row":{"close":"10"}},
            "jaljala044/nepse-history-starter":{"commit_sha":"c"*40,"path":"data/example.csv","file_sha256":"d"*64,"source_csv_line":2,"row":{"close":"11"}}}})
        if number<5:
            common.update({
                "disposition":"resolved_with_user_authoritative_evidence",
                "evidence_pointer":"conversation-memory://user-final-authoritative-2025-07-28-records" if number<5 else "https://github.com/jaljala044/nepse-smc-data/commit/e4d069c6ed292c127e7805b19f98e2837e999073",
                "resolution_evidence":{
                    "authority":"explicit_user_designation_as_final_and_authoritative",
                    "authoritative_values":{"open":"1.00","high":"1.00","low":"1.00","close":"1.00","volume":"1","turnover_npr":"1"},
                    "canonical_promotion_allowed":False,
                    "raw_source_rows_modified":False
                }
            })
        elif number<7:
            supported={"high":"334.20","low":"330.00","close":"331.80","volume":"105340"} if number==5 else {"high":"259.50","low":"252.10","close":"258.00","volume":"9054","trades":"47"}
            common.update({
                "disposition":"resolved_with_nepse_field_evidence",
                "resolution_evidence":{
                    "authority":"captured_nepse_source_field_scoped",
                    "source_reference":"https://www.nepalstock.com.np/",
                    "supported_fields":supported,
                    "omitted_fields":["open"],
                    "canonical_promotion_allowed":False,
                    "raw_source_rows_modified":False
                }
            })
    return common

def write_fixture(root, records):
    jp,cp=root/"ledger.json",root/"ledger.csv"
    counts={"total_exception_records":1339,"invalid_ohlc_rows":1331,"cross_source_conflict_keys":8,"unresolved":1332,"resolved_with_user_authoritative_evidence":5,"resolved_with_nepse_field_evidence":2}
    jp.write_text(json.dumps({"counts":counts,"exceptions":records}),encoding="utf-8")
    fields=sorted({k for row in records for k in row})
    with cp.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in records:
            writer.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    return jp,cp

class LedgerValidationTests(unittest.TestCase):
    def fixture(self):
        return [record("invalid_ohlc",i) for i in range(1331)]+[record("cross_source_ohlcv_conflict",i) for i in range(8)]

    def test_expected_ledger_passes_with_separate_user_and_nepse_field_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),self.fixture())
            self.assertEqual(validate(jp,cp),[])

    def test_invalid_ohlc_cannot_be_resolved_by_conflict_policy(self):
        records=self.fixture();records[0]["disposition"]="resolved_with_user_authoritative_evidence"
        records[0]["evidence_pointer"]="conversation-memory://user-final-authoritative-2025-07-28-records"
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            self.assertTrue(any("invalid OHLC record" in e for e in validate(jp,cp)))

    def test_hrl_conflict_cannot_use_user_authority_disposition(self):
        records=self.fixture();records[-1]["disposition"]="resolved_with_user_authoritative_evidence"
        records[-1]["evidence_pointer"]="conversation-memory://user-final-authoritative-2025-07-28-records"
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            self.assertTrue(any("outside approved" in e for e in validate(jp,cp)))

    def test_csv_identity_fields_must_match_json_for_each_exception_id(self):
        records=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            with cp.open(encoding="utf-8",newline="") as stream:
                rows=list(csv.DictReader(stream)); fields=rows[0].keys()
            rows[0]["symbol"]="ALTERED"
            with cp.open("w",encoding="utf-8",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            self.assertTrue(any("JSON/CSV field mismatch" in e and ".symbol" in e for e in validate(jp,cp)))

    def test_csv_nested_source_evidence_must_match_json(self):
        records=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            jp,cp=write_fixture(Path(tmp),records)
            with cp.open(encoding="utf-8",newline="") as stream:
                rows=list(csv.DictReader(stream)); fields=rows[0].keys()
            conflict_row=next(row for row in rows if row["exception_type"]=="cross_source_ohlcv_conflict")
            conflict_row["source_evidence"]=conflict_row["source_evidence"].replace('"close": "10"','"close": "999"')
            with cp.open("w",encoding="utf-8",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            self.assertTrue(any("JSON/CSV field mismatch" in e and ".source_evidence" in e for e in validate(jp,cp)))

if __name__=="__main__": unittest.main()
