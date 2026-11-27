import hashlib
import unittest

from app.historical_pilot_capture import validate_official_capture_manifest
from app.historical_pilot_ingest import calculate_pilot_row_sha256, ingest_captured_ohlcv_csv


class CapturedOHLCVIngestTests(unittest.TestCase):
    CUTOFF = "2025-01-03T00:00:00+05:45"
    REGISTRY = [{
        "source_id": "SRC-1", "publisher_id": "PUB-1", "review_status": "approved",
        "allowed_hosts": ["official.example"],
    }]
    COLUMN_MAP = {
        "symbol": "ticker", "session_date": "date", "open": "o",
        "high": "h", "low": "l", "close": "c", "volume": "qty",
    }

    def fixture(self, csv_bytes=None):
        raw = csv_bytes or b"ticker,date,o,h,l,c,qty\nAAA,2025-01-02,10,12,9,11,100\n"
        digest = hashlib.sha256(raw).hexdigest()
        manifest = {
            "source_id": "SRC-1", "publisher_id": "PUB-1",
            "request_url": "https://official.example/history.csv",
            "captured_at": "2025-01-02T16:00:00+05:45",
            "available_at": "2025-01-02T16:00:00+05:45",
            "window_start": "2025-01-02T00:00:00+05:45",
            "window_end": "2025-01-02T23:59:59+05:45",
            "capture_id": "CAP-1", "expected_page_count": 1,
            "capture_complete": True, "response_content_type": "text/csv",
            "pages": [{
                "page_number": 1, "payload_id": "p1", "raw_sha256": digest,
                "http_status": 200, "final_page": True,
            }],
        }
        report = validate_official_capture_manifest(
            manifest, {"p1": raw}, approved_registry=self.REGISTRY,
            decision_cutoff=self.CUTOFF,
        )
        return raw, manifest, report

    def ingest(self, raw, manifest, report, mapping=None):
        return ingest_captured_ohlcv_csv(
            capture_report=report, manifest=manifest, payloads={"p1": raw},
            column_map=mapping or self.COLUMN_MAP, decision_cutoff=self.CUTOFF,
        )

    def test_ingests_exact_validated_manifest_and_preserves_row_fingerprint(self):
        raw, manifest, report = self.fixture()
        self.assertEqual(report["status"], "CAPTURE_VALIDATED")
        result = self.ingest(raw, manifest, report)
        self.assertEqual(result["status"], "INGESTED")
        self.assertEqual(result["rows"][0]["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            result["rows"][0]["row_sha256"],
            calculate_pilot_row_sha256(result["rows"][0]),
        )
        self.assertEqual(result["capture_manifest_sha256"], report["manifest_sha256"])
        self.assertFalse(result["backtest_admission_allowed"])

    def test_changed_payload_blocks(self):
        raw, manifest, report = self.fixture()
        result = ingest_captured_ohlcv_csv(
            capture_report=report, manifest=manifest, payloads={"p1": raw + b"x"},
            column_map=self.COLUMN_MAP, decision_cutoff=self.CUTOFF,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("hash" in item["reason"] for item in result["errors"]))

    def test_changed_manifest_after_validation_blocks(self):
        raw, manifest, report = self.fixture()
        manifest["available_at"] = "2025-01-02T16:01:00+05:45"
        result = self.ingest(raw, manifest, report)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["errors"][0]["reason"], "manifest_does_not_match_validated_capture")

    def test_nonfinite_prices_and_nonpositive_volume_block(self):
        for values in (
            b"AAA,2025-01-02,nan,12,9,11,100",
            b"AAA,2025-01-02,10,inf,9,11,100",
            b"AAA,2025-01-02,10,12,9,11,0",
        ):
            with self.subTest(values=values):
                raw, manifest, report = self.fixture(
                    b"ticker,date,o,h,l,c,qty\n" + values + b"\n"
                )
                result = self.ingest(raw, manifest, report)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertFalse(result["all_rows_accepted"])

    def test_fractional_volume_blocks(self):
        raw, manifest, report = self.fixture(
            b"ticker,date,o,h,l,c,qty\nAAA,2025-01-02,10,12,9,11,100.5\n"
        )
        self.assertEqual(self.ingest(raw, manifest, report)["status"], "BLOCKED")

    def test_missing_column_blocks(self):
        raw, manifest, report = self.fixture()
        mapping = dict(self.COLUMN_MAP, volume="missing")
        result = self.ingest(raw, manifest, report, mapping)
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_symbol_session_across_valid_pages_blocks(self):
        raw = b"ticker,date,o,h,l,c,qty\nAAA,2025-01-02,10,12,9,11,100\n"
        digest = hashlib.sha256(raw).hexdigest()
        manifest = {
            "source_id": "SRC-1", "publisher_id": "PUB-1",
            "request_url": "https://official.example/history.csv",
            "captured_at": "2025-01-02T16:00:00+05:45",
            "available_at": "2025-01-02T16:00:00+05:45",
            "window_start": "2025-01-02T00:00:00+05:45",
            "window_end": "2025-01-02T23:59:59+05:45",
            "capture_id": "CAP-2", "expected_page_count": 2,
            "capture_complete": True, "response_content_type": "text/csv",
            "pages": [
                {"page_number": 1, "payload_id": "p1", "raw_sha256": digest, "http_status": 200, "final_page": False},
                {"page_number": 2, "payload_id": "p2", "raw_sha256": digest, "http_status": 200, "final_page": True},
            ],
        }
        payloads = {"p1": raw, "p2": raw}
        report = validate_official_capture_manifest(
            manifest, payloads, approved_registry=self.REGISTRY, decision_cutoff=self.CUTOFF,
        )
        result = ingest_captured_ohlcv_csv(
            capture_report=report, manifest=manifest, payloads=payloads,
            column_map=self.COLUMN_MAP, decision_cutoff=self.CUTOFF,
        )
        self.assertEqual(report["status"], "CAPTURE_VALIDATED")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("duplicate" in item["reason"] for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
