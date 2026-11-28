import unittest

from app.historical_pilot_identity_coverage import (
    build_bounded_ohlcv_coverage_pilot,
    validate_corporate_action_evidence,
    validate_effective_dated_security_identity,
)


class IdentityCoveragePilotTests(unittest.TestCase):
    def setUp(self):
        self.cutoff = "2026-11-28T12:00:00+05:45"

    def identity(self, **overrides):
        row = {
            "symbol": "NABIL", "security_id": "100", "instrument_type": "equity",
            "effective_from": "2020-01-01", "effective_to": None,
            "source_id": "nepse", "publisher_id": "nepse-publisher",
            "authority": "exchange_primary", "available_at": "2020-01-01T00:00:00+05:45",
            "observed_at": "2026-11-20T00:00:00+05:45", "evidence_sha256": "a" * 64,
        }
        row.update(overrides)
        return row

    def action_report(self):
        records = [
            {"event_id": "NABIL-BONUS-2024", "symbol": "NABIL", "action_type": "bonus",
             "effective_date": "2024-06-01", "available_at": "2024-05-01T00:00:00+05:45",
             "source_id": "nepse", "publisher_id": "exchange", "authority": "exchange_primary",
             "evidence_sha256": "b" * 64, "adjustment_factor": "0.95"},
            {"event_id": "NABIL-BONUS-2024", "symbol": "NABIL", "action_type": "bonus",
             "effective_date": "2024-06-01", "available_at": "2024-05-02T00:00:00+05:45",
             "source_id": "sharesansar", "publisher_id": "ss-publisher", "authority": "third_party",
             "evidence_sha256": "c" * 64, "adjustment_factor": "0.95"},
        ]
        return validate_corporate_action_evidence(action_records=records, decision_cutoff=self.cutoff)

    def test_valid_identity_and_corporate_action_evidence(self):
        identity = validate_effective_dated_security_identity(
            identity_records=[self.identity()], decision_cutoff=self.cutoff)
        action = self.action_report()
        self.assertEqual(identity["status"], "IDENTITY_EVIDENCE_VALIDATED")
        self.assertEqual(action["status"], "CORPORATE_ACTION_EVIDENCE_VALIDATED")

    def test_overlapping_security_id_symbol_conflict_blocks_identity(self):
        identity = validate_effective_dated_security_identity(
            identity_records=[self.identity(), self.identity(symbol="NABILX", evidence_sha256="d" * 64)],
            decision_cutoff=self.cutoff)
        self.assertEqual(identity["status"], "IDENTITY_EVIDENCE_BLOCKED")
        self.assertTrue(any(x["reason"] == "security_id_maps_to_multiple_symbols_in_overlapping_interval"
                            for x in identity["errors"]))

    def test_future_identity_evidence_blocks(self):
        identity = validate_effective_dated_security_identity(
            identity_records=[self.identity(available_at="2026-12-01T00:00:00+05:45")],
            decision_cutoff=self.cutoff)
        self.assertEqual(identity["status"], "IDENTITY_EVIDENCE_BLOCKED")

    def test_corporate_action_needs_two_publishers_and_primary(self):
        rows = self.action_report()["accepted_events"]
        action = validate_corporate_action_evidence(
            action_records=rows[:1], decision_cutoff=self.cutoff)
        self.assertEqual(action["status"], "CORPORATE_ACTION_EVIDENCE_BLOCKED")

    def test_conflicting_corporate_action_factors_block(self):
        rows = [
            {"event_id": "EV1", "symbol": "AAA", "action_type": "split", "effective_date": "2024-01-01",
             "available_at": "2023-12-01T00:00:00+05:45", "source_id": "nepse", "publisher_id": "p1",
             "authority": "exchange_primary", "evidence_sha256": "e" * 64, "adjustment_factor": "0.5"},
            {"event_id": "EV1", "symbol": "AAA", "action_type": "split", "effective_date": "2024-01-01",
             "available_at": "2023-12-02T00:00:00+05:45", "source_id": "other", "publisher_id": "p2",
             "authority": "third_party", "evidence_sha256": "f" * 64, "adjustment_factor": "0.4"},
        ]
        action = validate_corporate_action_evidence(action_records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(action["status"], "CORPORATE_ACTION_EVIDENCE_BLOCKED")
        self.assertTrue(any(x["reason"] == "action_sources_disagree_on_event_facts" for x in action["errors"]))

    def test_coverage_grid_reports_source_specific_missing_rows_and_conflicts(self):
        identity = validate_effective_dated_security_identity(
            identity_records=[self.identity()], decision_cutoff=self.cutoff)
        action = self.action_report()
        rows = [
            {"session_date": "2026-11-20", "symbol": "NABIL", "source_id": "source_a",
             "close": "100", "raw_payload_sha256": "1" * 64},
            {"session_date": "2026-11-20", "symbol": "NABIL", "source_id": "source_b",
             "close": "101", "raw_payload_sha256": "2" * 64},
        ]
        report = build_bounded_ohlcv_coverage_pilot(
            records=rows, expected_sessions=["2026-11-20", "2026-11-21"],
            identity_report=identity, corporate_action_report=action,
            source_requirements={"official_calendar_verified": True, "session_calendar_sha256": "3" * 64,
                                 "universe_manifest_verified": True, "universe_manifest_sha256": "4" * 64},
        )
        self.assertEqual(report["status"], "COVERAGE_PILOT_BLOCKED")
        self.assertEqual(report["summary"]["cross_source_close_conflict_count"], 1)
        self.assertEqual(report["summary"]["source_reports"]["source_a"]["missing_keys"][0]["session_date"],
                         "2026-11-21")
        self.assertFalse(report["scanner_replay_allowed"])

    def test_coverage_never_admits_without_action_and_calendar_evidence(self):
        report = build_bounded_ohlcv_coverage_pilot(
            records=[], expected_sessions=["2026-11-20"],
            identity_report={}, corporate_action_report={}, source_requirements={},
        )
        self.assertEqual(report["status"], "COVERAGE_PILOT_BLOCKED")
        self.assertFalse(report["canonical_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
