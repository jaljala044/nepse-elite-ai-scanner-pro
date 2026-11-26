import csv
import json
import tempfile
import unittest
from pathlib import Path

from audit_official_security_history_vs_floorsheet import reconcile


class OfficialSecurityHistoryReconciliationTests(unittest.TestCase):
    def test_exact_per_symbol_match_and_unknown_missing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            official = root / "official"
            floors = root / "floors"
            official.mkdir()
            floors.mkdir()
            snapshot = root / "snapshot.csv"
            snapshot.write_text("symbol,security_id,security_name,snapshot_date\nABC,1,Alpha,2026-11-25\nXYZ,2,Xyz,2026-11-25\n")
            payload = [
                {"businessDate": "2026-11-19", "symbol": "ABC", "securityId": 1,
                 "securityName": "Alpha", "totalTrades": 1, "totalTradedQuantity": 10, "totalTradedValue": 1000},
                {"businessDate": "2026-11-19", "symbol": "XYZ", "securityId": 2,
                 "securityName": "Xyz", "totalTrades": 1, "totalTradedQuantity": 5, "totalTradedValue": 500},
            ]
            for day in ("2026-11-19", "2026-11-20", "2026-11-24"):
                (official / f"{day}-parsed-response.json").write_text(json.dumps(payload if day == "2026-11-19" else [
                    {"businessDate": day, "symbol": "ABC", "securityId": 1, "securityName": "Alpha",
                     "totalTrades": 1, "totalTradedQuantity": 10, "totalTradedValue": 1000}
                ]))
                for source in ("samir", "socrateai"):
                    with (floors / f"{source}-{day}.csv").open("w", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=["date", "contract_no", "stock_symbol", "quantity", "amount"] if source == "samir" else ["date", "transaction", "symbol", "quantity", "amount"])
                        writer.writeheader()
                        for symbol, qty, amount in ([("ABC", 10, 1000), ("XYZ", 5, 500)] if day == "2026-11-19" else [("ABC", 10, 1000)]):
                            writer.writerow({
                                "date": day,
                                "contract_no" if source == "samir" else "transaction": f"{symbol}-1",
                                "stock_symbol" if source == "samir" else "symbol": symbol,
                                "quantity": qty, "amount": amount,
                            })
            report = reconcile(official, floors, snapshot)
        self.assertEqual(report["dates"]["2026-11-19"]["samir"]["status_counts"], {"MATCH_EXACT": 2})
        self.assertFalse(report["coverage_admission_allowed"])
        self.assertFalse(report["historical_security_identity_verified"])

    def test_official_duplicate_symbols_fail_closed(self):
        # Loader-level duplicate rejection is exercised through the full audit.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            official = root / "official"
            floors = root / "floors"
            official.mkdir()
            floors.mkdir()
            (root / "snapshot.csv").write_text("symbol,security_id,security_name\nABC,1,Alpha\n")
            duplicate = [
                {"businessDate": "2026-11-19", "symbol": "ABC", "securityId": 1, "totalTrades": 1, "totalTradedQuantity": 1, "totalTradedValue": 1},
                {"businessDate": "2026-11-19", "symbol": "ABC", "securityId": 1, "totalTrades": 1, "totalTradedQuantity": 1, "totalTradedValue": 1},
            ]
            for day in ("2026-11-19", "2026-11-20", "2026-11-24"):
                (official / f"{day}-parsed-response.json").write_text(json.dumps(duplicate if day == "2026-11-19" else [
                    {"businessDate": day, "symbol": "ABC", "securityId": 1, "totalTrades": 1, "totalTradedQuantity": 1, "totalTradedValue": 1}
                ]))
                for source in ("samir", "socrateai"):
                    with (floors / f"{source}-{day}.csv").open("w", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=["date", "contract_no", "stock_symbol", "quantity", "amount"] if source == "samir" else ["date", "transaction", "symbol", "quantity", "amount"])
                        writer.writeheader()
                        writer.writerow({"date": day, "contract_no" if source == "samir" else "transaction": "1",
                                         "stock_symbol" if source == "samir" else "symbol": "ABC", "quantity": 1, "amount": 1})
            with self.assertRaisesRegex(ValueError, "duplicate official symbol"):
                reconcile(official, floors, root / "snapshot.csv")


if __name__ == "__main__":
    unittest.main()
