import tempfile
import unittest
from pathlib import Path
from app.broker_ingestion import payload_hash, reconcile_broker_batch
from app.broker_memory_store import BrokerMemoryStore
from app.broker_memory_promotion import PromotionRejected, promote_validated_batch

def row(day, evidence, side="BUY", amount="100"):
    payload = {"record": evidence, "amount": amount}
    return {"security_id":"CFCL","broker_id":"B-17","session_date":day,"side":side,
        "quantity":"2","amount":amount,"source_id":"SRC-A","evidence_id":evidence,
        "source_payload":payload,"source_payload_sha256":payload_hash(payload),
        "source_row_count":1,"coverage_ratio":"1"}

def rights_evidence():
    return {"SRC-FLOORSHEET": {"source_id": "SRC-FLOORSHEET", "evidence_id": "TEST-RIGHTS",
        "status": "approved", "document_sha256": "d" * 64,
        "scope": ["electronic_storage", "aggregation"], "effective_from": "2020-01-01",
        "effective_to": None, "available_at": "2026-11-24T09:00:00+05:45"}}


def report(rows):
    return reconcile_broker_batch(batch_id="batch-2026-11-24", rows=rows,
        verified_brokers={"B-17"}, verified_sessions={r["session_date"] for r in rows},
        expected_source_ids={"SRC-A"}, received_source_ids={"SRC-A"},
        available_at="2026-11-25T10:00:00+05:45",
        verified_session_finality={r["session_date"]: r["session_date"] + "T16:00:00+05:45" for r in rows})

class BrokerMemoryPromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=BrokerMemoryStore(Path(self.tmp.name)/"memory.duckdb")
    def tearDown(self): self.tmp.cleanup()

    def test_ineligible_batch_rejected_without_store_write(self):
        invalid=report([row("2026-11-24","E1")])
        invalid.quarantined.append({"reasons":["synthetic quarantine"]})
        with self.assertRaises(PromotionRejected):
            promote_validated_batch(invalid,self.store,as_of_date="2026-11-25")
        self.assertEqual(self.store.count(),0)

    def test_promotes_only_windows_with_enough_distinct_dates(self):
        rows=[row(f"2026-11-{day:02d}",f"E{day}") for day in range(19,25)]
        result=promote_validated_batch(report(rows),self.store,as_of_date="2026-11-25")
        self.assertEqual(result["promoted_snapshots"],2)
        self.assertEqual({x["window"] for x in result["withheld_windows"]},{"monthly","yearly"})
        self.assertEqual(self.store.count(),2)

    def test_replay_is_idempotent(self):
        rows=[row("2026-11-24","E1")]
        first=promote_validated_batch(report(rows),self.store,as_of_date="2026-11-25")
        second=promote_validated_batch(report(rows),self.store,as_of_date="2026-11-25")
        self.assertEqual(first["persistence"]["inserted"],1)
        self.assertEqual(second["persistence"]["replayed"],1)
        self.assertEqual(self.store.count(),1)

    def test_persisted_snapshot_retains_evidence_and_descriptive_status(self):
        rows=[row("2026-11-24","E1","BUY","120"),row("2026-11-24","E2","SELL","20")]
        promote_validated_batch(report(rows),self.store,as_of_date="2026-11-25")
        saved=self.store.get_as_of(security_id="CFCL",broker_entity_id="B-17",as_of_date="2026-11-25")
        snap=saved[0]["snapshot"]
        self.assertEqual(snap["net_amount"],"100")
        self.assertEqual(snap["status"],"descriptive_only")
        self.assertEqual(set(snap["evidence_ids"]),{"E1","E2"})
        self.assertEqual(snap["source_batch_ids"],["batch-2026-11-24"])


    def test_conflicting_replay_rolls_back_entire_multi_window_append(self):
        from app.broker_memory_store import IdempotencyConflict
        first_rows=[row("2026-11-24","E1")]
        promote_validated_batch(report(first_rows),self.store,as_of_date="2026-11-25")
        self.assertEqual(self.store.count(),1)
        changed_rows=[row(f"2026-11-{day:02d}",f"E{day}", "BUY", "999" if day == 24 else "100") for day in range(20,25)]
        with self.assertRaises(IdempotencyConflict):
            promote_validated_batch(report(changed_rows),self.store,as_of_date="2026-11-25")
        self.assertEqual(self.store.count(),1)

    def test_no_observation_window_is_fabricated(self):
        result=promote_validated_batch(report([row("2026-11-24","E1")]),self.store,as_of_date="2026-11-25")
        self.assertEqual(result["promoted_snapshots"],1)
        self.assertEqual(self.store.count(),1)

    def test_as_of_before_availability_rejected(self):
        with self.assertRaises(PromotionRejected):
            promote_validated_batch(report([row("2026-11-24","E1")]),self.store,as_of_date="2026-11-24")
        self.assertEqual(self.store.count(),0)

if __name__=="__main__": unittest.main()
