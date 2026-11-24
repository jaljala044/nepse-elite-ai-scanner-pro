import csv
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_sources import audit_source, reconcile_sources


class FloorsheetSourceAuditTests(unittest.TestCase):
    def write_csv(self, folder, name, rows):
        path = Path(folder) / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        return path

    def test_compact_amount_and_comma_formatted_amount_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            p1 = self.write_csv(folder, "jaljala.csv", [
                ["Contract_No", "Symbol", "Buyer", "Seller", "Quantity", "Rate", "Amount"],
                ["2026112005011353", "BHL", "57", "17", "10", "219.90", "2.20 K"],
            ])
            p2 = self.write_csv(folder, "samir.csv", [
                ["date", "contract_no", "stock_symbol", "buyer", "seller", "quantity", "rate", "amount"],
                ["2026-11-20", "2026112005011353", "BHL", "57", "17", "10", "219.90", "2,199.00"],
            ])
            one = audit_source("jaljala", p1)
            two = audit_source("samir", p2)
            self.assertEqual(one["valid_contracts"], 1)
            self.assertEqual(two["valid_contracts"], 1)
            self.assertEqual(one["turnover_npr"], "2199")
            self.assertEqual(two["turnover_npr"], "2199")

    def test_contract_missing_from_second_source_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            p1 = self.write_csv(folder, "full.csv", [
                ["date", "contract_no", "symbol", "buyer", "seller", "quantity", "rate", "amount"],
                ["2026-11-20", "2026112005011353", "BHL", "57", "17", "10", "219.9", "2199"],
                ["2026-11-20", "2026112005011352", "GVL", "87", "58", "10", "562", "5620"],
            ])
            p2 = self.write_csv(folder, "partial.csv", [
                ["date", "contract_no", "stock_symbol", "buyer", "seller", "quantity", "rate", "amount"],
                ["2026-11-20", "2026112005011353", "BHL", "57", "17", "10", "219.9", "2199"],
            ])
            report = reconcile_sources([("full", p1), ("partial", p2)])
            comparison = report["sessions"][0]["comparisons"][0]
            self.assertEqual(comparison["left_only_count"], 1)
            self.assertEqual(comparison["right_only_count"], 0)
            self.assertEqual(report["gate"], "FAIL")

    def test_duplicate_contract_and_bad_amount_fail_source_quality(self):
        with tempfile.TemporaryDirectory() as folder:
            p = self.write_csv(folder, "bad.csv", [
                ["date", "contract_no", "symbol", "buyer", "seller", "quantity", "rate", "amount"],
                ["2026-11-20", "2026112005011353", "BHL", "57", "17", "10", "219.9", "100"],
                ["2026-11-20", "2026112005011353", "BHL", "57", "17", "10", "219.9", "2199"],
            ])
            report = audit_source("bad", p)
            self.assertEqual(len(report["invalid_rows"]), 1)
            self.assertEqual(report["duplicate_contracts"], ["2026112005011353"])


if __name__ == "__main__":
    unittest.main()
