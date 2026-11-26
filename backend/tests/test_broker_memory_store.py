import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.broker_memory_store import BrokerMemoryStore, IdempotencyConflict


def snapshot(**changes):
    value = {
        "as_of_date": "2026-11-24", "security_id": "SEC-1",
        "broker_entity_id": "BROKER-1", "window": "weekly",
        "buy_amount": "120.50", "sell_amount": "20.00", "net_amount": "100.50",
        "source_ids": ["SRC-1"], "evidence_ids": ["E-1"],
        "payload_hashes": ["a" * 64], "status": "descriptive_only",
    }
    value.update(changes)
    return value


class BrokerMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "memory.duckdb"
        self.store = BrokerMemoryStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_persists_and_reopens(self):
        result = self.store.append(snapshot(), idempotency_key="run-1")
        self.assertTrue(result["inserted"])
        reopened = BrokerMemoryStore(self.path)
        self.assertEqual(reopened.count(), 1)

    def test_exact_replay_is_idempotent(self):
        first = self.store.append(snapshot(), idempotency_key="run-1")
        second = self.store.append(snapshot(), idempotency_key="run-1")
        self.assertTrue(first["inserted"])
        self.assertFalse(second["inserted"])
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(self.store.count(), 1)

    def test_changed_payload_under_same_key_is_rejected(self):
        self.store.append(snapshot(), idempotency_key="run-1")
        with self.assertRaises(IdempotencyConflict):
            self.store.append(snapshot(net_amount="999"), idempotency_key="run-1")
        self.assertEqual(self.store.count(), 1)

    def test_distinct_run_key_preserves_new_version(self):
        self.store.append(snapshot(), idempotency_key="run-1")
        self.store.append(snapshot(net_amount="101"), idempotency_key="run-2")
        self.assertEqual(self.store.count(), 2)

    def test_as_of_query_hides_future_event_and_late_available_rows(self):
        self.store.append(snapshot(), idempotency_key="old",
                          available_at=datetime(2026, 11, 24, 10, tzinfo=timezone.utc))
        self.store.append(snapshot(as_of_date="2026-11-25"), idempotency_key="future",
                          available_at=datetime(2026, 11, 25, 10, tzinfo=timezone.utc))
        self.store.append(snapshot(net_amount="200"), idempotency_key="late",
                          available_at=datetime(2026, 11, 26, 10, tzinfo=timezone.utc))
        rows = self.store.get_as_of(
            security_id="SEC-1", broker_entity_id="BROKER-1",
            as_of_date="2026-11-25",
            available_by=datetime(2026, 11, 25, 23, tzinfo=timezone.utc),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["snapshot"]["net_amount"], "100.50")

    def test_non_descriptive_snapshot_rejected(self):
        with self.assertRaisesRegex(ValueError, "descriptive_only"):
            self.store.append(snapshot(status="accumulation"), idempotency_key="bad")

    def test_naive_availability_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.store.append(snapshot(), idempotency_key="naive",
                              available_at=datetime(2026, 11, 24))

    def test_append_many_replays_without_duplicates(self):
        first = self.store.append_many([snapshot()], key_prefix="daily-2026-11-24")
        second = self.store.append_many([snapshot()], key_prefix="daily-2026-11-24")
        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["replayed"], 1)
        self.assertEqual(self.store.count(), 1)


if __name__ == "__main__":
    unittest.main()
