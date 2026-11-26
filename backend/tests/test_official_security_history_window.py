import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_official_security_history_window import audit_history_window


class OfficialSecurityHistoryWindowTests(unittest.TestCase):
    def _fixture(self, root):
        start, end = "2026-10-05", "2026-11-26"
        dates = ["2026-11-19", "2026-11-20"]
        market = [
            {"businessDate": day, "totalTransactions": 100, "totalTradedShares": 1000,
             "totalTurnover": 100000, "tradedScrips": 10}
            for day in dates
        ]
        body = root / "market-body.json"
        raw = json.dumps(market).encode()
        body.write_bytes(raw)
        market_report = root / "market-report.json"
        market_report.write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY",
            "source_url": "https://nepalstock.com.np/api/nots/market-summary-history",
            "http_status": 200, "response_origin_verified": True,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "response_bytes": len(raw), "retrieved_at_utc": "2026-11-26T16:00:00Z",
        }))
        symbols = []
        for symbol, security_id in (("ABC", "1"), ("XYZ", "2")):
            rows = []
            for day in dates:
                zero = symbol == "XYZ"
                rows.append({
                    "business_date": day, "trades": 0 if zero else 2,
                    "volume": 0 if zero else 20, "turnover": 0 if zero else 2000,
                })
            url = f"https://nepalstock.com.np/api/nots/market/history/security/{security_id}?size=500&startDate={start}&endDate={end}"
            digest = hashlib.sha256((symbol + "payload").encode()).hexdigest()
            symbols.append({
                "symbol": symbol, "status": "ROWS_RETURNED_REVIEW_ONLY",
                "current_id_match": True, "current_security_list_id": security_id,
                "historical_security_identity_verified": False, "rows": rows,
                "response_sha256": digest,
                "responses": [{"url": url, "status": 200, "origin_verified": True, "sha256": digest}],
            })
        history = root / "history.json"
        history.write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME_HISTORY",
            "endpoint_path": "/api/nots/market/history/security/{security_id}",
            "requested_start_date": start, "requested_end_date": end,
            "historical_security_identity_verified": False, "security_list_error": None,
            "security_list_capture": [{
                "url": "https://nepalstock.com.np/api/nots/security?nonDelisted=true",
                "status": 200, "origin_verified": True,
            }],
            "symbols": symbols,
        }))
        return history, body, market_report, start, end

    def test_window_counts_explicit_zero_and_missing_is_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            report = audit_history_window(*args, expected_equity_count=2)
        self.assertEqual(report["official_market_summary_date_count"], 2)
        self.assertEqual(report["date_reports"]["2026-11-19"]["explicit_zero_activity_rows"], 1)
        self.assertEqual(report["date_reports"]["2026-11-19"]["positive_activity_rows"], 1)
        self.assertFalse(report["historical_security_identity_verified"])
        self.assertFalse(report["coverage_admission_allowed"])

    def test_missing_history_date_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            data = json.loads(args[0].read_text())
            data["symbols"][0]["rows"].pop()
            args[0].write_text(json.dumps(data))
            report = audit_history_window(*args, expected_equity_count=2)
        day = report["date_reports"]["2026-11-20"]
        self.assertEqual(day["current_equity_candidate_rows_missing"], 1)
        self.assertEqual(day["explicit_zero_activity_rows"], 1)
        self.assertIn("ABC", day["missing_symbols"])

    def test_bad_raw_summary_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            data = json.loads(args[2].read_text())
            data["response_sha256"] = "0" * 64
            args[2].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "hash/size"):
                audit_history_window(*args, expected_equity_count=2)

    def test_duplicate_history_date_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            data = json.loads(args[0].read_text())
            data["symbols"][0]["rows"].append(data["symbols"][0]["rows"][0])
            args[0].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "duplicate history row"):
                audit_history_window(*args, expected_equity_count=2)

    def test_inconsistent_zero_activity_metrics_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            data = json.loads(args[0].read_text())
            data["symbols"][0]["rows"][0]["volume"] = 0
            args[0].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                audit_history_window(*args, expected_equity_count=2)


if __name__ == "__main__":
    unittest.main()
