import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_official_bulk_symbol_scope import audit_bulk_scope


class OfficialBulkSymbolScopeTests(unittest.TestCase):
    def _fixture(self, root):
        raw_dir = root / "raw"
        raw_dir.mkdir()
        days = ["2026-11-19"]
        rows = [
            {"businessDate": days[0], "securityId": 1, "symbol": "ABC", "securityName": "Alpha",
             "totalTrades": 2, "totalTradedQuantity": 20, "totalTradedValue": 2000},
            {"businessDate": days[0], "securityId": 2, "symbol": "MF1", "securityName": "Mutual Fund One",
             "totalTrades": 1, "totalTradedQuantity": 10, "totalTradedValue": 1000},
            {"businessDate": days[0], "securityId": 3, "symbol": "PROM", "securityName": "Promoter Share",
             "totalTrades": 1, "totalTradedQuantity": 5, "totalTradedValue": 500},
            {"businessDate": days[0], "securityId": 4, "symbol": "DEB", "securityName": "Debenture",
             "totalTrades": 1, "totalTradedQuantity": 6, "totalTradedValue": 600},
            {"businessDate": days[0], "securityId": 5, "symbol": "BOND", "securityName": "Government Bond",
             "totalTrades": 1, "totalTradedQuantity": 7, "totalTradedValue": 700},
            {"businessDate": days[0], "securityId": 6, "symbol": "UNK", "securityName": "Unclassified",
             "totalTrades": 1, "totalTradedQuantity": 8, "totalTradedValue": 800},
            {"businessDate": days[0], "securityId": 99, "symbol": "MISS", "securityName": "Missing snapshot",
             "totalTrades": 1, "totalTradedQuantity": 9, "totalTradedValue": 900},
        ]
        raw_path = raw_dir / "2026-11-19-response-body.bin"
        raw_bytes = json.dumps(rows).encode()
        raw_path.write_bytes(raw_bytes)
        bulk = root / "bulk.json"
        bulk.write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_BULK_DAILY_PRICE_VOLUME",
            "endpoint_path": "/api/nots/nepse-data/today-price",
            "date_reports": {
                days[0]: {
                    "capture_event": {
                        "requested_date": days[0], "query_business_date": days[0],
                        "url": f"https://nepalstock.com.np/api/nots/nepse-data/today-price?size=500&businessDate={days[0]}",
                        "status": 200, "origin_verified": True,
                        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        "raw_file": raw_path.name,
                    },
                    "response_bytes": len(raw_bytes),
                    "analysis": {"status": "ROWS_RETURNED_REVIEW_ONLY", "row_count": len(rows),
                                 "unique_symbol_count": len(rows), "rows": rows},
                }
            }
        }))
        summary_body = root / "summary.json"
        summary_body.write_text(json.dumps([{
            "businessDate": days[0], "totalTransactions": 8, "totalTradedShares": 65,
            "totalTurnover": 6500, "tradedScrips": 7,
        }]))
        summary_report = root / "summary-report.json"
        summary_raw = summary_body.read_bytes()
        summary_report.write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY", "http_status": 200,
            "source_url": "https://nepalstock.com.np/api/nots/market-summary-history",
            "response_origin_verified": True,
            "response_sha256": hashlib.sha256(summary_raw).hexdigest(),
            "response_bytes": len(summary_raw),
        }))
        snapshot = root / "snapshot.csv"
        with snapshot.open("w", newline="") as h:
            w = csv.DictWriter(h, fieldnames=["symbol", "security_id", "security_name", "active_status", "snapshot_date"])
            w.writeheader()
            for row in rows[:-1]:
                w.writerow({"symbol": row["symbol"], "security_id": row["securityId"],
                             "security_name": row["securityName"], "active_status": "A",
                             "snapshot_date": "2026-11-25"})
        crosswalk = root / "crosswalk.csv"
        with crosswalk.open("w", newline="") as h:
            w = csv.DictWriter(h, fieldnames=["symbol", "security_id", "security_name", "snapshot_date", "active_status", "crosswalk_status"])
            w.writeheader()
            w.writerow({"symbol": "ABC", "security_id": "1", "security_name": "Alpha",
                        "snapshot_date": "2026-11-25", "active_status": "A",
                        "crosswalk_status": "snapshot_id_match_active_status_A"})
        candidates = root / "candidates.csv"
        with candidates.open("w", newline="") as h:
            w = csv.DictWriter(h, fieldnames=["symbol", "instrument_class_from_rendered_list", "official_snapshot_id", "official_snapshot_status"])
            w.writeheader()
            w.writerow({"symbol": "MF1", "instrument_class_from_rendered_list": "Mutual Fund",
                        "official_snapshot_id": "2", "official_snapshot_status": "A"})
        return bulk, raw_dir, summary_body, summary_report, snapshot, crosswalk, candidates

    def test_classifies_equity_and_non_equity_and_keeps_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            report = audit_bulk_scope(*args)
        counts = report["dates"]["2026-11-19"]["scope_class_counts"]
        self.assertEqual(counts["IN_SCOPE_EQUITY_CANDIDATE"], 1)
        self.assertEqual(counts["OUT_OF_SCOPE_MUTUAL_FUND"], 1)
        self.assertEqual(counts["OUT_OF_SCOPE_PROMOTER_SHARE"], 1)
        self.assertEqual(counts["OUT_OF_SCOPE_DEBENTURE"], 1)
        self.assertEqual(counts["OUT_OF_SCOPE_BOND"], 1)
        self.assertEqual(counts["UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY"], 1)
        self.assertEqual(counts["UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH"], 1)
        self.assertFalse(report["historical_instrument_identity_verified"])
        self.assertFalse(report["coverage_admission_allowed"])

    def test_raw_bulk_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            raw_file = args[1] / "2026-11-19-response-body.bin"
            raw_file.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "raw response hash/size"):
                audit_bulk_scope(*args)

    def test_summary_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            data = json.loads(args[2].read_text())
            data[0]["tradedScrips"] = 8
            args[2].write_text(json.dumps(data))
            raw = args[2].read_bytes()
            report = json.loads(args[3].read_text())
            report["response_sha256"] = hashlib.sha256(raw).hexdigest()
            report["response_bytes"] = len(raw)
            args[3].write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "bulk symbol/aggregate totals"):
                audit_bulk_scope(*args)

    def test_target_candidate_id_mismatch_remains_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            candidates = args[6]
            rows = list(csv.DictReader(candidates.open()))
            rows[0]["official_snapshot_id"] = "999"
            with candidates.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            report = audit_bulk_scope(*args)
        counts = report["dates"]["2026-11-19"]["scope_class_counts"]
        self.assertEqual(counts["UNKNOWN_SECURITY_ID_MISMATCH"], 1)
        self.assertNotIn("OUT_OF_SCOPE_MUTUAL_FUND", counts)

    def test_snapshot_security_id_mismatch_remains_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._fixture(Path(tmp))
            snapshot = args[4]
            data = list(csv.DictReader(snapshot.open()))
            data[0]["security_id"] = "999"
            with snapshot.open("w", newline="") as h:
                w = csv.DictWriter(h, fieldnames=data[0].keys())
                w.writeheader()
                w.writerows(data)
            with self.assertRaisesRegex(ValueError, "crosswalk/current snapshot mismatch"):
                audit_bulk_scope(*args)


if __name__ == "__main__":
    unittest.main()
