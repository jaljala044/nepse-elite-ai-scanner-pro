import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.broker_batch_manifest import (
    BrokerRawCaptureRegistry, CaptureConflict, CaptureRejected, RawCaptureManifest, SourceRightsEvidence,
)
from app.broker_daily_history import BrokerDailyHistoryStore, DailyHistoryRejected
from app.broker_ingestion import IngestionReport


def fixture(raw=b"official source extract"):
    manifest = RawCaptureManifest(
        manifest_version=1, trade_date="2026-11-25", source_id="SRC-A",
        capture_id="CAP-1", captured_at="2026-11-26T09:00:00+05:45",
        available_at="2026-11-26T09:01:00+05:45",
        source_rights_status="cleared", source_rights_evidence_id="RIGHTS-1",
        source_rights_evidence=SourceRightsEvidence(
            source_id="SRC-A", evidence_id="RIGHTS-1", decision="cleared",
            terms_url="https://publisher.example/terms", terms_sha256="c" * 64,
            retrieved_at="2026-11-25T15:00:00+05:45",
            permitted_uses=("internal_research", "broker_aggregation"), reviewer_id="reviewer-1"),
        raw_sha256=hashlib.sha256(raw).hexdigest(), raw_byte_count=len(raw),
        parser_name="floorsheet-csv", parser_version="1.0.0", session_complete=True,
    )
    return manifest, raw


def clean_report(batch_id):
    return IngestionReport(
        batch_id=batch_id, coverage_status="complete", coverage_ratio="1",
        accepted=[{
            "security_id": "SEC-CFCL", "broker_id": "BROKER-17",
            "session_date": "2026-11-25", "side": "BUY", "quantity": "2",
            "amount": "100", "source_id": "SRC-A", "evidence_id": "E-1",
            "source_payload_sha256": "a" * 64, "source_row_count": 1,
            "coverage_ratio": "1", "batch_id": batch_id,
            "available_at": "2026-11-26T09:01:00+05:45",
            "status": "descriptive_only",
            "raw_record_lineage": [{
                "raw_record_sha256": "b" * 64,
                "raw_record_locator": "csv:row:2",
                "contract_id": "CONTRACT-1",
            }],
        }],
    )


def coverage_manifest():
    return {
        "session_date": "2026-11-25", "source_coverage_status": "complete",
        "source_coverage_ratio": "1", "source_control_reconciled": True,
        "identity_coverage_status": "complete", "identity_coverage_rows": 1,
        "identity_coverage_min": "1", "verified_session": True,
        "available_at": "2026-11-26T09:01:00+05:45",
    }


class BrokerRawCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = BrokerRawCaptureRegistry(self.root)

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
        restarted = BrokerRawCaptureRegistry(self.root)
        second = restarted.stage(manifest, raw)
        self.assertEqual(first["batch_id"], second["batch_id"])
        self.assertTrue(second["idempotent_replay"])

    def test_changed_capture_metadata_is_conflict_not_overwrite(self):
        manifest, raw = fixture()
        self.registry.stage(manifest, raw)
        changed = RawCaptureManifest(**{**manifest.__dict__, "parser_version": "2.0.0"})
        with self.assertRaises(CaptureConflict):
            self.registry.stage(changed, raw)

    def test_changed_raw_bytes_under_same_capture_identity_are_conflicts(self):
        manifest, raw = fixture()
        self.registry.stage(manifest, raw)
        changed_raw = b"corrected source extract"
        changed_manifest = RawCaptureManifest(**{
            **manifest.__dict__,
            "raw_sha256": hashlib.sha256(changed_raw).hexdigest(),
            "raw_byte_count": len(changed_raw),
        })
        with self.assertRaises(CaptureConflict):
            self.registry.stage(changed_manifest, changed_raw)

    def test_late_available_capture_is_retained_with_both_timestamps(self):
        manifest, raw = fixture()
        late = RawCaptureManifest(**{
            **manifest.__dict__,
            "captured_at": "2026-11-25T16:00:00+05:45",
            "available_at": "2026-11-27T09:00:00+05:45",
        })
        result = self.registry.stage(late, raw)
        stored = self.registry.get(result["batch_id"])["manifest"]
        self.assertEqual(stored["captured_at"], "2026-11-25T10:15:00+00:00")
        self.assertEqual(stored["available_at"], "2026-11-27T03:15:00+00:00")

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


    def test_structured_rights_evidence_is_required_and_bound_to_manifest(self):
        manifest, raw = fixture()
        missing = RawCaptureManifest(**{**manifest.__dict__, 'source_rights_evidence': None})
        with self.assertRaisesRegex(CaptureRejected, 'structured_source_rights_evidence_required'):
            self.registry.stage(missing, raw)
        wrong_source = SourceRightsEvidence(**{**manifest.source_rights_evidence.__dict__, 'source_id': 'OTHER'})
        with self.assertRaisesRegex(CaptureRejected, 'rights_evidence_source_mismatch'):
            self.registry.stage(RawCaptureManifest(**{**manifest.__dict__, 'source_rights_evidence': wrong_source}), raw)
        wrong_id = SourceRightsEvidence(**{**manifest.source_rights_evidence.__dict__, 'evidence_id': 'OTHER'})
        with self.assertRaisesRegex(CaptureRejected, 'rights_evidence_id_mismatch'):
            self.registry.stage(RawCaptureManifest(**{**manifest.__dict__, 'source_rights_evidence': wrong_id}), raw)

    def test_rights_evidence_requires_https_hash_reviewer_and_permitted_use(self):
        manifest, raw = fixture()
        base = manifest.source_rights_evidence
        invalids = [({'terms_url': 'http://publisher.example/terms'}, 'rights_terms_url_must_be_https'),
                    ({'terms_sha256': 'bad'}, 'invalid_rights_terms_sha256'),
                    ({'reviewer_id': ''}, 'rights_reviewer_required'),
                    ({'permitted_uses': ('internal_research',)}, 'broker_aggregation_not_permitted')]
        for changes, reason in invalids:
            evidence = SourceRightsEvidence(**{**base.__dict__, **changes})
            candidate = RawCaptureManifest(**{**manifest.__dict__, 'source_rights_evidence': evidence})
            with self.subTest(reason=reason), self.assertRaisesRegex(CaptureRejected, reason):
                self.registry.stage(candidate, raw)

    def test_expired_rights_evidence_is_rejected(self):
        manifest, raw = fixture()
        expired = SourceRightsEvidence(**{**manifest.source_rights_evidence.__dict__, 'expires_at': '2026-11-26T08:30:00+05:45'})
        candidate = RawCaptureManifest(**{**manifest.__dict__, 'source_rights_evidence': expired})
        with self.assertRaisesRegex(CaptureRejected, 'rights_evidence_expired_at_capture'):
            self.registry.stage(candidate, raw)

    def test_rights_evidence_is_persisted_in_manifest(self):
        manifest, raw = fixture()
        result = self.registry.stage(manifest, raw)
        evidence = self.registry.get(result['batch_id'])['manifest']['source_rights_evidence']
        self.assertEqual(evidence['terms_sha256'], 'c' * 64)
        self.assertEqual(evidence['permitted_uses'], ['broker_aggregation', 'internal_research'])
        self.assertEqual(evidence['reviewer_id'], 'reviewer-1')

    def test_approval_requires_typed_clean_reconciliation_and_exact_hash(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        with self.assertRaises(CaptureRejected):
            self.registry.record_dry_run(batch, {"passed": True, "quarantined_count": 0})
        report = clean_report(batch)
        report_hash = self.registry.record_dry_run(batch, report)
        with self.assertRaises(CaptureRejected):
            self.registry.approve(batch, operator_id="operator-1", dry_run_sha256="wrong")
        self.registry.approve(batch, operator_id="operator-1", dry_run_sha256=report_hash)
        self.assertEqual(self.registry.get(batch)["state"], "approved")

    def test_quarantined_reconciliation_cannot_pass_dry_run_or_be_approved(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        report = clean_report(batch)
        report.accepted[0]["raw_capture_sha256"] = manifest.raw_sha256
        report.quarantined.append({"row_index": 0, "reasons": ["invalid"]})
        with self.assertRaises(CaptureRejected):
            self.registry.record_dry_run(batch, report)
        with self.assertRaises(CaptureRejected):
            self.registry.approve(batch, operator_id="operator-1", dry_run_sha256="irrelevant")

    def test_approved_capture_appends_to_daily_history_and_records_receipt(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        report = clean_report(batch)
        report.accepted[0]["raw_capture_sha256"] = manifest.raw_sha256
        digest = self.registry.record_dry_run(batch, report)
        self.registry.approve(batch, operator_id="operator-1", dry_run_sha256=digest)
        history = BrokerDailyHistoryStore(self.root / "daily.duckdb")
        receipt = self.registry.admit_to_daily_history(
            batch, report, coverage_manifest=coverage_manifest(), history_store=history)
        self.assertEqual(receipt["inserted"], 1)
        self.assertEqual(self.registry.get(batch)["state"], "admitted")
        self.assertEqual(history.count(), 1)
        stored_rows = history.observations_as_of(
            as_of_date="2026-11-25",
            as_of_timestamp="2026-11-27T00:00:00+05:45")
        self.assertEqual(stored_rows[0]["raw_capture_sha256"], manifest.raw_sha256)
        record_lineage = json.loads(stored_rows[0]["raw_record_lineage_json"])
        self.assertEqual(record_lineage[0]["raw_record_sha256"], "b" * 64)
        self.assertEqual(record_lineage[0]["raw_record_locator"], "csv:row:2")
        self.assertEqual(record_lineage[0]["contract_id"], "CONTRACT-1")
        self.assertEqual(stored_rows[0]["raw_capture_batch_id"], manifest.capture_id)
        self.assertEqual(stored_rows[0]["raw_capture_captured_at"], "2026-11-26 03:15:00+00")
        self.assertEqual(stored_rows[0]["raw_capture_available_at"], "2026-11-26 03:16:00+00")
        self.assertEqual(stored_rows[0]["parser_name"], manifest.parser_name)
        self.assertEqual(stored_rows[0]["parser_version"], manifest.parser_version)
        self.assertEqual(stored_rows[0]["reconciliation_sha256"], digest)
        events = self.registry.events(batch)
        self.assertEqual([e["event_type"] for e in events],
                         ["staged", "dry_run_passed", "approved", "admitted"])
        self.assertIn("daily_history_receipt", events[-1]["detail"])

    def test_changed_reconciliation_after_approval_is_rejected(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        report = clean_report(batch)
        report.accepted[0]["raw_capture_sha256"] = manifest.raw_sha256
        digest = self.registry.record_dry_run(batch, report)
        self.registry.approve(batch, operator_id="operator-1", dry_run_sha256=digest)
        changed = clean_report(batch)
        changed.accepted[0]["raw_capture_sha256"] = manifest.raw_sha256
        changed.accepted[0]["amount"] = "999"
        history = BrokerDailyHistoryStore(self.root / "daily.duckdb")
        with self.assertRaises(CaptureRejected):
            self.registry.admit_to_daily_history(
                batch, changed, coverage_manifest=coverage_manifest(), history_store=history)
        self.assertEqual(history.count(), 0)

    def test_dry_run_requires_matching_per_row_raw_capture_provenance(self):
        for mutation in ("missing_locator", "wrong_capture_hash"):
            root = self.root / mutation
            registry = BrokerRawCaptureRegistry(root)
            manifest, raw = fixture()
            batch = registry.stage(manifest, raw)["batch_id"]
            report = clean_report(batch)
            if mutation == "missing_locator":
                report.accepted[0]["raw_record_lineage"][0].pop("raw_record_locator")
            else:
                report.accepted[0]["raw_capture_sha256"] = "0" * 64
            with self.assertRaises(CaptureRejected):
                registry.record_dry_run(batch, report)
            self.assertEqual(registry.get(batch)["state"], "staged")

    def test_daily_ledger_cannot_precede_raw_source_availability(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        report = clean_report(batch)
        report.accepted[0]["raw_capture_sha256"] = manifest.raw_sha256
        digest = self.registry.record_dry_run(batch, report)
        self.registry.approve(batch, operator_id="operator-1", dry_run_sha256=digest)
        late_coverage = coverage_manifest()
        late_coverage["available_at"] = "2026-11-26T09:00:00+05:45"
        history = BrokerDailyHistoryStore(self.root / "daily.duckdb")
        with self.assertRaises(DailyHistoryRejected):
            self.registry.admit_to_daily_history(
                batch, report, coverage_manifest=late_coverage, history_store=history)
        self.assertEqual(history.count(), 0)

    def test_unapproved_or_ineligible_batches_cannot_reach_daily_history(self):
        manifest, raw = fixture()
        batch = self.registry.stage(manifest, raw)["batch_id"]
        history = BrokerDailyHistoryStore(self.root / "daily.duckdb")
        with self.assertRaises(CaptureRejected):
            self.registry.admit_to_daily_history(
                batch, clean_report(batch), coverage_manifest=coverage_manifest(),
                history_store=history)
        self.assertEqual(history.count(), 0)


if __name__ == "__main__":
    unittest.main()
