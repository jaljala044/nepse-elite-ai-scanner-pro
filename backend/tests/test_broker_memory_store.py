import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app.broker_memory_store import (
    broker_memory_status,
    get_latest_broker_memory,
    persist_broker_memory,
)


class BrokerMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "broker-memory.duckdb"
        os.environ["NEPSE_API_DATABASE"] = str(self.db)
        self.sessions = [(date(2026, 1, 1) + timedelta(days=i)).isoformat()
                         for i in range(5)]
        self.rows = []
        for day in self.sessions:
            self.rows.extend([
                {
                    "trade_date": day, "symbol": "NABIL", "side": "buy",
                    "amount": "100", "quantity": "2",
                    "identity_status": "verified", "broker_entity_id": "BROKER-A",
                    "source_broker_code": "11", "source_id": "floorsheet-source",
                    "source_payload_sha256": "a" * 64, "source_row_number": 2,
                    "evidence_id": "evidence-buy-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                },
                {
                    "trade_date": day, "symbol": "NABIL", "side": "sell",
                    "amount": "100", "quantity": "2",
                    "identity_status": "verified", "broker_entity_id": "BROKER-B",
                    "source_broker_code": "22", "source_id": "floorsheet-source",
                    "source_payload_sha256": "b" * 64, "source_row_number": 3,
                    "evidence_id": "evidence-sell-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                },
            ])

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def persist(self, rows=None, sessions=None, decision_time=None):
        return persist_broker_memory(
            self.rows if rows is None else rows,
            session_dates=self.sessions if sessions is None else sessions,
            decision_time=decision_time or self.sessions[-1] + "T16:00:00+05:45",
            minimum_amount_coverage=0.8,
        )

    def test_persists_immutable_profile_and_exposes_horizons(self):
        result = self.persist()
        self.assertEqual(result["status"], "stored")
        self.assertEqual(result["features"]["security_features"]["NABIL"]["1D"]["status"], "observed")
        self.assertIn("1Y", result["features"]["security_features"]["NABIL"])
        latest = get_latest_broker_memory(symbol="NABIL")
        self.assertEqual(latest["selected_symbol"], "NABIL")
        self.assertEqual(latest["features"]["security_features"]["NABIL"]["1W"]["observed_sessions"], 5)
        self.assertEqual(broker_memory_status()["snapshot_count"], 1)

    def test_exact_replay_is_idempotent(self):
        first = self.persist()
        second = self.persist()
        self.assertEqual(first["status"], "stored")
        self.assertEqual(second["status"], "already_stored")
        self.assertEqual(broker_memory_status()["observation_count"], 10)
        self.assertEqual(broker_memory_status()["snapshot_count"], 1)

    def test_broker_filter_returns_observed_execution_channel_profile(self):
        self.persist()
        profile = get_latest_broker_memory(broker_entity_id="BROKER-A")
        self.assertEqual(profile["selected_broker_entity_id"], "BROKER-A")
        self.assertTrue(profile["broker_matches"])
        self.assertEqual(get_latest_broker_memory(broker_entity_id="NOT-FOUND"), None)

    def test_rejects_unverified_or_incomplete_floorsheet(self):
        bad = [dict(row) for row in self.rows]
        bad[0]["floorsheet_coverage_status"] = "partial"
        with self.assertRaisesRegex(ValueError, "coverage is not verified complete"):
            self.persist(rows=bad)

    def test_rejects_unverified_session_and_unknown_date(self):
        bad = [dict(row) for row in self.rows]
        bad[0]["session_calendar_status"] = "candidate_unverified"
        with self.assertRaisesRegex(ValueError, "not confirmed open"):
            self.persist(rows=bad)
        bad = [dict(row) for row in self.rows]
        bad[0]["trade_date"] = "2025-12-31"
        with self.assertRaisesRegex(ValueError, "not in the supplied verified session calendar"):
            self.persist(rows=bad)

    def test_rejects_future_available_at_and_missing_lineage(self):
        bad = [dict(row) for row in self.rows]
        bad[0]["available_at"] = "2026-01-05T17:00:00+05:45"
        with self.assertRaisesRegex(ValueError, "not available at the decision time"):
            self.persist(rows=bad)
        bad = [dict(row) for row in self.rows]
        del bad[0]["source_payload_sha256"]
        with self.assertRaisesRegex(ValueError, "missing required evidence fields"):
            self.persist(rows=bad)

    def test_rejects_duplicate_source_lineage(self):
        bad = [dict(row) for row in self.rows]
        bad[1]["source_row_number"] = bad[0]["source_row_number"]
        bad[1]["source_payload_sha256"] = bad[0]["source_payload_sha256"]
        bad[1]["evidence_id"] = bad[0]["evidence_id"]
        bad[1]["side"] = bad[0]["side"]
        bad[1]["broker_entity_id"] = bad[0]["broker_entity_id"]
        bad[1]["source_broker_code"] = bad[0]["source_broker_code"]
        with self.assertRaisesRegex(ValueError, "duplicate source lineage row"):
            self.persist(rows=bad)

    def test_no_profile_returns_none_until_evidence_is_stored(self):
        self.assertIsNone(get_latest_broker_memory())
        status = broker_memory_status()
        self.assertEqual(status["status"], "insufficient_evidence")
        self.assertFalse(status["live_ingestion_connected"])
        self.assertIsNone(status["latest_as_of_trade_date"])


if __name__ == "__main__":
    unittest.main()
