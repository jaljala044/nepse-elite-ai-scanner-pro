import hashlib
import unittest
from app.historical_pilot_capture import validate_official_capture_manifest
from app.historical_pilot_ingest import ingest_captured_ohlcv_csv


class CapturedOHLCVIngestTests(unittest.TestCase):
    def fixture(self):
        raw = b"ticker,date,o,h,l,c,qty\\nAAA,2025-01-02,10,12,9,11,100\\n"
        digest = hashlib.sha256(raw).hexdigest()
        manifest = {
            "source_id": "SRC-1",
            "publisher_id": "PUB-1",
            "request_url": "https://source.example/floorsheet.csv",
            "captured_at": "2025-01-02T16:00:00+05:45",
            "available_at": "2025-01-02T16:00:00+05:45",
            "window_start": "2025-01-02T00:00:00+05:45",
            "window_end": "2025-01-02T23:59:59+05:45",
            "pages": [{
                "page_number": 1,
                "payload_id": "p1",
                "raw_sha256": digest,
                "http_status": 200,
                "final_page": True,
            }],
            "expected_page_count": 1,
            "capture_complete": True,
            "response_content_type": "text/csv",
            "capture_id": "CAP-1",
        }
        report = validate_official_capture_manifest(
            manifest,
            {"p1": raw},
            approved_registry=[{
                "source_id": "SRC-1",
                "publisher_id": "PUB-1",
                "review_status": "approved",
                "allowed_hosts": ["source.example"],
            }],
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )
        mapping = {
            "symbol": "ticker",
            "session_date": "date",
            "open": "o",
            "high": "h",
            "low": "l",
            "close": "c",
            "volume": "qty",
        }
        return raw, manifest, report, mapping

    def test_ingests_and_preserves_hash_provenance(self):
        raw, manifest, report, columns = self.fixture()
        out = ingest_captured_ohlcv_csv(
            capture_report=report,
            manifest=manifest,
            payloads={"p1": raw},
            column_map=columns,
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )
        self.assertEqual(out["status"], "INGESTED")
        self.assertEqual(out["rows"][0]["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(out["backtest_admission_allowed"])

    def test_changed_bytes_block(self):
        raw, manifest, report, columns = self.fixture()
        out = ingest_captured_ohlcv_csv(
            capture_report=report,
            manifest=manifest,
            payloads={"p1": raw + b"x"},
            column_map=columns,
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )
        self.assertEqual(out["status"], "BLOCKED")

    def test_missing_column_blocks(self):
        raw, manifest, report, columns = self.fixture()
        columns["volume"] = "missing"
        out = ingest_captured_ohlcv_csv(
            capture_report=report,
            manifest=manifest,
            payloads={"p1": raw},
            column_map=columns,
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )
        self.assertEqual(out["status"], "BLOCKED")

    def test_future_capture_blocks(self):
        raw, manifest, report, columns = self.fixture()
        manifest["available_at"] = "2025-01-04T00:00:00+05:45"
        out = ingest_captured_ohlcv_csv(
            capture_report=report,
            manifest=manifest,
            payloads={"p1": raw},
            column_map=columns,
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )
        self.assertEqual(out["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
