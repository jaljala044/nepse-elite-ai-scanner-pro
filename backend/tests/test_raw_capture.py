import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.raw_capture import (
    CaptureConflictError,
    build_capture_manifest,
    persist_capture,
)


class RawCaptureTests(unittest.TestCase):
    def manifest(self, payload=b"exact bytes", **overrides):
        args = {
            "source_id": "test-source",
            "source_url": "https://example.invalid/floorsheet",
            "request_method": "GET",
            "request_metadata": {"date": "2026-11-24"},
            "requested_at": "2026-11-25T00:00:00+05:45",
            "received_at": "2026-11-25T00:00:01+05:45",
            "claimed_session_date": "2026-11-24",
            "fetch_id": "fetch-001",
        }
        args.update(overrides)
        return build_capture_manifest(payload, **args)

    def test_hash_and_exact_byte_count(self):
        payload = b"raw\x00response"
        manifest = self.manifest(payload)
        self.assertEqual(manifest["payload_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(manifest["payload_bytes"], len(payload))
        self.assertEqual(manifest["requested_at_utc"], "2026-11-24T18:15:00Z")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.manifest(requested_at="2026-11-25T00:00:00")

    def test_confirmed_open_requires_verified_date(self):
        with self.assertRaises(ValueError):
            self.manifest(session_status="confirmed_open")

    def test_confirmed_closed_requires_evidence(self):
        with self.assertRaises(ValueError):
            self.manifest(session_status="confirmed_closed")

    def test_persist_is_idempotent_and_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = b"payload\r\n"
            manifest = self.manifest(payload)
            first = persist_capture(tmp, payload, manifest)
            second = persist_capture(tmp, payload, manifest)
            self.assertFalse(first["idempotent"])
            self.assertTrue(second["idempotent"])
            self.assertEqual(Path(first["payload_path"]).read_bytes(), payload)
            saved = json.loads(Path(first["manifest_path"]).read_text())
            self.assertEqual(saved["payload_sha256"], manifest["payload_sha256"])

    def test_manifest_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.manifest()
            with self.assertRaises(ValueError):
                persist_capture(tmp, b"different", manifest)

    def test_conflicting_manifest_for_same_payload_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = b"same payload"
            first = self.manifest(payload, fetch_id="first")
            second = self.manifest(payload, fetch_id="second")
            persist_capture(tmp, payload, first)
            with self.assertRaises(CaptureConflictError):
                persist_capture(tmp, payload, second)
            manifest_path = Path(tmp) / "test-source" / "2026-11-24" / hashlib.sha256(payload).hexdigest() / "manifest.json"
            self.assertEqual(json.loads(manifest_path.read_text())["fetch_id"], "first")


if __name__ == "__main__":
    unittest.main()
