import csv
import tempfile
import unittest
from pathlib import Path

from compare_floorsheet_source_csvs import compare_sources, HEADERS


def write_csv(source_format, rows):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.close()
    with open(tmp.name, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS[source_format], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return Path(tmp.name)


class FloorsheetSourceComparisonTests(unittest.TestCase):
    def tearDown(self):
        for path in getattr(self, "paths", []):
            path.unlink(missing_ok=True)

    def make_pair(self, extra=False, conflict=False):
        left = write_csv("samir", [
            {"date":"2026-11-24","sn":"1","contract_no":"C1","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"200"},
            {"date":"2026-11-24","sn":"2","contract_no":"C2","stock_symbol":"NABIL",
             "buyer":"12","seller":"22","quantity":"3","rate":"110","amount":"330"},
        ])
        right_rows = [
            {"transaction":"C1","symbol":"NABIL","buyer":"11","seller":"22",
             "quantity":"2.0","rate":"100.0","amount":"200.0","date":"2026-11-24"},
            {"transaction":"C2","symbol":"NABIL","buyer":"12","seller":"22",
             "quantity":"3.0","rate":"110.0","amount":"330.0","date":"2026-11-24"},
        ]
        if conflict:
            right_rows[1]["amount"] = "331.0"
        if extra:
            right_rows.append({
                "transaction":"C3","symbol":"NMLBBLP","buyer":"34","seller":"22",
                "quantity":"4.0","rate":"100.0","amount":"400.0","date":"2026-11-24",
            })
        right = write_csv("socrate", right_rows)
        self.paths = [left, right]
        return left, right

    def test_exact_shared_transactions_and_extra_contract_are_reported(self):
        left, right = self.make_pair(extra=True)
        result = compare_sources(
            left, right, left_format="samir", right_format="socrate",
            independent_control={
                "trade_date":"2026-11-24","quantity":"9","gross_amount":"930",
            },
        )
        self.assertEqual(result["comparison"]["shared_contract_count"], 2)
        self.assertEqual(result["comparison"]["exact_row_match_count"], 2)
        self.assertEqual(result["comparison"]["left_only_contract_count"], 0)
        self.assertEqual(result["comparison"]["right_only_contract_count"], 1)
        self.assertEqual(result["comparison"]["right_only_contracts"][0]["contract_id"], "C3")
        self.assertEqual(result["independent_control"]["left"]["status"], "failed")
        self.assertEqual(result["independent_control"]["right"]["status"], "passed")
        self.assertFalse(result["acceptance"]["canonical_source_selected"])

    def test_shared_contract_field_conflict_is_not_hidden(self):
        left, right = self.make_pair(conflict=True)
        result = compare_sources(left, right, left_format="samir", right_format="socrate")
        self.assertEqual(result["comparison"]["exact_row_match_count"], 1)
        self.assertEqual(result["comparison"]["conflicting_shared_contract_count"], 1)
        self.assertIn("amount", result["comparison"]["conflicts"][0]["different_fields"])
        self.assertEqual(result["comparison"]["status"], "mismatch")

    def test_wrong_headers_are_rejected(self):
        left, right = self.make_pair()
        bad = Path(left.parent / "wrong_header.csv")
        bad.write_text("x,y\n1,2\n", encoding="utf-8")
        self.paths.append(bad)
        with self.assertRaisesRegex(ValueError, "header mismatch"):
            compare_sources(bad, right, left_format="samir", right_format="socrate")


    def test_independent_controls_require_matching_file_date(self):
        left = write_csv("samir", [
            {"date":"2026-11-23","sn":"1","contract_no":"C1","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"200"},
        ])
        right = write_csv("socrate", [
            {"transaction":"C1","symbol":"NABIL","buyer":"11","seller":"22",
             "quantity":"2","rate":"100","amount":"200","date":"2026-11-23"},
        ])
        self.paths = [left, right]
        result = compare_sources(
            left, right, left_format="samir", right_format="socrate",
            independent_control={
                "trade_date":"2026-11-24","quantity":"2","gross_amount":"200",
            },
        )
        self.assertEqual(result["independent_control"]["left"]["status"], "failed")
        self.assertIn(
            "source_date_mismatch",
            result["independent_control"]["left"]["differences"],
        )



if __name__ == "__main__":
    unittest.main()
