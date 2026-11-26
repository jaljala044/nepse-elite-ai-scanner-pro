import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.official_market_summary_adapter import (
    MarketSummaryCaptureError,
    validate_official_market_summary_capture,
)


class OfficialMarketSummaryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = json.dumps([
            {"businessDate": "2026-11-25", "totalTurnover": 1000,
             "totalTradedShares": 100, "totalTransactions": 10, "tradedScrips": 5},
            {"businessDate": "2026-11-26", "totalTurnover": 1200,
             "totalTradedShares": 120, "totalTransactions": 12, "tradedScrips": 6},
        ]).encode()
        (self.root / "body.bin").write_bytes(self.raw)
        self.report = {
            "source_id": "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY",
            "source_url": "https://nepalstock.com.np/api/nots/market-summary-history",
            "retrieved_at_utc": "2026-11-26T16:00:20Z",
            "http_status": 200, "response_origin_verified": True,
            "response_preserved": True, "response_bytes": len(self.raw),
            "response_sha256": hashlib.sha256(self.raw).hexdigest(),
        }
        self.write_report()

    def tearDown(self):
        self.tmp.cleanup()

    def write_report(self):
        (self.root / "report.json").write_text(json.dumps(self.report), encoding="utf-8")

    def load(self, **kwargs):
        return validate_official_market_summary_capture(
            self.root, report_path="report.json", raw_payload_path="body.bin",
            decision_time="2026-11-27T12:00:00+05:45", **kwargs
        )

    def test_verified_origin_and_hash_produce_review_only_rows(self):
        result = self.load()
        self.assertEqual(result["status"], "review_only")
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["rows"][0]["record_type"], "market_summary")
        self.assertEqual(result["rows"][0]["source_validation_status"], "verified")
        self.assertEqual(result["rows"][0]["finality_status"], "unverified")
        self.assertFalse(result["rows"][0]["evidence_gate_passed"])
        self.assertFalse(result["promotion_allowed"])


    def test_committed_nepse_capture_is_source_verified_but_not_finality_promoted(self):
        repo_root = Path(__file__).resolve().parents[2]
        result = validate_official_market_summary_capture(
            repo_root,
            report_path="data/evidence/raw/nepse/market-summary-history/2026-11-26/capture-report.json",
            raw_payload_path="data/evidence/raw/nepse/market-summary-history/2026-11-26/response-body.bin",
            decision_time="2026-11-27T12:00:00+05:45",
        )
        self.assertEqual(result["record_count"], 229)
        self.assertEqual(result["last_session"], "2026-11-26")
        self.assertEqual(result["status"], "review_only")
        self.assertFalse(result["promotion_allowed"])

    def test_raw_payload_hash_mismatch_is_rejected(self):
        (self.root / "body.bin").write_bytes(self.raw + b" ")
        with self.assertRaisesRegex(MarketSummaryCaptureError, "sha256_mismatch"):
            self.load()

    def test_non_official_host_is_rejected(self):
        self.report["source_url"] = "https://example.com/api/nots/market-summary-history"
        self.write_report()
        with self.assertRaisesRegex(MarketSummaryCaptureError, "origin_or_endpoint"):
            self.load()

    def test_future_capture_is_rejected(self):
        self.report["retrieved_at_utc"] = "2026-11-28T00:00:00Z"
        self.write_report()
        with self.assertRaisesRegex(MarketSummaryCaptureError, "retrieved_after_decision"):
            self.load()

    def test_stale_capture_is_rejected(self):
        self.report["retrieved_at_utc"] = "2026-11-01T00:00:00Z"
        self.write_report()
        with self.assertRaisesRegex(MarketSummaryCaptureError, "capture_stale"):
            self.load()

    def test_duplicate_sessions_are_rejected(self):
        duplicate = json.loads(self.raw)
        duplicate.append(dict(duplicate[-1]))
        raw = json.dumps(duplicate).encode()
        (self.root / "body.bin").write_bytes(raw)
        self.report["response_sha256"] = hashlib.sha256(raw).hexdigest()
        self.report["response_bytes"] = len(raw)
        self.write_report()
        with self.assertRaisesRegex(MarketSummaryCaptureError, "duplicate_market_summary_date"):
            self.load()

    def test_zero_turnover_is_not_promoted_as_trading_session(self):
        invalid = json.loads(self.raw)
        invalid[0]["totalTurnover"] = 0
        raw = json.dumps(invalid).encode()
        (self.root / "body.bin").write_bytes(raw)
        self.report["response_sha256"] = hashlib.sha256(raw).hexdigest()
        self.report["response_bytes"] = len(raw)
        self.write_report()
        with self.assertRaisesRegex(MarketSummaryCaptureError, "total_turnover_must_be_finite_and_positive"):
            self.load()


if __name__ == "__main__":
    unittest.main()
