from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from capture_nepse_security_classification import capture, main


class _Response:
    def __init__(self, body: bytes, page: int):
        self.url = f"https://nepalstock.com.np/api/nots/security/classification?page={page}"
        self.status_code = 200
        self.content = body
        self.headers = {"content-type": "application/json"}

    def read(self):
        return self.content


class _PaginatedClient:
    "("""
    def __init__(self, timeout, pages):
        self.headers = {}
        self.client = SimpleNamespace(event_hooks={"response": []})
        self.pages = pages

    def requestGETAPI(self, path):
        page = int(path.rsplit("page=", 1)[1])
        body = self.pages[page]
        response = _Response(body, page)
        for hook in self.client.event_hooks["response"]:
            hook(response)
        return json.loads(body)

    def close(self):
        pass


class NepseSecurityClassificationCaptureTests(unittest.TestCase):
    def test_capture_preserves_all_pages_and_rows(self):
        pages = {
            0: b'{"content":[{"id":1,"symbol":"AAA","listingDate":"2020-01-01","tradingStartDate":"2020-01-02"}],"totalPages":2}',
            1: b'{"content":[{"id":2,"symbol":"BBB","listingDate":"2021-05-05","tradingStartDate":"2021-05-06"}],"totalPages":2}',
        }

        class Client(_PaginatedClient):
            def __init__(self, timeout):
                super().__init__(timeout, pages)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=Client)}):
                report = capture(Path(tmp))
            self.assertEqual(report["pages_captured"], 2)
            self.assertEqual(report["row_count"], 2)
            self.assertEqual(report["unique_symbol_count"], 2)
            self.assertEqual(report["request_errors"], [])
            checksums = (Path(tmp) / "SHA256SUMS").read_text()
            self.assertEqual(len(checksums.strip().splitlines()), 2)
            parsed = json.loads((Path(tmp) / "parsed-classification.json").read_text())
            self.assertEqual([r["symbol"] for r in parsed], ["AAA", "BBB"])
            self.assertFalse(report["canonical_promotion_allowed"])

    def test_capture_records_request_errors_without_promotion(self):
        class OfflineClient:
            def __init__(self, timeout):
                self.headers = {}
                self.client = SimpleNamespace(event_hooks={"response": []})

            def requestGETAPI(self, path):
                raise RuntimeError("fixture network failure")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=OfflineClient)}):
                report = capture(Path(tmp))
        self.assertEqual(report["pages_captured"], 0)
        self.assertEqual(report["row_count"], 0)
        self.assertEqual(report["request_errors"][0]["type"], "RuntimeError")
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_main_prints_summary(self):
        class EmptyClient:
            def __init__(self, timeout):
                self.headers = {}
                self.client = SimpleNamespace(event_hooks={"response": []})

            def requestGETAPI(self, path):
                return {"content": [], "totalPages": 1}

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch.dict(sys.modules, {"nepse_client": SimpleNamespace(NepseClient=EmptyClient)}):
                with patch.object(sys, "argv", ["capture", "--output-dir", tmp]):
                    with redirect_stdout(output):
                        exit_code = main()
            summary = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["row_count"], 0)


if __name__ == "__main__":
    unittest.main()
