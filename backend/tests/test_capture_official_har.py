import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from capture_official_har import capture_har_entry


def make_har(body: bytes, url="https://www.nepalstock.com.np/api/nots/security",
             content_type="application/json", encoding="base64", status=200):
    text = base64.b64encode(body).decode("ascii") if encoding == "base64" else body.decode("utf-8")
    return {
        "log": {
            "entries": [{
                "startedDateTime": "2026-11-27T02:00:00.000Z",
                "request": {"method": "GET", "url": url, "headers": [{"name": "Authorization", "value": "SECRET"}]},
                "response": {
                    "status": status,
                    "headers": [{"name": "Content-Type", "value": content_type}],
                    "content": {"size": len(body), "mimeType": content_type, "encoding": encoding, "text": text},
                    "redirectURL": "",
                },
            }]
        }
    }


class CaptureOfficialHarTests(unittest.TestCase):
    def _write_har(self, folder, archive):
        path = Path(folder) / "capture.har"
        path.write_text(json.dumps(archive), encoding="utf-8")
        return path

    def test_captures_exact_json_bytes_and_keeps_all_gates_closed(self):
        body = b'{"securities":[{"id":1,"symbol":"ABC"}]}'
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(body))
            result = capture_har_entry(har, 0, "nepse-registry", Path(tmp) / "out")
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)
            self.assertEqual(result["raw_payload_sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(result["raw_byte_count"], len(body))
            self.assertFalse(result["manifest_verified"])
            self.assertFalse(result["membership_admission_allowed"])
            self.assertFalse(result["production_sector_signals_allowed"])
            self.assertEqual(result["tls_verification_status"], "not_attested_by_har")
            self.assertEqual(result["hostname_verification_status"], "not_attested_by_har")
            self.assertNotIn("SECRET", json.dumps(result))

    def test_captures_pdf_bytes(self):
        body = b"%PDF-1.7\nfixture"
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(body, content_type="application/pdf"))
            result = capture_har_entry(har, 0, "sebon-pdf", Path(tmp) / "out")
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)
            self.assertTrue(result["raw_payload_path"].endswith(".pdf"))

    def test_plain_text_har_json_body_is_preserved_as_utf8(self):
        body = b'{"ok":true}'
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(body, encoding=""))
            result = capture_har_entry(har, 0, "registry", Path(tmp) / "out")
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)

    def test_rejects_non_official_or_non_https_url(self):
        for url in ("https://example.com/data", "http://www.nepalstock.com.np/data",
                    "https://nepalstock.com.np:8443/data",
                    "https://nepalstock.com.evil.example/data"):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                har = self._write_har(tmp, make_har(b'{"x":1}', url=url))
                with self.assertRaisesRegex(ValueError, "approved official"):
                    capture_har_entry(har, 0, "registry", Path(tmp) / "out")

    def test_captures_observed_nepalstock_com_catalogue_host(self):
        body = b'{"companies":[{"symbol":"NABIL"}]}'
        for host in ("nepalstock.com", "www.nepalstock.com"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                har = self._write_har(tmp, make_har(body, url=f"https://{host}/company"))
                result = capture_har_entry(har, 0, "nepse-company-catalogue", Path(tmp) / "out")
                self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), body)
                self.assertEqual(result["raw_payload_sha256"], hashlib.sha256(body).hexdigest())
                self.assertFalse(result["manifest_verified"])
                self.assertFalse(result["membership_admission_allowed"])

    def test_rejects_credential_like_query_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b'{"x":1}', url="https://www.nepalstock.com.np/api/list?token=secret"))
            with self.assertRaisesRegex(ValueError, "credential-like query"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")

    def test_rejects_non_200_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b'{"x":1}', status=302))
            with self.assertRaisesRegex(ValueError, "HTTP status 200"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")

    def test_rejects_missing_body_and_bad_base64(self):
        archive = make_har(b'{"x":1}')
        del archive["log"]["entries"][0]["response"]["content"]["text"]
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, archive)
            with self.assertRaisesRegex(ValueError, "body is missing"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")
        archive = make_har(b'{"x":1}')
        archive["log"]["entries"][0]["response"]["content"]["text"] = "%%%bad%%%"
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, archive)
            with self.assertRaisesRegex(ValueError, "encoding is invalid"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")

    def test_rejects_wrong_content_type_or_invalid_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b"<html/>", content_type="text/html"))
            with self.assertRaisesRegex(ValueError, "must be JSON or PDF"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b"not-json"))
            with self.assertRaisesRegex(ValueError, "JSON response body is invalid"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b"not-pdf", content_type="application/pdf"))
            with self.assertRaisesRegex(ValueError, "PDF signature"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out")

    def test_enforces_size_limit_and_safe_source_id_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b'{"x":"123456"}'))
            with self.assertRaisesRegex(ValueError, "exceeds max_response_bytes"):
                capture_har_entry(har, 0, "registry", Path(tmp) / "out", max_response_bytes=4)
            with self.assertRaisesRegex(ValueError, "filename-safe"):
                capture_har_entry(har, 0, "../escape", Path(tmp) / "out")
            with self.assertRaisesRegex(ValueError, "entry_index"):
                capture_har_entry(har, 3, "registry", Path(tmp) / "out")

    def test_same_capture_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write_har(tmp, make_har(b'{"x":1}'))
            out = Path(tmp) / "out"
            first = capture_har_entry(har, 0, "registry", out)
            second = capture_har_entry(har, 0, "registry", out)
            self.assertEqual(first["raw_payload_sha256"], second["raw_payload_sha256"])


if __name__ == "__main__":
    unittest.main()
