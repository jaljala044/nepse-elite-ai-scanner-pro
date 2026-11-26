import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.broker_ingestion import payload_hash
from app.broker_ingestion_memory import ingest_and_persist_broker_batch
from app.broker_memory_store import BrokerMemoryStore


def row(**changes):
    payload = {"trade_id": "trade-1", "amount": "1250"}
    value = {
        "security_id": "CFCL", "broker_id": "BROKER-1",
        "session_date": "2026-11-25", "side": "BUY",
        "quantity": "10", "amount": "1250",
        "source_id": "SRC-A", "evidence_id": "E-1",
        "source_payload": payload, "source_payload_sha256": payload_hash(payload),
        "source_row_count": 1, "coverage_ratio": "1.0",
    }
    value.update(changes)
    return value


class BrokerIngestionMemoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BrokerMemoryStore(Path(self.tmp.name) / "memory.duckdb")

    def tearDown(self):
        self.tmp.cleanup()

    def run_batch(self, *, rows=None, **changes):
        args = {
            "store": self.store,
            "batch_id": "batch-2026-11-25",
            "rows": [row()] if rows is None else rows,
            "verified_brokers": {"BROKER-1"},
            "verified_sessions": {"2026-11-25"},
            "verified_session_finality": {"2026-11-25": "2026-11-25T15:00:00+05:45"},
            "expected_source_ids": {"SRC-A"},
            "received_source_ids": {"SRC-A"},
            "available_at": "2026-11-26T09:00:00+05:45",
            "as_of_date": "2026-11-26",
            "available_by": datetime(2026, 11, 26, 10, tzinfo=timezone.utc),
        }
        args.update(changes)
        return ingest_and_persist_broker_batch(**args)

    def test_eligible_batch_persists_daily_weekly_monthly_yearly_memory(self):
        result = self.run_batch()
        self.assertEqual(result["status"], "persisted")
        self.assertEqual(result["memory_rows"], 4)
        self.assertEqual(result["persistence"]["inserted"], 4)
        self.assertEqual(self.store.count(), 4)

    def test_exact_batch_replay_is_idempotent(self):
        first = self.run_batch()
        second = self.run_batch()
        self.assertEqual(first["persistence"]["inserted"], 4)
        self.assertEqual(second["persistence"]["inserted"], 0)
        self.assertEqual(second["persistence"]["replayed"], 4)
        self.assertEqual(self.store.count(), 4)

    def test_ineligible_source_batch_never_writes_memory(self):
        result = self.run_batch(received_source_ids=set())
        self.assertEqual(result["status"], "ingestion_rejected")
        self.assertEqual(self.store.count(), 0)

    def test_intraday_late_availability_never_writes_memory(self):
        result = self.run_batch(
            available_by=datetime(2026, 11, 26, 2, tzinfo=timezone.utc)
        )
        self.assertEqual(result["status"], "memory_admission_rejected")
        self.assertIsNone(result["persistence"])
        self.assertEqual(self.store.count(), 0)

    def test_contract_mismatch_never_writes_memory(self):
        from decimal import Decimal
        from app.broker_ingestion import ContractTotal
        result = self.run_batch(contracts=[
            ContractTotal("CFCL", "BROKER-1", "2026-11-25", "BUY",
                          Decimal("11"), Decimal("1250"))
        ])
        self.assertEqual(result["status"], "ingestion_rejected")
        self.assertEqual(self.store.count(), 0)


if __name__ == "__main__":
    unittest.main()
