import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_official_market_summary_reconciliation import load_official_summary, reconcile


class OfficialSummaryReconciliationTests(unittest.TestCase):
    def _fixture(self, root):
        official = root / "official"
        floors = root / "floors"
        official.mkdir()
        floors.mkdir()
        payload = []
        for day in ("2026-11-19", "2026-11-20", "2026-11-24"):
            payload.append({
                "businessDate": day,
                "totalTurnover": 1000,
                "totalTradedShares": 10,
                "totalTransactions": 2,
                "tradedScrips": 1,
            })
            for source in ("samir", "socrateai"):
                path = floors / f"{source}-{day}.csv"
                fields = (["date", "contract_no", "stock_symbol", "quantity", "amount"]
                          if source == "samir" else
                          ["date", "transaction", "symbol", "quantity", "amount"])
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    for n in (1, 2):
                        writer.writerow({
                            "date": day,
                            "contract_no" if source == "samir" else "transaction": str(n),
                            "stock_symbol" if source == "samir" else "symbol": "ABC",
                            "quantity": "5",
                            "amount": "500",
                        })
        raw = json.dumps(payload).encode()
        (official / "response-body.bin").write_bytes(raw)
        (official / "capture-report.json").write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY",
            "source_url": "https://nepalstock.com.np/api/nots/market-summary-history",
            "http_status": 200,
            "response_origin_verified": True,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "response_bytes": len(raw),
            "retrieved_at_utc": "2026-11-26T16:00:00Z",
        }))
        return official, floors

    def test_official_totals_match_both_pinned_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            official, floors = self._fixture(Path(tmp))
            report = reconcile(official, floors)
        self.assertTrue(report["official_aggregate_control_verified"])
        for day in report["date_reports"].values():
            self.assertTrue(day["sources"]["samir"]["all_aggregate_metrics_match"])
            self.assertTrue(day["sources"]["socrateai"]["all_aggregate_metrics_match"])
        self.assertFalse(report["coverage_admission_allowed"])

    def test_tampered_official_raw_bytes_fail_digest_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            official, _ = self._fixture(Path(tmp))
            (official / "response-body.bin").write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "digest/size"):
                load_official_summary(official)

    def test_unapproved_host_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            official, _ = self._fixture(Path(tmp))
            report_path = official / "capture-report.json"
            report = json.loads(report_path.read_text())
            report["source_url"] = "https://example.invalid/api/nots/market-summary-history"
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "outside the approved"):
                load_official_summary(official)

    def test_missing_official_date_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            official, floors = self._fixture(Path(tmp))
            body = json.loads((official / "response-body.bin").read_text())
            body = [row for row in body if row["businessDate"] != "2026-11-20"]
            raw = json.dumps(body).encode()
            (official / "response-body.bin").write_bytes(raw)
            report_path = official / "capture-report.json"
            report = json.loads(report_path.read_text())
            report["response_sha256"] = hashlib.sha256(raw).hexdigest()
            report["response_bytes"] = len(raw)
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "no row for required date"):
                reconcile(official, floors)


if __name__ == "__main__":
    unittest.main()
