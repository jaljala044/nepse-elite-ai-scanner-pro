import unittest
from datetime import datetime, timezone

from app.source_data_quality_gate import (
    assess_source_capture_completeness, build_data_quality_report, gate_market_record,
    reconcile_source_observations, resolve_record_corrections, validate_calendar_sessions,
    validate_capture_policy,
)

NOW = "2026-11-28T12:00:00Z"
HASH = "a" * 64


def calendar_row(day="2026-11-27", **extra):
    return {"date": day, "status": "confirmed_open", "review_status": "reviewed",
            "source_id": "calendar-review", "source_payload_sha256": HASH,
            "available_at": "2026-11-27T08:00:00Z", **extra}


def policy(**extra):
    return {"source_id": "sharesansar", "dataset": "ohlcv", "expected_sessions": ["2026-11-27"],
            "max_age_hours": 48, "review_status": "reviewed", "reviewer_id": "reviewer-1", **extra}


def capture(**extra):
    return {"source_id": "sharesansar", "dataset": "ohlcv", "session_date": "2026-11-27",
            "captured_at": "2026-11-27T10:00:00Z", "available_at": "2026-11-27T10:05:00Z",
            "payload_sha256": HASH, **extra}


class SourceDataQualityGateTests(unittest.TestCase):
    def test_calendar_requires_review_and_source_hash(self):
        result = validate_calendar_sessions([calendar_row()], decision_time=NOW)
        self.assertEqual(result["status"], "verified_input")
        bad = validate_calendar_sessions([calendar_row(review_status="pending")], decision_time=NOW)
        self.assertEqual(bad["accepted_session_count"], 0)

    def test_calendar_excludes_future_evidence_and_duplicate_dates(self):
        rows = [calendar_row(), calendar_row(available_at="2026-11-29T00:00:00Z")]
        result = validate_calendar_sessions(rows, decision_time=NOW)
        self.assertEqual(result["accepted_session_count"], 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_capture_policy_requires_explicit_reviewed_schedule(self):
        with self.assertRaisesRegex(ValueError, "reviewed_reviewer"):
            validate_capture_policy(policy(review_status="candidate"))
        self.assertEqual(validate_capture_policy(policy())["expected_sessions"], ["2026-11-27"])

    def test_missing_capture_is_not_assumed_outage_or_zero_activity(self):
        cal = validate_calendar_sessions([calendar_row()], decision_time=NOW)
        result = assess_source_capture_completeness([policy()], [], cal, decision_time=NOW)
        self.assertEqual(result["rows"][0]["status"], "missing_or_delayed")

    def test_outage_classification_requires_explicit_lifecycle_event(self):
        cal = validate_calendar_sessions([calendar_row()], decision_time=NOW)
        event = {"source_id": "sharesansar", "event_type": "outage_started",
                 "effective_date": "2026-11-27", "available_at": "2026-11-27T11:00:00Z"}
        result = assess_source_capture_completeness([policy()], [], cal, decision_time=NOW,
                                                    reliability_events=[event])
        self.assertEqual(result["rows"][0]["status"], "declared_outage")

    def test_capture_freshness_uses_policy_not_assumed_daily_schedule(self):
        cal = validate_calendar_sessions([calendar_row()], decision_time=NOW)
        result = assess_source_capture_completeness([policy()], [capture()], cal, decision_time=NOW)
        self.assertEqual(result["rows"][0]["status"], "captured_fresh")

    def test_correction_history_selects_latest_linked_version_as_of_cutoff(self):
        records = [{"record_id": "r1", "available_at": "2026-11-27T10:00:00Z", "value": 10},
                   {"record_id": "r2", "available_at": "2026-11-28T10:00:00Z",
                    "supersedes_record_id": "r1", "value": 11}]
        result = resolve_record_corrections(records, decision_time=NOW)
        self.assertEqual(result["active_versions"][0]["record_id"], "r2")
        self.assertEqual(result["superseded_record_ids"], ["r1"])

    def test_future_correction_does_not_leak_into_historical_cutoff(self):
        records = [{"record_id": "r1", "available_at": "2026-11-27T10:00:00Z", "value": 10},
                   {"record_id": "r2", "available_at": "2026-11-29T10:00:00Z",
                    "supersedes_record_id": "r1", "value": 11}]
        result = resolve_record_corrections(records, decision_time=NOW)
        self.assertEqual(result["active_versions"][0]["record_id"], "r1")

    def test_correction_with_missing_predecessor_is_not_active(self):
        records = [{"record_id": "r2", "available_at": "2026-11-28T10:00:00Z",
                    "supersedes_record_id": "missing-r1", "value": 11}]
        result = resolve_record_corrections(records, decision_time=NOW)
        self.assertEqual(result["active_versions"], [])
        self.assertEqual(result["rejected"][0]["reason"],
                         "superseded_record_missing_at_cutoff")

    def test_descendant_of_orphan_correction_is_not_active(self):
        records = [{"record_id": "r2", "available_at": "2026-11-27T10:00:00Z",
                    "supersedes_record_id": "missing-r1", "value": 11},
                   {"record_id": "r3", "available_at": "2026-11-28T10:00:00Z",
                    "supersedes_record_id": "r2", "value": 12}]
        result = resolve_record_corrections(records, decision_time=NOW)
        self.assertEqual(result["active_versions"], [])

    def test_cross_source_conflict_is_retained_not_majority_promoted(self):
        rows = [{"dataset": "ohlcv", "symbol": "NABIL", "session_date": "2026-11-27",
                 "source_id": "a", "value": 500},
                {"dataset": "ohlcv", "symbol": "NABIL", "session_date": "2026-11-27",
                 "source_id": "b", "value": 501},
                {"dataset": "ohlcv", "symbol": "NABIL", "session_date": "2026-11-27",
                 "source_id": "c", "value": 501}]
        result = reconcile_source_observations(rows)
        self.assertEqual(result["conflict_count"], 1)
        self.assertIsNone(result["results"][0]["canonical_value"])

    def test_quality_and_record_gate_fail_closed_for_ohlcv_and_floorsheet(self):
        cal = validate_calendar_sessions([], decision_time=NOW)
        completeness = {"status": "incomplete", "counts": {}}
        reconciliation = {"results": [], "conflict_count": 0}
        report = build_data_quality_report(calendar=cal, completeness=completeness,
                                           reconciliation=reconciliation)
        for dataset in ("ohlcv", "floorsheet"):
            result = gate_market_record({"source_id": "sharesansar",
                "source_payload_sha256": HASH}, dataset=dataset, quality_report=report)
            self.assertFalse(result["eligible_for_research_review"])
            self.assertFalse(result["production_admission_allowed"])


if __name__ == "__main__":
    unittest.main()
