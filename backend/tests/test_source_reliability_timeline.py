import unittest

from app.source_reliability_timeline import (
    CANDIDATE_SOURCES, build_source_event_manifest, replay_source_reliability,
)

CAPTURED = "2026-11-28T10:00:00Z"
RECEIVED = "2026-11-28T10:05:00Z"


def event(event_id, event_type, day="2026-11-27", **extra):
    return {
        "event_id": event_id, "source_id": "sharesansar", "event_type": event_type,
        "effective_date": day, "captured_at": "2026-11-28T10:01:00Z",
        "available_at": "2026-11-28T10:02:00Z", **extra,
    }


class SourceReliabilityTimelineTests(unittest.TestCase):
    def test_candidate_catalog_keeps_user_requested_publishers_unapproved(self):
        ids = {row["source_id"] for row in CANDIDATE_SOURCES}
        self.assertTrue({"sharesansar", "chukul", "sharehub_nepal", "punji"} <= ids)
        self.assertTrue(all(row["status"] == "candidate_unreviewed" for row in CANDIDATE_SOURCES))

    def test_manifest_hash_is_deterministic_and_append_only(self):
        row = event("e1", "source_registered")
        a = build_source_event_manifest([row], batch_id="b1", captured_at=CAPTURED, received_at=RECEIVED)
        b = build_source_event_manifest([row], batch_id="b1", captured_at=CAPTURED, received_at=RECEIVED)
        self.assertEqual(a["payload_sha256"], b["payload_sha256"])
        self.assertEqual(a["immutability"], "append_only_input_manifest")
        self.assertFalse(a["production_admission_allowed"])

    def test_duplicate_event_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "event_1_id_missing_or_duplicate"):
            build_source_event_manifest(
                [event("e1", "source_registered"), event("e1", "source_suspended")],
                batch_id="b", captured_at=CAPTURED, received_at=RECEIVED)

    def test_capture_requires_https_url_and_digest(self):
        with self.assertRaisesRegex(ValueError, "successful_capture_requires_https"):
            build_source_event_manifest([event("e1", "capture_succeeded", source_url="http://bad.example", payload_sha256="a"*64)],
                batch_id="b", captured_at=CAPTURED, received_at=RECEIVED)

    def test_capture_requires_digest(self):
        with self.assertRaisesRegex(ValueError, "successful_capture_requires_sha256"):
            build_source_event_manifest([event("e1", "capture_succeeded", source_url="https://data.example/file")],
                batch_id="b", captured_at=CAPTURED, received_at=RECEIVED)

    def test_hostname_and_ownership_changes_require_both_sides(self):
        with self.assertRaisesRegex(ValueError, "hostname_change_requires_distinct_hosts"):
            build_source_event_manifest([event("e1", "hostname_changed", old_host="a.example", new_host="a.example")],
                batch_id="b", captured_at=CAPTURED, received_at=RECEIVED)
        with self.assertRaisesRegex(ValueError, "ownership_change_requires_both_groups"):
            build_source_event_manifest([event("e2", "ownership_group_changed", old_ownership_group_id="g1")],
                batch_id="b", captured_at=CAPTURED, received_at=RECEIVED)

    def test_future_events_excluded_at_historical_cutoff(self):
        rows = [event("e1", "source_registered"),
                event("e2", "source_suspended", day="2026-11-29")]
        report = replay_source_reliability(rows, decision_time="2026-11-28T12:00:00Z",
            verified_session_dates=["2026-11-27"], expected_source_ids=["sharesansar"])
        self.assertEqual(report["excluded_future_or_invalid_event_count"], 1)
        self.assertNotEqual(report["sources"]["sharesansar"]["status"], "suspended")

    def test_outage_recovery_and_suspension_transitions(self):
        rows = [event("e1", "outage_started"), event("e2", "outage_resolved", day="2026-11-28"),
                event("e3", "source_suspended", day="2026-11-28")]
        report = replay_source_reliability(rows, decision_time="2026-11-28T12:00:00Z")
        self.assertEqual(report["sources"]["sharesansar"]["status"], "suspended")

    def test_verified_session_coverage_not_weekday_inferred(self):
        rows = [event("e1", "capture_succeeded", source_url="https://archive.example/data",
                      payload_sha256="b"*64)]
        report = replay_source_reliability(rows, decision_time="2026-11-28T12:00:00Z",
            verified_session_dates=["2026-11-27", "2026-11-28"])
        source = report["sources"]["sharesansar"]
        self.assertEqual(source["session_coverage"], 0.5)
        self.assertEqual(source["missing_verified_sessions"], ["2026-11-28"])

    def test_hostname_ownership_and_correction_events_are_flagged(self):
        rows = [
            event("e1", "hostname_changed", old_host="old.example", new_host="new.example"),
            event("e2", "ownership_group_changed", old_ownership_group_id="g1", new_ownership_group_id="g2"),
            event("e3", "source_corrected", correction_ref="correction:123"),
        ]
        report = replay_source_reliability(rows, decision_time="2026-11-28T12:00:00Z")
        source = report["sources"]["sharesansar"]
        self.assertTrue(source["review_required"])
        self.assertEqual(len(source["hostname_changes"]), 1)
        self.assertEqual(len(source["ownership_group_changes"]), 1)
        self.assertEqual(len(source["corrections"]), 1)

    def test_absent_capture_does_not_infer_outage_without_calendar(self):
        report = replay_source_reliability([], decision_time="2026-11-28T12:00:00Z",
            expected_source_ids=["punji"])
        self.assertEqual(report["sources"]["punji"]["status"], "no_capture_evidence")
        self.assertIsNone(report["sources"]["punji"]["session_coverage"])
        self.assertEqual(report["status"], "calendar_unconfigured")


if __name__ == "__main__":
    unittest.main()
