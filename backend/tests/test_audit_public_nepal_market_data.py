import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_public_nepal_market_data import (
    audit_symbol_csv, crosscheck_official_history, compare_socrateai_daily_csvs,
)


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


    def test_socrateai_daily_archive_matches_official_fields(self):
        official = [{
            "businessDate": "2026-11-26", "symbol": "CFCL",
            "highPrice": 570.8, "lowPrice": 550, "closePrice": 561,
            "totalTradedQuantity": 87614, "totalTradedValue": 49159830.2,
        }]
        daily = {
            "2026-11-26": (
                b"date,close,open,high,low,volume,symbol\n"
                b"2026-11-26,561,550,570.8,550,87614,CFCL\n"
            )
        }
        result = compare_socrateai_daily_csvs(official, daily)
        self.assertEqual(result["official_rows_matched_by_date"], 1)
        self.assertEqual(result["fully_matching_rows"], 1)
        self.assertEqual(result["field_comparisons"], 4)
        self.assertEqual(result["field_mismatches"], 0)

    def test_socrateai_daily_archive_records_volume_mismatch(self):
        official = [{
            "businessDate": "2026-11-18", "symbol": "CFCL",
            "highPrice": 640, "lowPrice": 589.9, "closePrice": 589.9,
            "totalTradedQuantity": 307576, "totalTradedValue": 184031033.4,
        }]
        daily = {
            "2026-11-18": (
                b"date,close,open,high,low,volume,symbol\n"
                b"2026-11-18,589.9,598.5,640,589.9,307567,CFCL\n"
            )
        }
        result = compare_socrateai_daily_csvs(official, daily)
        self.assertEqual(result["field_mismatches"], 1)
        self.assertEqual(result["mismatches_by_field"]["volume"], 1)
        self.assertEqual(result["field_error_stats"]["volume"]["max_absolute_difference"], 9)
        self.assertAlmostEqual(
            result["field_error_stats"]["volume"]["max_relative_difference_pct"],
            9 / 307576 * 100,
            places=6,
        )

    def test_socrateai_daily_archive_missing_active_row_is_counted(self):
        official = [{
            "businessDate": "2026-11-26", "symbol": "CFCL",
            "highPrice": 570.8, "lowPrice": 550, "closePrice": 561,
            "totalTradedQuantity": 87614, "totalTradedValue": 49159830.2,
        }]
        result = compare_socrateai_daily_csvs(official, {})
        self.assertEqual(result["missing_public_files"], ["2026-11-26"])
        self.assertEqual(result["missing_public_active_rows"], 1)


    def _write_official_capture(self, evidence_root, start_date, end_date, symbol_rows):
        evidence_root.mkdir(parents=True, exist_ok=True)
        symbols_root = evidence_root / "symbols"
        symbols_root.mkdir(parents=True, exist_ok=True)
        security_list = b"[]"
        (evidence_root / "security-list-response-01.bin").write_bytes(security_list)
        manifest_lines = [
            f"{hashlib.sha256(security_list).hexdigest()}  security-list-response-01.bin\\n"
        ]
        symbol_items = []
        for symbol, security_id, rows in symbol_rows:
            folder = symbols_root / symbol
            folder.mkdir(parents=True, exist_ok=True)
            raw = json.dumps({"content": rows}).encode()
            raw_path = folder / "response-01.bin"
            raw_path.write_bytes(raw)
            relative = f"symbols/{symbol}/response-01.bin"
            sha = hashlib.sha256(raw).hexdigest()
            manifest_lines.append(f"{sha}  {relative}\\n")
            normalized = [{
                "business_date": row["businessDate"],
                "trades": row["totalTrades"],
                "volume": row["totalTradedQuantity"],
                "turnover": row["totalTradedValue"],
                "raw": row,
            } for row in rows]
            url = (
                "https://nepalstock.com.np/api/nots/market/history/security/"
                f"{security_id}?size=500&startDate={start_date}&endDate={end_date}"
            )
            symbol_items.append({
                "symbol": symbol, "crosswalk_security_id": security_id,
                "current_security_list_id": security_id, "current_id_match": True,
                "historical_security_identity_verified": False,
                "status": "ROWS_RETURNED_REVIEW_ONLY", "rows": normalized,
                "response_sha256": sha, "responses": [{
                    "status": 200, "origin_verified": True, "url": url,
                    "sha256": sha, "raw_file": relative,
                }],
            })
        (evidence_root / "SHA256SUMS").write_text("".join(manifest_lines))
        capture = {
            "source_id": "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME_HISTORY",
            "endpoint_path": "/api/nots/market/history/security/{security_id}",
            "requested_start_date": start_date, "requested_end_date": end_date,
            "security_list_error": None,
            "security_list_capture": [{
                "status": 200, "origin_verified": True,
                "url": "https://nepalstock.com.np/api/nots/security?nonDelisted=true",
                "sha256": hashlib.sha256(security_list).hexdigest(),
                "raw_file": "security-list-response-01.bin",
            }],
            "symbols": symbol_items,
            "historical_security_identity_verified": False,
        }
        (evidence_root / "capture-report.json").write_text(json.dumps(capture))
        return symbols_root

    def _official_row(self, day, close=10):
        return {
            "businessDate": day, "totalTrades": 1, "totalTradedQuantity": 10,
            "totalTradedValue": close * 10, "highPrice": close + 1,
            "lowPrice": close - 1, "closePrice": close,
        }

    def test_merges_overlapping_official_windows_and_verifies_raw_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            long_root = self._write_official_capture(
                base / "long", "2024-01-02", "2024-01-03",
                [("TEST", "1", [self._official_row("2024-01-02"),
                                self._official_row("2024-01-03")])],
            )
            short_root = self._write_official_capture(
                base / "short", "2024-01-03", "2024-01-03",
                [("TEST", "1", [self._official_row("2024-01-03")])],
            )
            lifecycle = base / "lifecycle.csv"
            lifecycle.write_text(
                "security_id,symbol,valid_from,valid_from_evidence_status\\n"
                "1,TEST,,unverified\\n"
            )
            merged_root = base / "merged" / "symbols"
            result = build_merged_official_history_root(
                [long_root, short_root], merged_root,
                ["2024-01-02", "2024-01-03"], lifecycle,
            )
            merged = json.loads((merged_root / "TEST" / "response-01.bin").read_text())
            self.assertEqual(len(merged["content"]), 2)
            self.assertEqual(result["official_rows_after_merge"], 2)
            self.assertEqual(result["overlap_rows_compared"], 1)
            self.assertEqual(result["overlap_mismatch_rows"], 0)
            self.assertEqual(result["missing_symbol_date_pairs"], 0)
            self.assertEqual(result["gate"], "RECONCILED_REVIEW_ONLY")

    def test_official_window_overlap_mismatch_fails_review_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            long_root = self._write_official_capture(
                base / "long", "2024-01-02", "2024-01-03",
                [("TEST", "1", [self._official_row("2024-01-02"),
                                self._official_row("2024-01-03", close=10)])],
            )
            short_root = self._write_official_capture(
                base / "short", "2024-01-03", "2024-01-03",
                [("TEST", "1", [self._official_row("2024-01-03", close=11)])],
            )
            lifecycle = base / "lifecycle.csv"
            lifecycle.write_text(
                "security_id,symbol,valid_from,valid_from_evidence_status\\n"
                "1,TEST,,unverified\\n"
            )
            result = build_merged_official_history_root(
                [long_root, short_root], base / "merged" / "symbols",
                ["2024-01-02", "2024-01-03"], lifecycle,
            )
            self.assertEqual(result["overlap_mismatch_rows"], 1)
            self.assertEqual(result["gate"], "FAIL")

if __name__ == "__main__":
    unittest.main()
