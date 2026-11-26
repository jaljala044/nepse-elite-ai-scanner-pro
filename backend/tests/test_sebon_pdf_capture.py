import hashlib
import tempfile
import unittest
from pathlib import Path

import httpx

from app.sebon_pdf_capture import capture_sebon_pdf


class SebonPdfCaptureTests(unittest.TestCase):
    URL = "https://www.sebon.gov.np/uploads/example.pdf"
    PDF = b"%PDF-1.7\nfixture bytes\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "evidence"

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, status=200, content=None, headers=None, cert=b"fixture-cert"):
        def handler(request):
            response = httpx.Response(
                status,
                content=self.PDF if content is None else content,
                headers=headers or {"content-type": "application/pdf"},
                request=request,
            )
            # Supply a deterministic TLS peer object for the transport seam.
            class SSL:
                def getpeercert(self, binary_form=False):
                    return cert if binary_form else {}
            class Stream:
                def get_extra_info(self, key):
                    return SSL() if key == "ssl_object" else None
            response.extensions["network_stream"] = Stream()
            return response
        return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)

    def test_captures_and_persists_exact_pdf_bytes(self):
        result = capture_sebon_pdf(self.URL, storage_root=self.root, client=self.client())
        manifest = result["capture_manifest"]
        path = Path(result["storage"]["payload_path"])
        self.assertEqual(path.read_bytes(), self.PDF)
        self.assertEqual(manifest["payload_sha256"], hashlib.sha256(self.PDF).hexdigest())
        self.assertEqual(manifest["payload_bytes"], len(self.PDF))
        self.assertTrue(result["transport"]["tls_verified"])
        self.assertTrue(result["transport"]["hostname_verified"])
        self.assertFalse(result["membership_admission_allowed"])

    def test_rejects_non_official_host(self):
        with self.assertRaisesRegex(ValueError, "official_sebon"):
            capture_sebon_pdf("https://example.com/a.pdf", storage_root=self.root)

    def test_rejects_non_pdf_path(self):
        with self.assertRaisesRegex(ValueError, "official_sebon"):
            capture_sebon_pdf("https://www.sebon.gov.np/a.txt", storage_root=self.root)

    def test_rejects_non_200(self):
        with self.assertRaisesRegex(ValueError, "http_status_not_200"):
            capture_sebon_pdf(self.URL, storage_root=self.root, client=self.client(status=404))

    def test_rejects_non_pdf_content_type(self):
        with self.assertRaisesRegex(ValueError, "content_type_not_pdf"):
            capture_sebon_pdf(self.URL, storage_root=self.root,
                              client=self.client(headers={"content-type": "text/html"}))

    def test_rejects_invalid_pdf_magic(self):
        with self.assertRaisesRegex(ValueError, "body_not_pdf"):
            capture_sebon_pdf(self.URL, storage_root=self.root,
                              client=self.client(content=b"not a pdf"))

    def test_rejects_oversized_payload(self):
        with self.assertRaisesRegex(ValueError, "size_limit"):
            capture_sebon_pdf(self.URL, storage_root=self.root,
                              max_bytes=10, client=self.client())

    def test_rejects_missing_peer_certificate_evidence(self):
        with self.assertRaisesRegex(ValueError, "peer_certificate_unavailable"):
            capture_sebon_pdf(self.URL, storage_root=self.root,
                              client=self.client(cert=None))

    def test_exact_repeat_is_content_addressed(self):
        first = capture_sebon_pdf(self.URL, storage_root=self.root, client=self.client())
        second = capture_sebon_pdf(self.URL, storage_root=self.root, client=self.client())
        self.assertEqual(first["capture_manifest"]["payload_sha256"],
                         second["capture_manifest"]["payload_sha256"])
        self.assertEqual(first["storage"]["payload_path"], second["storage"]["payload_path"])


if __name__ == "__main__":
    unittest.main()
