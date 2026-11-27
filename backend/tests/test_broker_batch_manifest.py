import hashlib
import tempfile
import unittest
from pathlib import Path

from app.broker_batch_manifest import (
    BrokerRawCaptureRegistry, CaptureConflict, CaptureRejected, RawCaptureManifest,
)


def fixture(raw=b"official source extract"):
    manifest = RawCaptureManifest(
        manifest_version=1, trade_date="2026-11-25", source_id="SRC-A",
        capture_id="CAP-1", captured_at="2026-11-26T09:00:00+05:45",
        available_at="2026-11-26T09:01:00+05:45",
        source_rights_status="cleared", source_rights_evidence_id="RIGHTS-1",
        raw_sha256=hashlib.sha256(raw).hexdigest(), raw_byte_count=len(raw),
        parser_name="floorsheet-csv", parser_version="1.0.0", session_complete=True,
    )
    return manifest, raw


class BrokerRawCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = BrokerRawCaptureRegistry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_stage_preserves_exact_bytes_and_manifest(self):
        manifest, raw = fixture()
        result = self.registry.stage(manifest, raw)
        stored = self.registry.get(result["batch_id"])
        self.assertEqual(Path(stored["raw_object_path"]).read_bytes(), raw)
        self.assertEqual(stored["manifest"]["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(stored["state"], "staged")

    def test_identical_capture_is_idempotent_across_restart(self):
        manifest, raw = fixture()
        first = self.registry.stage(manifest, raw)
        restarted = BrokerRawCaptureRegistry(Path(self.tmp.name))
        second = restarted.stage(manifest, raw)
        self.assertEqual(first["batch_id"], second["batch_id"])
        self.assertTrue(second["idempotent_replay"])

    def test_changed_capture_metadata_is_conflict_not_overwrite(self):
        manifest, raw = fixture()
        self.registry.stage(manifest, raw)
        changed = RawCaptureManifest(**{**manifest.__dict__, "parser_version": "2.0.0"})
        with self.assertRaises(CaptureConflict):
            self.registry.stage(changed, raw)

    def test_raw_hash_and_byte_count_are_verified(self):
        manifest, raw = fixture()
        with self.assertRaises(CaptureRejected):
            self.registry.stage(RawCaptureManifest(**{**manifest.__dict__, "raw_byte_count": 1}), raw)
        with self.assertRaises(CaptureRejected):
            self.registry.stage(RawCaptureManifest(**{**manifest.__dict__, "raw_sha256": "0" * 64}), raw)

    def test_rights_denial_and_incomplete_session_are_quarantined(self):
        manifest, raw = fixture()
        denied = RawCaptureManifest(**{**manifest.__dict__, "source_rights_status": "denied"})
        incomplete = RawCaptureManifest(**{**manifest.__dict__, "capture_id": "CAP-2",
                                             "session_complete": False})
        self.assertEqual(self.registry.stage(denied, raw)["state"], "rejected")
        self.assertEqual(self.registry.stage(incomplete, raw)["state"], "rejected")

    def test_approval_requires_clean_dry_run_and_exact_report_hash(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        with self.assertRaises(CaptureRejected):
            self.registry.approve(batch, operator_id="operator-1", dry_run_sha256="x")
        report_hash = self.registry.record_dry_run(batch, {"passed": True, "quarantined_count": 0})
        with self.assertRaises(CaptureRejected):
            self.registry.approve(batch, operator_id="operator-1", dry_run_sha256="wrong")
        self.registry.approve(batch, operator_id="operator-1", dry_run_sha256=report_hash)
        self.registry.mark_admitted(batch, reconciler_memory_eligible=True)
        self.assertEqual(self.registry.get(batch)["state"], "admitted")
        self.assertEqual([e["event_type"] for e in self.registry.events(batch)],
                         ["staged", "dry_run_passed", "approved", "admitted"])

    def test_quarantined_dry_run_and_ineligible_reconciler_cannot_admit(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        self.registry.record_dry_run(batch, {"passed": False, "quarantined_count": 1})
        with self.assertRaises(CaptureRejected):
            self.registry.approve(batch, operator_id="operator-1", dry_run_sha256="irrelevant")
        manifest2, raw2 = fixture(b"another extract")
        manifest2 = RawCaptureManifest(**{**manifest2.__dict__, "capture_id": "CAP-2"})
        batch2 = self.registry.stage(manifest2, raw2)["batch_id"]
        digest = self.registry.record_dry_run(batch2, {"passed": True, "quarantined_count": 0})
        self.registry.approve(batch2, operator_id="operator-1", dry_run_sha256=digest)
        with self.assertRaises(CaptureRejected):
            self.registry.mark_admitted(batch2, reconciler_memory_eligible=False)


if __name__ == "__main__":
    unittest.main()
