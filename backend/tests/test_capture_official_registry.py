import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capture_official_registry import capture_registry


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}

    def __init__(self, body=b'{"data":[]}', url="https://www.nepalstock.com.np/api/nots/security"):
        self.body = body
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body

    def geturl(self):
        return self.url


class CaptureOfficialRegistryTests(unittest.TestCase):
    def test_captures_json_bytes_and_leaves_schema_unreviewed(self):
        body = b'{"data":[]}'
        with tempfile.TemporaryDirectory() as tmp, patch(
            "capture_official_registry.urlopen", return_value=FakeResponse(body=body)
        ):
            result = capture_registry("https://www.nepalstock.com.np/api/nots/security",
                                      "nepse-security-list", tmp)
            self.assertEqual(result["raw_payload_sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)
            self.assertEqual(result["schema_review_status"], "unreviewed")
            self.assertFalse(result["manifest_verified"])

    def test_non_official_host_rejected(self):
        with self.assertRaisesRegex(ValueError, "approved official"):
            capture_registry("https://example.com/security", "x", tempfile.gettempdir())

    def test_non_json_content_type_rejected(self):
        response = FakeResponse()
        response.headers = {"Content-Type": "text/html"}
        with tempfile.TemporaryDirectory() as tmp, patch(
            "capture_official_registry.urlopen", return_value=response
        ):
            with self.assertRaisesRegex(ValueError, "content type is not JSON"):
                capture_registry("https://www.nepalstock.com.np/api/nots/security", "x", tmp)

    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "capture_official_registry.urlopen", return_value=FakeResponse(body=b"not-json")
        ):
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                capture_registry("https://www.nepalstock.com.np/api/nots/security", "x", tmp)


if __name__ == "__main__":
    unittest.main()
