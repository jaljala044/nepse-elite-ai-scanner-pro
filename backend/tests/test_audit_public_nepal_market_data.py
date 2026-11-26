import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_public_nepal_market_data import audit_symbol_csv, crosscheck_official_history


HEADER = b"published_date,open,high,low,close,per_change,traded_quantity,traded_amount,status\n"


class PublicNepalMarketDataAuditTests(unittest.TestCase):
    def test_valid_rows_and_normal_date_range(self):
        data = HEADER + (
            b"2024-01-02,10,11,9,10.5,nan,100,1050,A\n"
            b"2024-01-03,10.5,12,10,11,4.76,200,2200,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["invalid_ohlc"], 0)
        self.assertEqual(result["first_date"], "2024-01-02")
        self.assertEqual(result["last_date"], "2024-01-03")

    def test_duplicate_date_and_out_of_order_are_detected(self):
        data = HEADER + (
            b"2024-01-03,10,11,9,10,0,100,1000,A\n"
            b"2024-01-03,10,11,9,10,0,100,1000,A\n"
            b"2024-01-02,10,11,9,10,0,100,1000,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["duplicate_dates"], 1)
        self.assertEqual(result["out_of_order_transitions"], 1)

    def test_ohlc_bounds_and_fractional_volume_are_detected(self):
        data = HEADER + (
            b"2024-01-02,10,9,8,10,0,100.5,1000,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["invalid_ohlc"], 1)
        self.assertEqual(result["fractional_volume"], 1)
        self.assertEqual(result["valid_rows"], 0)
        sample = result["row_error_samples"]["invalid_ohlc_bounds"][0]
        self.assertEqual(sample["date"], "2024-01-02")
        self.assertEqual(sample["open"], 10)
        self.assertEqual(sample["high"], 9)
        self.assertEqual(sample["low"], 8)
        self.assertEqual(sample["close"], 10)

    def test_zero_turnover_with_volume_has_auditable_row_sample(self):
        data = HEADER + b"2024-01-02,10,11,9,10,nan,100,0,A\n"
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["zero_turnover_with_volume"], 1)
        sample = result["row_error_samples"]["zero_turnover_with_volume"][0]
        self.assertEqual(sample["date"], "2024-01-02")
        self.assertEqual(sample["volume"], 100)
        self.assertEqual(sample["turnover"], 0)

    def test_header_mismatch_fails_closed(self):
        result = audit_symbol_csv(
            b"date,open,high,low,close,volume\n2024-01-02,10,11,9,10,100\n",
            "TEST", "data/nepse/TEST.csv",
        )
        self.assertIn("header_mismatch", result)
        self.assertEqual(result["rows"], 0)


    def test_official_history_overlap_compares_five_independent_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "symbols"
            symbol_dir = root / "TEST"
            symbol_dir.mkdir(parents=True)
            raw = json.dumps({"content": [{
                "businessDate": "2024-01-02", "highPrice": 11, "lowPrice": 9,
                "closePrice": 10.5, "totalTradedQuantity": 100,
                "totalTradedValue": 1050,
            }]}).encode()
            (symbol_dir / "response-01.bin").write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest()
            (root.parent / "SHA256SUMS").write_text(
                f"{sha}  symbols/TEST/response-01.bin\n", encoding="utf-8"
            )
            public = HEADER + b"2024-01-02,10,11,9,10.5,nan,100,1050,A\n"
            result = crosscheck_official_history({"TEST": public}, root)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["official_rows"], 1)
            self.assertEqual(result["fully_matching_rows"], 1)
            self.assertEqual(result["field_comparisons"], 5)
            self.assertEqual(result["field_mismatches"], 0)

    def test_official_history_mismatch_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "symbols"
            symbol_dir = root / "TEST"
            symbol_dir.mkdir(parents=True)
            raw = json.dumps({"content": [{
                "businessDate": "2024-01-02", "highPrice": 11, "lowPrice": 9,
                "closePrice": 10.5, "totalTradedQuantity": 100,
                "totalTradedValue": 1050,
            }]}).encode()
            (symbol_dir / "response-01.bin").write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest()
            (root.parent / "SHA256SUMS").write_text(
                f"{sha}  symbols/TEST/response-01.bin\n", encoding="utf-8"
            )
            public = HEADER + b"2024-01-02,10,11,9,10.5,nan,101,1050,A\n"
            result = crosscheck_official_history({"TEST": public}, root)
            self.assertEqual(result["field_mismatches"], 1)
            self.assertEqual(result["mismatches_by_field"]["traded_quantity"], 1)

if __name__ == "__main__":
    unittest.main()
