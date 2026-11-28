import unittest
from datetime import date, timedelta

from app.historical_eligibility import build_lifecycle_eligibility_manifest


HASH = "a" * 64
CUTOFF = "2026-11-28T12:00:00+04:00"


def fixture(days=120, *, status="traded", basis="raw_unadjusted"):
    sessions = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(days)]
    records = []
    for day in sessions:
        row = {
            "session_date": day,
            "observation_status": status,
            "evidence_id": "E-" + day,
            "source_sha256": HASH,
            "available_at": "2026-11-27T12:00:00+04:00",
        }
        if status == "traded":
            row["ohlcv"] = {
                "open": "100", "high": "105", "low": "99",
                "close": "103", "volume": "1000",
            }
            row["adjustment_basis"] = basis
            row["rights_status"] = "approved"
        else:
            row["ohlcv"] = None
        records.append(row)
    return sessions, records


def build(sessions, records, **kwargs):
    return build_lifecycle_eligibility_manifest(
        records, symbol="NABIL", verified_sessions=sessions,
        lifecycle={"listing_date": sessions[0], "suspensions": []},
        required_warmup_sessions=100, available_as_of=CUTOFF, **kwargs
    )


class LifecycleEligibilityTests(unittest.TestCase):
    def test_complete_120_session_segment_is_review_eligible_not_approved(self):
        sessions, records = fixture()
        report = build(sessions, records)
        self.assertEqual(report["verified_session_count"], 120)
        self.assertEqual(report["traded_session_count"], 120)
        self.assertEqual(report["review_status"], "ELIGIBLE_FOR_INDEPENDENT_REVIEW")
        self.assertFalse(report["approved_backtest"])
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_missing_session_blocks_segment(self):
        sessions, records = fixture()
        records.pop(40)
        report = build(sessions, records)
        self.assertIn("missing", {row["classification"] for row in report["rows"]})
        self.assertIn("expected_session_has_no_classified_observation",
                      {item["reason"] for item in report["blockers"]})

    def test_explicit_no_trade_is_classified_without_imputation(self):
        sessions, records = fixture()
        records[5]["observation_status"] = "no_trade"
        records[5]["ohlcv"] = None
        records[5].pop("adjustment_basis")
        records[5].pop("rights_status")
        report = build(sessions, records)
        self.assertEqual(report["rows"][5]["classification"], "no_trade")
        self.assertEqual(report["explicit_no_trade_session_count"], 1)
        self.assertEqual(report["traded_session_count"], 119)

    def test_suspension_is_distinguished_from_missing(self):
        sessions, records = fixture()
        records.pop(20)
        lifecycle = {"listing_date": sessions[0],
                     "suspensions": [{"start": sessions[20], "end": sessions[20]}]}
        report = build_lifecycle_eligibility_manifest(
            records, symbol="NABIL", verified_sessions=sessions,
            lifecycle=lifecycle, required_warmup_sessions=100,
            available_as_of=CUTOFF)
        self.assertEqual(report["rows"][20]["classification"], "suspended")
        self.assertNotIn("expected_session_has_no_classified_observation",
                         {item["reason"] for item in report["blockers"]})

    def test_merger_boundary_stops_predecessor_segment(self):
        sessions, records = fixture()
        lifecycle = {"listing_date": sessions[0], "merger_effective_date": sessions[60]}
        report = build_lifecycle_eligibility_manifest(
            records, symbol="PFL", verified_sessions=sessions,
            lifecycle=lifecycle, required_warmup_sessions=40,
            available_as_of=CUTOFF)
        self.assertEqual(report["rows"][60]["classification"], "lifecycle_conflict")
        self.assertTrue(report["history_spliced"] is False)

    def test_mixed_adjustment_basis_blocks_segment(self):
        sessions, records = fixture()
        records[80]["adjustment_basis"] = "split_adjusted"
        report = build(sessions, records)
        self.assertIn("mixed_adjustment_basis_within_segment",
                      {item["reason"] for item in report["blockers"]})

    def test_duplicate_session_rows_block_segment(self):
        sessions, records = fixture()
        records.append(dict(records[10]))
        report = build(sessions, records)
        self.assertEqual(report["rows"][10]["classification"], "duplicate")

    def test_stale_available_at_after_cutoff_is_rejected(self):
        sessions, records = fixture()
        records[10]["available_at"] = "2026-11-29T00:00:00+04:00"
        report = build(sessions, records)
        self.assertIn("lookahead_available_after_cutoff",
                      {item["reason"] for item in report["blockers"]})

    def test_insufficient_warmup_blocks_segment(self):
        sessions, records = fixture(days=120)
        report = build(sessions, records, required_warmup_sessions=121)
        self.assertIn("insufficient_classified_causal_warmup",
                      {item["reason"] for item in report["blockers"]})

    def test_short_history_does_not_meet_120_session_gate(self):
        sessions, records = fixture(days=119)
        report = build(sessions, records)
        self.assertIn("insufficient_verified_session_count",
                      {item["reason"] for item in report["blockers"]})

    def test_invalid_ohlcv_and_missing_rights_block_segment(self):
        sessions, records = fixture()
        records[3]["ohlcv"]["high"] = "90"
        records[4]["rights_status"] = "unknown"
        report = build(sessions, records)
        reasons = {item["reason"] for item in report["blockers"]}
        self.assertIn("invalid_ohlc_geometry", reasons)
        self.assertIn("source_rights_not_approved", reasons)

    def test_out_of_calendar_row_is_not_silently_ignored(self):
        sessions, records = fixture()
        extra = dict(records[0])
        extra["session_date"] = "2025-12-31"
        records.append(extra)
        report = build(sessions, records)
        self.assertIn("rows_outside_verified_session_calendar",
                      {item["reason"] for item in report["blockers"]})

    def test_unverified_session_order_is_rejected(self):
        sessions, records = fixture()
        with self.assertRaisesRegex(ValueError, "unique_and_chronological"):
            build(list(reversed(sessions)), records)


if __name__ == "__main__":
    unittest.main()
