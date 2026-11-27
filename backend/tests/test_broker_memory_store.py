import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app.broker_memory_store import (
    broker_memory_status,
    get_broker_memory_lineage,
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
                    "source_payload_sha256": ("a" * 62) + day[-2:], "source_row_number": 2,
                    "evidence_id": "evidence-buy-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "source_rights_status": "research_only",
                    "rights_evidence_id": "rights-review-floorsheet",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                },
                {
                    "trade_date": day, "symbol": "NABIL", "side": "sell",
                    "amount": "100", "quantity": "2",
                    "identity_status": "verified", "broker_entity_id": "BROKER-B",
                    "source_broker_code": "22", "source_id": "floorsheet-source",
                    "source_payload_sha256": ("a" * 62) + day[-2:], "source_row_number": 2,
                    "evidence_id": "evidence-sell-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "source_rights_status": "research_only",
                    "rights_evidence_id": "rights-review-floorsheet",
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
        yearly = result["features"]["security_features"]["NABIL"]["1Y"]
        self.assertEqual(yearly["expected_covered_sessions"], 5)
        self.assertFalse(yearly["window_complete"])
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

    def test_changed_content_for_existing_source_lineage_is_rejected(self):
        self.persist()
        changed = dict(self.rows[0], amount="101")
        with self.assertRaisesRegex(ValueError, "immutable-record conflict for source lineage"):
            self.persist(rows=[changed])
        self.assertEqual(broker_memory_status()["observation_count"], 10)

    def test_memory_rebuilds_from_prior_sessions_not_only_latest_batch(self):
        first_rows = [row for row in self.rows if row["trade_date"] in self.sessions[:3]]
        later_rows = [row for row in self.rows if row["trade_date"] in self.sessions[3:]]
        first = self.persist(rows=first_rows, decision_time=self.sessions[2] + "T16:00:00+05:45")
        late_arriving = dict(
            self.rows[2], source_id="late-correction-source",
            source_payload_sha256="c" * 62 + self.sessions[1][-2:],
            source_row_number=99, evidence_id="late-arriving-prior-session",
            available_at=self.sessions[3] + "T15:30:00+05:45",
        )
        second = self.persist(
            rows=later_rows + [late_arriving],
            decision_time=self.sessions[4] + "T16:00:00+05:45",
        )
        self.assertEqual(first["observation_count"], 6)
        first_week = first["features"]["security_features"]["NABIL"]["1W"]
        self.assertEqual(first_week["expected_covered_sessions"], 3)
        self.assertFalse(first_week["window_complete"])
        self.assertEqual(second["observation_count"], 11)
        self.assertEqual(broker_memory_status()["observation_count"], 11)
        latest = get_latest_broker_memory(symbol="NABIL")
        self.assertEqual(latest["features"]["security_features"]["NABIL"]["1W"]["observed_sessions"], 5)
        old_lineage = get_broker_memory_lineage(symbol="NABIL", as_of=self.sessions[2])
        self.assertEqual(old_lineage["total_observations"], 6)
        latest_lineage = get_broker_memory_lineage(symbol="NABIL")
        self.assertEqual(latest_lineage["total_observations"], 11)
        self.assertTrue(any(item["evidence_id"] == "late-arriving-prior-session"
                            for item in latest_lineage["observations"]))

    def test_daily_channel_profile_uses_exact_prior_20_session_baseline(self):
        sessions = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(21)]
        rows = []
        for day in sessions:
            suffix = day[-2:]
            rows.extend([
                {
                    "trade_date": day, "symbol": "NABIL", "side": "buy",
                    "amount": "100", "quantity": "1", "identity_status": "unmapped",
                    "broker_entity_id": None, "source_broker_code": "11",
                    "source_id": "floorsheet-source", "source_payload_sha256": "a" * 62 + suffix,
                    "source_row_number": 2, "evidence_id": "buy-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "source_rights_status": "research_only",
                    "rights_evidence_id": "rights-review-floorsheet",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                },
                {
                    "trade_date": day, "symbol": "NABIL", "side": "sell",
                    "amount": "100", "quantity": "1", "identity_status": "unmapped",
                    "broker_entity_id": None, "source_broker_code": "22",
                    "source_id": "floorsheet-source", "source_payload_sha256": "a" * 62 + suffix,
                    "source_row_number": 3, "evidence_id": "sell-" + day,
                    "available_at": day + "T15:00:00+05:45",
                    "source_validation_status": "verified",
                    "source_rights_status": "research_only",
                    "rights_evidence_id": "rights-review-floorsheet",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                },
            ])
        context = {
            "status": "verified",
            "symbol": "NABIL",
            "as_of_session": sessions[-1],
            "available_at": sessions[-1] + "T15:00:00+05:45",
            "source_id": "verified-nepse-context",
            "source_payload_sha256": "c" * 64,
            "price_extension_status": "not_extended",
            "component_statuses": {
                "price": "verified", "nepse_index": "verified",
                "sector_index": "verified", "market_breadth": "verified",
                "turnover_liquidity": "verified", "circuit_context": "verified",
                "corporate_actions": "verified",
            },
        }
        persist_broker_memory(
            rows, session_dates=sessions,
            decision_time=sessions[-1] + "T16:00:00+05:45",
            market_context_by_symbol={"NABIL": context},
            minimum_daily_flow_multiple=0.5,
        )
        profile = get_latest_broker_memory(symbol="NABIL", broker_code="11")
        daily = next(item for item in profile["execution_channel_matches"] if item["horizon"] == "1D")
        self.assertEqual(daily["prior_20_session_count"], 20)
        self.assertEqual(daily["latest_buy_vs_prior_20_avg_ratio"], 1.0)
        self.assertEqual(len(daily["daily_activity"]), 21)
        self.assertEqual(daily["daily_activity"][-1]["session_date"], sessions[-1])
        self.assertEqual(profile["observation_count"], 42)
        self.assertEqual(len(profile["input_lineage_sha256"]), 64)
        self.assertEqual(
            profile["selected_early_patterns"][0]["status"],
            "EARLY_ENTRY_CANDIDATE",
            profile["selected_early_patterns"][0],
        )

    def test_source_lineage_drilldown_is_paginated_and_filterable_by_code(self):
        self.persist()
        page = get_broker_memory_lineage(symbol="NABIL", broker_code="11", limit=3)
        self.assertEqual(page["total_observations"], 5)
        self.assertEqual(len(page["observations"]), 3)
        self.assertEqual(page["next_offset"], 3)
        self.assertTrue(all(item["side"] == "buy" for item in page["observations"]))
        next_page = get_broker_memory_lineage(symbol="NABIL", broker_code="11", limit=3, offset=3)
        self.assertEqual(len(next_page["observations"]), 2)
        self.assertIsNone(next_page["next_offset"])

    def test_broker_filter_returns_observed_execution_channel_profile(self):
        self.persist()
        profile = get_latest_broker_memory(broker_entity_id="BROKER-A")
        self.assertEqual(profile["selected_broker_entity_id"], "BROKER-A")
        self.assertTrue(profile["broker_matches"])
        self.assertEqual(get_latest_broker_memory(broker_entity_id="NOT-FOUND"), None)
        channel = get_latest_broker_memory(broker_code="11")
        self.assertEqual(channel["selected_execution_channel_code"], "11")
        self.assertTrue(channel["execution_channel_matches"])
        self.assertEqual(channel["execution_channel_matches"][0]["identity_status"], "execution_channel_only")

    def test_unmapped_execution_codes_are_remembered_without_entity_identity(self):
        rows = [dict(row, identity_status="unmapped", broker_entity_id=None)
                for row in self.rows]
        result = self.persist(rows=rows)
        self.assertEqual(result["features"]["status"], "insufficient_evidence")
        channel = get_latest_broker_memory(broker_code="11")
        self.assertIsNotNone(channel)
        self.assertEqual(channel["execution_channel_matches"][0]["identity_status"], "execution_channel_only")
        self.assertEqual(channel["execution_channel_matches"][0]["flow_class"], "net_buyer")

    def test_rejects_unverified_or_incomplete_floorsheet(self):
        bad = [dict(row) for row in self.rows]
        bad[0]["floorsheet_coverage_status"] = "partial"
        with self.assertRaisesRegex(ValueError, "coverage is not verified complete"):
            self.persist(rows=bad)

    def test_rejects_unknown_or_prohibited_source_rights(self):
        bad = [dict(row) for row in self.rows]
        bad[0]["source_rights_status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "source rights are not cleared"):
            self.persist(rows=bad)
        bad = [dict(row) for row in self.rows]
        bad[0]["source_rights_status"] = "redistribution_permitted"
        bad[0]["rights_evidence_id"] = None
        with self.assertRaisesRegex(ValueError, "redistribution permission requires rights evidence"):
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
        with self.assertRaisesRegex(ValueError, "duplicate party observation source lineage"):
            self.persist(rows=bad)

    def test_no_profile_returns_none_until_evidence_is_stored(self):
        self.assertIsNone(get_latest_broker_memory())
        status = broker_memory_status()
        self.assertEqual(status["status"], "insufficient_evidence")
        self.assertFalse(status["live_ingestion_connected"])
        self.assertIsNone(status["latest_as_of_trade_date"])


if __name__ == "__main__":
    unittest.main()
