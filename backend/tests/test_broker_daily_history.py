import tempfile
import unittest
from pathlib import Path

from app.broker_ingestion import reconcile_broker_batch, payload_hash
from app.broker_daily_history import (
    BrokerDailyHistoryStore, DailyHistoryConflict, DailyHistoryRejected,
)


def source_row(day="2026-11-25", evidence="E1", side="BUY", amount="100"):
    payload={"evidence":evidence,"amount":amount}
    return {"security_id":"SEC-CFCL","broker_id":"BROKER-17","session_date":day,
        "side":side,"quantity":"2","amount":amount,"source_id":"SRC-FLOORSHEET",
        "evidence_id":evidence,"source_payload":payload,
        "source_payload_sha256":payload_hash(payload),"source_row_count":1,"coverage_ratio":"1"}


def rights_evidence():
    return {"SRC-FLOORSHEET": {"source_id": "SRC-FLOORSHEET", "evidence_id": "TEST-RIGHTS",
        "status": "approved", "document_sha256": "d" * 64,
        "scope": ["electronic_storage", "aggregation"], "effective_from": "2020-01-01",
        "effective_to": None, "available_at": "2026-11-24T09:00:00+05:45"}}


def report(rows, batch_id="BATCH-2026-11-25"):
    days={r["session_date"] for r in rows}
    return reconcile_broker_batch(batch_id=batch_id,rows=rows,
        verified_brokers={"BROKER-17"},verified_sessions=days,
        expected_source_ids={"SRC-FLOORSHEET"},received_source_ids={"SRC-FLOORSHEET"},
        available_at="2026-11-26T10:00:00+05:45",
        verified_session_finality={d:d+"T16:00:00+05:45" for d in days},
        source_rights_evidence=rights_evidence())


def manifest(day="2026-11-25"):
    return {"session_date":day,"source_coverage_status":"complete",
        "source_coverage_ratio":"1","source_control_reconciled":True,
        "identity_coverage_status":"complete","identity_coverage_rows":2,
        "identity_coverage_min":"0.99","verified_session":True,
        "available_at":"2026-11-26T10:00:00+05:45"}


class BrokerDailyHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=BrokerDailyHistoryStore(Path(self.tmp.name)/"history.duckdb")
    def tearDown(self): self.tmp.cleanup()

    def test_persists_verified_daily_observations_and_manifest(self):
        result=self.store.append_validated_daily_batch(
            report([source_row(),source_row(evidence="E2",side="SELL",amount="40")]),
            coverage_manifest=manifest())
        self.assertEqual(result["inserted"],2)
        self.assertEqual(self.store.count(),2)
        self.assertEqual(self.store.complete_sessions_as_of(
            as_of_date="2026-11-25",as_of_timestamp="2026-11-26T11:00:00+05:45"),
            ["2026-11-25"])

    def test_exact_replay_is_idempotent(self):
        r=report([source_row()])
        first=self.store.append_validated_daily_batch(r,coverage_manifest=manifest())
        second=self.store.append_validated_daily_batch(r,coverage_manifest=manifest())
        self.assertEqual(first["inserted"],1)
        self.assertEqual(second["replayed"],1)
        self.assertEqual(self.store.count(),1)

    def test_conflicting_replay_rolls_back(self):
        self.store.append_validated_daily_batch(report([source_row()]),coverage_manifest=manifest())
        changed=report([source_row(amount="101")])
        with self.assertRaises(DailyHistoryConflict):
            self.store.append_validated_daily_batch(changed,coverage_manifest=manifest())
        self.assertEqual(self.store.count(),1)

    def test_incomplete_source_manifest_rejected(self):
        m=manifest(); m["source_coverage_status"]="partial"
        with self.assertRaises(DailyHistoryRejected):
            self.store.append_validated_daily_batch(report([source_row()]),coverage_manifest=m)

    def test_identity_coverage_below_threshold_rejected(self):
        m=manifest(); m["identity_coverage_min"]="0.94"
        with self.assertRaises(DailyHistoryRejected):
            self.store.append_validated_daily_batch(report([source_row()]),coverage_manifest=m)

    def test_source_controls_must_be_reconciled(self):
        m=manifest(); m["source_control_reconciled"]=False
        with self.assertRaises(DailyHistoryRejected):
            self.store.append_validated_daily_batch(report([source_row()]),coverage_manifest=m)

    def test_empty_batch_is_unknown_not_zero(self):
        r=report([source_row()])
        r.accepted=[]
        with self.assertRaises(DailyHistoryRejected):
            self.store.append_validated_daily_batch(r,coverage_manifest=manifest())

    def test_as_of_hides_late_available_observations_and_manifest(self):
        self.store.append_validated_daily_batch(report([source_row()]),coverage_manifest=manifest())
        self.assertEqual(self.store.observations_as_of(
            as_of_date="2026-11-25",as_of_timestamp="2026-11-26T09:00:00+05:45"),[])
        self.assertEqual(self.store.complete_sessions_as_of(
            as_of_date="2026-11-25",as_of_timestamp="2026-11-26T09:00:00+05:45"),[])

    def test_multiple_sessions_in_one_daily_batch_rejected(self):
        with self.assertRaises(DailyHistoryRejected):
            self.store.append_validated_daily_batch(
                report([source_row("2026-11-24"),source_row("2026-11-25",evidence="E2")]),
                coverage_manifest=manifest("2026-11-25"))

if __name__=="__main__": unittest.main()
