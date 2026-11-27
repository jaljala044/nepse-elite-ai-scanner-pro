import hashlib
import unittest

from app.historical_pilot_capture import manifest_sha256, validate_official_capture_manifest


class OfficialCaptureManifestTests(unittest.TestCase):
    def fixture(self):
        raw = b"symbol,price\nAAA,100\n"
        manifest = {
            "source_id": "NEPSE-FS", "publisher_id": "NEPSE",
            "request_url": "https://api.nepalstock.com/floorsheet?date=2025-01-02",
            "captured_at": "2025-01-02T16:00:00+05:45",
            "available_at": "2025-01-02T16:00:00+05:45",
            "window_start": "2025-01-02T00:00:00+05:45",
            "window_end": "2025-01-02T23:59:00+05:45",
            "pages": [{
                "page_number": 1, "payload_id": "p1",
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "http_status": 200, "final_page": True,
            }],
            "expected_page_count": 1, "capture_complete": True,
            "response_content_type": "text/csv", "capture_id": "CAP-1",
        }
        registry = [{
            "source_id": "NEPSE-FS", "publisher_id": "NEPSE",
            "review_status": "approved", "allowed_hosts": ["api.nepalstock.com"],
        }]
        return raw, manifest, registry

    def validate(self, manifest, payloads, registry):
        return validate_official_capture_manifest(
            manifest, payloads, approved_registry=registry,
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )

    def test_valid_capture_hashes_exact_bytes_and_manifest(self):
        raw, manifest, registry = self.fixture()
        result = self.validate(manifest, {"p1": raw}, registry)
        self.assertEqual(result["status"], "CAPTURE_VALIDATED")
        self.assertEqual(result["manifest_sha256"], manifest_sha256(manifest))
        self.assertFalse(result["backtest_admission_allowed"])

    def test_payload_tampering_blocks(self):
        raw, manifest, registry = self.fixture()
        result = self.validate(manifest, {"p1": raw + b"x"}, registry)
        self.assertEqual(result["status"], "CAPTURE_BLOCKED")
        self.assertIn("raw_payload_sha256_mismatch", [item["reason"] for item in result["errors"]])

    def test_incomplete_pages_block(self):
        raw, manifest, registry = self.fixture()
        manifest["expected_page_count"] = 2
        result = self.validate(manifest, {"p1": raw}, registry)
        self.assertIn("pagination_incomplete_or_noncontiguous", [item["reason"] for item in result["errors"]])

    def test_duplicate_payload_id_blocks(self):
        raw, manifest, registry = self.fixture()
        manifest["expected_page_count"] = 2
        manifest["pages"] = [
            dict(manifest["pages"][0], final_page=False),
            dict(manifest["pages"][0], page_number=2, final_page=True),
        ]
        result = self.validate(manifest, {"p1": raw}, registry)
        self.assertIn("missing_or_duplicate_payload_id", [item["reason"] for item in result["errors"]])

    def test_nonfinal_page_flag_must_be_last(self):
        raw, manifest, registry = self.fixture()
        manifest["expected_page_count"] = 2
        manifest["pages"] = [
            dict(manifest["pages"][0], final_page=True),
            dict(manifest["pages"][0], page_number=2, payload_id="p2", final_page=False),
        ]
        manifest["pages"][1]["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        result = self.validate(manifest, {"p1": raw, "p2": raw}, registry)
        self.assertIn("final_page_not_unique_and_last", [item["reason"] for item in result["errors"]])

    def test_unapproved_host_blocks(self):
        raw, manifest, registry = self.fixture()
        manifest["request_url"] = "http://evil.example/data"
        result = self.validate(manifest, {"p1": raw}, registry)
        self.assertIn("request_url_not_https_allowlisted", [item["reason"] for item in result["errors"]])


if __name__ == "__main__":
    unittest.main()
