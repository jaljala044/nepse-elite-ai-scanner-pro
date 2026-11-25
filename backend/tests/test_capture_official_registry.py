import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capture_official_registry import ApprovedHostRedirectHandler, capture_registry


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

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout):
        return self.response


class CaptureOfficialRegistryTests(unittest.TestCase):
    def _mock_opener(self, response):
        return patch("capture_official_registry.build_opener", return_value=FakeOpener(response))

    def test_captures_json_bytes_and_leaves_schema_unreviewed(self):
        body = b'{"data":[]}'
        with tempfile.TemporaryDirectory() as tmp, self._mock_opener(FakeResponse(body=body)):
            result = capture_registry("https://www.nepalstock.com.np/api/nots/security",
                                      "nepse-security-list", tmp)
            self.assertEqual(result["raw_payload_sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)
            self.assertEqual(result["schema_review_status"], "unreviewed")
            self.assertFalse(result["manifest_verified"])

    def test_response_size_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp, self._mock_opener(
            FakeResponse(body=b'{"data":"123456"}')
        ):
            with self.assertRaisesRegex(ValueError, "exceeds max_response_bytes"):
                capture_registry("https://www.nepalstock.com.np/api/nots/security",
                                 "nepse-security-list", tmp, max_response_bytes=8)

    def test_source_id_cannot_escape_output_directory(self):
        with self.assertRaisesRegex(ValueError, "filename-safe"):
            capture_registry("https://www.nepalstock.com.np/api/nots/security",
                             "../outside", tempfile.gettempdir())

    def test_non_official_host_rejected(self):
        with self.assertRaisesRegex(ValueError, "approved official"):
            capture_registry("https://example.com/security", "x", tempfile.gettempdir())

    def test_nonstandard_port_rejected(self):
        with self.assertRaisesRegex(ValueError, "approved official"):
            capture_registry("https://www.nepalstock.com.np:8443/security", "x", tempfile.gettempdir())

    def test_non_json_content_type_rejected(self):
        response = FakeResponse()
        response.headers = {"Content-Type": "text/html"}
        with tempfile.TemporaryDirectory() as tmp, self._mock_opener(response):
            with self.assertRaisesRegex(ValueError, "content type is not JSON"):
                capture_registry("https://www.nepalstock.com.np/api/nots/security", "x", tmp)

    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, self._mock_opener(FakeResponse(body=b"not-json")):
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                capture_registry("https://www.nepalstock.com.np/api/nots/security", "x", tmp)

    def test_redirect_handler_rejects_unapproved_target_before_follow(self):
        handler = ApprovedHostRedirectHandler()
        with self.assertRaisesRegex(ValueError, "redirect target"):
            handler.redirect_request(None, None, 302, "Found", {}, "https://example.com/collect")

    def test_redirect_handler_rejects_http_and_nonstandard_port(self):
        handler = ApprovedHostRedirectHandler()
        for target in (
            "http://www.nepalstock.com.np/security",
            "https://www.nepalstock.com.np:8443/security",
        ):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "redirect target"):
                handler.redirect_request(None, None, 302, "Found", {}, target)

    def test_official_https_redirect_is_permitted(self):
        from urllib.request import Request
        handler = ApprovedHostRedirectHandler()
        original = Request("https://nepalstock.com.np/old")
        redirected = handler.redirect_request(
            original, None, 302, "Found", {}, "https://www.nepalstock.com.np/new"
        )
        self.assertEqual(redirected.full_url, "https://www.nepalstock.com.np/new")


if __name__ == "__main__":
    unittest.main()
