import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.floorsheet_source_capture import (
    FloorsheetCapturePolicy,
    FloorsheetCaptureRejected,
    capture_public_floorsheet,
)


class FakeResponse:
    def __init__(self, payload=b'{"trades":[]}', status=200,
                 content_type="application/json", content_length=None):
        self.payload = payload
        self.status = status
        self.headers = {"Content-Type": content_type}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.closed = False

    def getcode(self):
        return self.status

    def read(self, limit=-1):
        return self.payload[:limit]

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


class FloorsheetSourceCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.policy = FloorsheetCapturePolicy(
            source_id="REVIEW_PENDING_PROVIDER",
            allowed_host="example.test",
            allowed_path_prefix="/api/floorsheet",
            max_response_bytes=100,
            rights_status="review_required",
            parser_version="not-yet-assigned",
        )
        self.times = iter([
            datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 11, 26, 10, 0, 1, tzinfo=timezone.utc),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def capture(self, url="https://example.test/api/floorsheet",
                opener=None, policy=None):
        return capture_public_floorsheet(
            url,
            policy=policy or self.policy,
            storage_root=self.tmp.name,
            fetch_id="fetch-001",
            opener=opener or FakeOpener(),
            clock=lambda: next(self.times),
        )

    def test_exact_response_is_captured_with_hash_and_metadata(self):
        opener = FakeOpener(FakeResponse(b'{"trades":[1]}'))
        result = self.capture(opener=opener)
        self.assertEqual(result["status"], "captured")
        self.assertEqual(result["payload_bytes"], len(b'{"trades":[1]}'))
        self.assertEqual(len(result["payload_sha256"]), 64)
        self.assertFalse(result["canonical_eligible"])
        self.assertFalse(result["production_eligible"])
        self.assertTrue(opener.response.closed)
        self.assertEqual(opener.calls[0][0].get_method(), "GET")

    def test_exact_replay_is_idempotent(self):
        self.capture(opener=FakeOpener(FakeResponse()))
        # Use the same manifest times to make the exact fetch receipt identical.
        fixed = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
        result = capture_public_floorsheet(
            "https://example.test/api/floorsheet",
            policy=self.policy, storage_root=self.tmp.name, fetch_id="fetch-001",
            opener=FakeOpener(FakeResponse()),
            clock=lambda: fixed,
        )
        self.assertTrue(result["capture"]["idempotent"])

    def test_non_https_or_unlisted_host_is_rejected_before_network(self):
        opener = FakeOpener()
        for url in (
            "http://example.test/api/floorsheet",
            "https://evil.test/api/floorsheet",
            "https://example.test:444/api/floorsheet",
            "https://user:pass@example.test/api/floorsheet",
            "https://example.test/api/floorsheet?token=secret",
        ):
            with self.subTest(url=url), self.assertRaises(FloorsheetCaptureRejected):
                self.capture(url=url, opener=opener)
        self.assertEqual(opener.calls, [])

    def test_path_prefix_is_enforced(self):
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "path_not_allowlisted"):
            self.capture(url="https://example.test/api/other")

    def test_redirect_and_non_200_responses_are_rejected(self):
        from urllib.error import HTTPError
        opener = FakeOpener(error=HTTPError(
            "https://example.test/api/floorsheet", 302, "redirect", {}, None
        ))
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "redirect_rejected"):
            self.capture(opener=opener)
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "http_status_not_accepted:503"):
            self.capture(opener=FakeOpener(FakeResponse(status=503)))

    def test_content_type_empty_body_and_size_are_rejected(self):
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "content_type_not_allowlisted"):
            self.capture(opener=FakeOpener(FakeResponse(content_type="text/html")))
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "empty_response_body"):
            self.capture(opener=FakeOpener(FakeResponse(b"")))
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "response_exceeds_size_limit"):
            self.capture(opener=FakeOpener(FakeResponse(b"x" * 101)))

    def test_declared_content_length_is_checked_before_read(self):
        response = FakeResponse(content_length=101)
        with self.assertRaisesRegex(FloorsheetCaptureRejected, "response_exceeds_size_limit"):
            self.capture(opener=FakeOpener(response))
        self.assertTrue(response.closed)

    def test_policy_rejects_invalid_limits_and_hosts(self):
        with self.assertRaises(ValueError):
            FloorsheetCapturePolicy("SRC", "https://example.test", "/")
        with self.assertRaises(ValueError):
            FloorsheetCapturePolicy("SRC", "example.test", "/api/../private")


if __name__ == "__main__":
    unittest.main()
