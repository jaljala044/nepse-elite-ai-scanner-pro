import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from capture_official_index_har import capture_index_har_entry


def har_entry(url, method, response_body=b'{"data":[]}', request_body=None):
    request = {
        "method": method,
        "url": url,
        "headers": [
            {"name": "Authorization", "value": "Bearer DO_NOT_COPY"},
            {"name": "Accept", "value": "application/json"},
            {"name": "Content-Type", "value": "application/json"},
        ],
    }
    if request_body is not None:
        request["postData"] = {"mimeType": "application/json", "text": json.dumps(request_body)}
    return {
        "log": {"entries": [{
            "startedDateTime": "2026-11-27T02:00:00.000Z",
            "request": request,
            "response": {
                "status": 200,
                "headers": [{"name": "Content-Type", "value": "application/json"}],
                "content": {"encoding": "base64", "text": base64.b64encode(response_body).decode()},
                "redirectURL": "",
            },
        }]}
    }


class CaptureOfficialIndexHarTests(unittest.TestCase):
    def _write(self, folder, value):
        path = Path(folder) / "index.har"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_graph_post_preserves_safe_request_and_response_evidence(self):
        body = {"id": 58}
        response = b'{"data":[{"date":"2026-11-26","close":2500}]}'
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write(tmp, har_entry(
                "https://www.nepalstock.com.np/api/nots/graph/index/58", "POST", response, body
            ))
            result = capture_index_har_entry(har, 0, "nepse-index-58", Path(tmp) / "out")
            self.assertEqual(result["route_family"], "candidate_graph_post")
            self.assertEqual(result["index_id"], 58)
            self.assertTrue(result["candidate_id_range_match"])
            self.assertEqual(Path(result["request_body_path"]).read_bytes(), b'{"id": 58}')
            self.assertEqual(result["request_body_sha256"], hashlib.sha256(b'{"id": 58}').hexdigest())
            self.assertEqual(Path(result["raw_payload_path"]).read_bytes(), response)
            self.assertEqual(result["request_sensitive_header_names_redacted"], ["authorization"])
            self.assertNotIn("DO_NOT_COPY", json.dumps(result))
            self.assertFalse(result["source_contract_verified"])
            self.assertFalse(result["history_completeness_verified"])
            self.assertFalse(result["evidence_gate_passed"])
            self.assertFalse(result["promotion_allowed"])

    def test_history_get_route_classified_without_claiming_verified_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write(tmp, har_entry(
                "https://www.nepalstock.com.np/index/history/58?startDate=2026-01-01",
                "GET",
            ))
            result = capture_index_har_entry(har, 0, "nepse-index-history-58", Path(tmp) / "out")
            self.assertEqual(result["route_family"], "candidate_index_history_get")
            self.assertEqual(result["request_query_parameters"], [
                {"name": "startDate", "value": "2026-01-01"}
            ])
            self.assertEqual(result["request_body_path"], None)
            self.assertEqual(result["route_contract_status"], "third_party_discovery_only")

    def test_rejects_method_path_mismatch_and_unknown_route(self):
        cases = [
            ("https://www.nepalstock.com.np/api/nots/graph/index/58", "GET", {"id": 58}),
            ("https://www.nepalstock.com.np/index/history/58", "POST", {"id": 58}),
            ("https://www.nepalstock.com.np/api/other/58", "GET", None),
        ]
        for url, method, body in cases:
            with self.subTest(url=url, method=method), tempfile.TemporaryDirectory() as tmp:
                har = self._write(tmp, har_entry(url, method, request_body=body))
                with self.assertRaisesRegex(ValueError, "documented candidate"):
                    capture_index_har_entry(har, 0, "candidate", Path(tmp) / "out")

    def test_rejects_credential_like_request_body_and_query(self):
        cases = [
            ("https://www.nepalstock.com.np/api/nots/graph/index/58", "POST",
             {"id": 58, "token": "secret"}),
            ("https://www.nepalstock.com.np/index/history/58?api_key=secret", "GET", None),
        ]
        for url, method, body in cases:
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                har = self._write(tmp, har_entry(url, method, request_body=body))
                with self.assertRaisesRegex(ValueError, "credential-like"):
                    capture_index_har_entry(har, 0, "candidate", Path(tmp) / "out")

    def test_rejects_graph_post_without_json_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            har = self._write(tmp, har_entry(
                "https://www.nepalstock.com.np/api/nots/graph/index/58", "POST"
            ))
            with self.assertRaisesRegex(ValueError, "body is missing"):
                capture_index_har_entry(har, 0, "candidate", Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
