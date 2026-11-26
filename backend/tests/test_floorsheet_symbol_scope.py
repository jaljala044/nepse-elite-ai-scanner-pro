import csv
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_symbol_scope import audit_floorsheet_symbol_scope


class FloorsheetSymbolScopeAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.samir = self.root / "samir.csv"
        self.socrateai = self.root / "socrateai.csv"
        self.crosswalk = self.root / "crosswalk.csv"
        self.candidates = self.root / "candidates.csv"
        self.snapshot = self.root / "snapshot.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, path, headers, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def test_classifies_equity_fund_promoter_debenture_and_unknown_without_promotion(self):
        self.write_csv(self.samir,
            ["contract_no", "stock_symbol", "quantity", "rate", "amount", "date"], [
                {"contract_no":"E1","stock_symbol":"EQ1","quantity":"10","rate":"10","amount":"100","date":"2026-11-24"},
                {"contract_no":"F1","stock_symbol":"MF1","quantity":"10","rate":"10","amount":"100","date":"2026-11-24"},
                {"contract_no":"P1","stock_symbol":"PROM1","quantity":"10","rate":"10","amount":"100","date":"2026-11-24"},
            ])
        self.write_csv(self.socrateai,
            ["transaction", "symbol", "quantity", "rate", "amount", "date"], [
                {"transaction":"D1","symbol":"DEB1","quantity":"10","rate":"10","amount":"100","date":"2026-11-24"},
                {"transaction":"U1","symbol":"UNK1","quantity":"10","rate":"10","amount":"100","date":"2026-11-24"},
            ])
        self.write_csv(self.crosswalk,
            ["symbol","security_id","security_name","snapshot_date","active_status","crosswalk_status"], [
                {"symbol":"EQ1","security_id":"1","security_name":"Example Equity","snapshot_date":"2026-11-25","active_status":"A","crosswalk_status":"snapshot_id_match_active_status_A"},
            ])
        self.write_csv(self.candidates,
            ["symbol","instrument_class_from_rendered_list","official_snapshot_id","official_snapshot_status"], [
                {"symbol":"MF1","instrument_class_from_rendered_list":"Mutual Fund","official_snapshot_id":"2","official_snapshot_status":"A"},
            ])
        self.write_csv(self.snapshot,
            ["symbol","security_id","security_name","active_status","snapshot_date"], [
                {"symbol":"EQ1","security_id":"1","security_name":"Example Equity","active_status":"A","snapshot_date":"2026-11-25"},
                {"symbol":"PROM1","security_id":"3","security_name":"Example Company Promoter Share","active_status":"A","snapshot_date":"2026-11-25"},
                {"symbol":"DEB1","security_id":"4","security_name":"8% Example Debenture 2089","active_status":"A","snapshot_date":"2026-11-25"},
            ])
        report = audit_floorsheet_symbol_scope(
            self.samir,self.socrateai,self.crosswalk,self.candidates,self.snapshot,
            "2026-11-24", "2026-11-25",
        )
        by_symbol = {row["symbol"]: row for row in report["symbols"]}
        self.assertEqual(by_symbol["EQ1"]["scope_class"], "IN_SCOPE_EQUITY_CANDIDATE")
        self.assertEqual(by_symbol["MF1"]["scope_class"], "OUT_OF_SCOPE_MUTUAL_FUND")
        self.assertEqual(by_symbol["PROM1"]["scope_class"], "OUT_OF_SCOPE_PROMOTER_SHARE")
        self.assertEqual(by_symbol["DEB1"]["scope_class"], "OUT_OF_SCOPE_DEBENTURE")
        self.assertEqual(by_symbol["UNK1"]["scope_class"], "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH")
        self.assertFalse(report["policy"]["canonical_promotion_allowed"])
        self.assertFalse(report["policy"]["unknown_scope_promoted"])

    def test_equity_candidate_missing_crosswalk_is_not_auto_included(self):
        self.write_csv(self.samir,
            ["contract_no", "stock_symbol", "quantity", "rate", "amount", "date"], [
                {"contract_no":"E1","stock_symbol":"EQ2","quantity":"1","rate":"1","amount":"1","date":"2026-11-24"},
            ])
        self.write_csv(self.socrateai,
            ["transaction", "symbol", "quantity", "rate", "amount", "date"], [
                {"transaction":"E1","symbol":"EQ2","quantity":"1","rate":"1","amount":"1","date":"2026-11-24"},
            ])
        self.write_csv(self.crosswalk,
            ["symbol","security_id","security_name","snapshot_date","active_status","crosswalk_status"], [])
        self.write_csv(self.candidates,
            ["symbol","instrument_class_from_rendered_list","official_snapshot_id","official_snapshot_status"], [
                {"symbol":"EQ2","instrument_class_from_rendered_list":"Equity","official_snapshot_id":"22","official_snapshot_status":"A"},
            ])
        self.write_csv(self.snapshot,
            ["symbol","security_id","security_name","active_status","snapshot_date"], [
                {"symbol":"EQ2","security_id":"22","security_name":"Example Equity","active_status":"A","snapshot_date":"2026-11-25"},
            ])
        report = audit_floorsheet_symbol_scope(
            self.samir,self.socrateai,self.crosswalk,self.candidates,self.snapshot
        )
        self.assertEqual(report["symbols"][0]["scope_class"], "EQUITY_CANDIDATE_NOT_IN_CROSSWALK")


    def test_wrong_trade_date_is_rejected(self):
        self.write_csv(self.samir,
            ["contract_no", "stock_symbol", "quantity", "rate", "amount", "date"], [
                {"contract_no":"E1","stock_symbol":"EQ1","quantity":"1","rate":"1","amount":"1","date":"2026-11-23"},
            ])
        self.write_csv(self.socrateai,
            ["transaction", "symbol", "quantity", "rate", "amount", "date"], [])
        for path, headers in (
            (self.crosswalk,["symbol","security_id","security_name","snapshot_date","active_status","crosswalk_status"]),
            (self.candidates,["symbol","instrument_class_from_rendered_list","official_snapshot_id","official_snapshot_status"]),
            (self.snapshot,["symbol","security_id","security_name","active_status","snapshot_date"]),
        ):
            self.write_csv(path, headers, [])
        with self.assertRaisesRegex(ValueError, "differs from expected"):
            audit_floorsheet_symbol_scope(
                self.samir,self.socrateai,self.crosswalk,self.candidates,self.snapshot,
                "2026-11-24", "2026-11-25",
            )

    def test_crosswalk_snapshot_identity_conflict_is_rejected(self):
        self.write_csv(self.samir,
            ["contract_no", "stock_symbol", "quantity", "rate", "amount", "date"], [])
        self.write_csv(self.socrateai,
            ["transaction", "symbol", "quantity", "rate", "amount", "date"], [])
        self.write_csv(self.crosswalk,
            ["symbol","security_id","security_name","snapshot_date","active_status","crosswalk_status"], [
                {"symbol":"EQ1","security_id":"1","security_name":"Example Equity","snapshot_date":"2026-11-25","active_status":"A","crosswalk_status":"snapshot_id_match_active_status_A"},
            ])
        self.write_csv(self.candidates,
            ["symbol","instrument_class_from_rendered_list","official_snapshot_id","official_snapshot_status"], [])
        self.write_csv(self.snapshot,
            ["symbol","security_id","security_name","active_status","snapshot_date"], [
                {"symbol":"EQ1","security_id":"999","security_name":"Example Equity","active_status":"A","snapshot_date":"2026-11-25"},
            ])
        with self.assertRaisesRegex(ValueError, "crosswalk/security snapshot conflict"):
            audit_floorsheet_symbol_scope(
                self.samir,self.socrateai,self.crosswalk,self.candidates,self.snapshot,
                "2026-11-24", "2026-11-25",
            )

    def test_duplicate_contract_keys_fail_closed(self):
        self.write_csv(self.samir,
            ["contract_no", "stock_symbol", "quantity", "rate", "amount", "date"], [
                {"contract_no":"E1","stock_symbol":"EQ1","quantity":"1","rate":"1","amount":"1","date":"2026-11-24"},
                {"contract_no":"E1","stock_symbol":"EQ1","quantity":"1","rate":"1","amount":"1","date":"2026-11-24"},
            ])
        self.write_csv(self.socrateai,
            ["transaction", "symbol", "quantity", "rate", "amount", "date"], [
                {"transaction":"E1","symbol":"EQ1","quantity":"1","rate":"1","amount":"1","date":"2026-11-24"},
            ])
        for path, headers in (
            (self.crosswalk,["symbol","security_id","security_name","snapshot_date","active_status","crosswalk_status"]),
            (self.candidates,["symbol","instrument_class_from_rendered_list","official_snapshot_id","official_snapshot_status"]),
            (self.snapshot,["symbol","security_id","security_name","active_status","snapshot_date"]),
        ):
            self.write_csv(path, headers, [])
        with self.assertRaisesRegex(ValueError, "duplicate date/contract"):
            audit_floorsheet_symbol_scope(
                self.samir,self.socrateai,self.crosswalk,self.candidates,self.snapshot
            )


if __name__ == "__main__":
    unittest.main()
