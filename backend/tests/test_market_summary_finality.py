import unittest

from app.market_summary_finality import (
    sign_finality_attestation,
    validate_market_summary_finality,
)

KEY = b"test-only-reviewer-key-not-for-production"
DIGEST = "a" * 64
CAL_DIGEST = "b" * 64
CUTOFF = "2026-11-27T12:00:00+05:45"


def fixtures():
    dates = ["2026-11-25", "2026-11-26"]
    capture = {
        "status": "review_only", "promotion_allowed": False,
        "source_payload_sha256": DIGEST,
        "retrieved_at": "2026-11-26T16:00:20+00:00",
        "rows": [{"session_date": day, "source_payload_sha256": DIGEST} for day in dates],
    }
    calendar = {
        "status": "verified", "calendar_id": "nepse-calendar-v1",
        "calendar_sha256": CAL_DIGEST, "source_id": "official-calendar-review",
        "available_at": "2026-11-26T15:00:00Z", "session_dates": dates,
    }
    attestation = {
        "reviewer": "independent-reviewer",
        "validation_id": "FIN-2026-11-26-001",
        "decision": "final", "reviewed_at": "2026-11-27T06:00:00Z",
        "capture_payload_sha256": DIGEST, "calendar_sha256": CAL_DIGEST,
        "calendar_id": "nepse-calendar-v1",
        "evidence_refs": ["official-session-notice:2026-11-26", "review-record:001"],
    }
    attestation["signature"] = sign_finality_attestation(attestation, KEY)
    return capture, calendar, attestation


class MarketSummaryFinalityTests(unittest.TestCase):
    def validate(self, capture=None, calendar=None, attestation=None):
        default_capture, default_calendar, default_attestation = fixtures()
        return validate_market_summary_finality(
            capture or default_capture,
            session_calendar=calendar or default_calendar,
            attestation=attestation or default_attestation,
            reviewer_keys={"independent-reviewer": KEY},
            decision_time=CUTOFF,
        )

    def test_signed_exact_calendar_attestation_passes(self):
        result = self.validate()
        self.assertEqual(result["status"], "attested_final")
        self.assertTrue(result["evidence_gate_passed"])
        self.assertTrue(result["promotion_allowed"])
        self.assertEqual(result["session_count"], 2)

    def test_missing_session_fails_closed(self):
        capture, calendar, attestation = fixtures()
        capture["rows"].append({"session_date": "2026-11-27", "source_payload_sha256": DIGEST})
        calendar["session_dates"].append("2026-11-26")
        calendar["session_dates"].append("2026-11-27")
        calendar["session_dates"] = sorted(set(calendar["session_dates"]))
        result = self.validate(capture, calendar, attestation)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["missing_sessions"], ["2026-11-26"])
        self.assertFalse(result["promotion_allowed"])

    def test_calendar_dates_outside_capture_range_are_not_missing_rows(self):
        capture, calendar, attestation = fixtures()
        calendar["session_dates"] = ["2026-11-24", "2026-11-25", "2026-11-26", "2026-11-27"]
        result = self.validate(capture, calendar, attestation)
        self.assertEqual(result["status"], "attested_final")
        self.assertEqual(result["session_count"], 2)
        self.assertTrue(result["promotion_allowed"])

    def test_unexpected_observed_date_fails_closed(self):
        capture, calendar, attestation = fixtures()
        capture["rows"].append({"session_date": "2026-11-27", "source_payload_sha256": DIGEST})
        result = self.validate(capture, calendar, attestation)
        self.assertEqual(result["unexpected_sessions"], ["2026-11-27"])
        self.assertFalse(result["promotion_allowed"])

    def test_short_reviewer_key_cannot_sign_or_verify(self):
        capture, calendar, attestation = fixtures()
        with self.assertRaisesRegex(ValueError, "at_least_32_bytes"):
            sign_finality_attestation(attestation, b"short")
        with self.assertRaisesRegex(ValueError, "trusted_reviewer_signature_required"):
            validate_market_summary_finality(
                capture, session_calendar=calendar, attestation=attestation,
                reviewer_keys={"independent-reviewer": b"short"},
                decision_time=CUTOFF,
            )

    def test_nonfinite_attestation_payload_is_not_signable(self):
        attestation = {"reviewer": "independent-reviewer", "confidence": float("nan")}
        with self.assertRaises(ValueError):
            sign_finality_attestation(attestation, KEY)

    def test_unsigned_attestation_rejected(self):
        capture, calendar, attestation = fixtures()
        attestation["signature"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "signature_invalid"):
            self.validate(capture, calendar, attestation)

    def test_wrong_capture_digest_rejected(self):
        capture, calendar, attestation = fixtures()
        attestation["capture_payload_sha256"] = "c" * 64
        attestation["signature"] = sign_finality_attestation(
            {k: v for k, v in attestation.items() if k != "signature"}, KEY)
        with self.assertRaisesRegex(ValueError, "capture_digest_mismatch"):
            self.validate(capture, calendar, attestation)

    def test_wrong_calendar_digest_rejected(self):
        capture, calendar, attestation = fixtures()
        attestation["calendar_sha256"] = "c" * 64
        attestation["signature"] = sign_finality_attestation(
            {k: v for k, v in attestation.items() if k != "signature"}, KEY)
        with self.assertRaisesRegex(ValueError, "calendar_digest_mismatch"):
            self.validate(capture, calendar, attestation)

    def test_future_review_rejected(self):
        capture, calendar, attestation = fixtures()
        attestation["reviewed_at"] = "2026-11-28T00:00:00Z"
        attestation["signature"] = sign_finality_attestation(
            {k: v for k, v in attestation.items() if k != "signature"}, KEY)
        with self.assertRaisesRegex(ValueError, "review_after_decision"):
            self.validate(capture, calendar, attestation)

    def test_unverified_calendar_rejected(self):
        capture, calendar, attestation = fixtures()
        calendar["status"] = "candidate"
        with self.assertRaisesRegex(ValueError, "verified_session_calendar_required"):
            self.validate(capture, calendar, attestation)

    def test_capture_rows_must_share_digest(self):
        capture, calendar, attestation = fixtures()
        capture["rows"][0]["source_payload_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "row_provenance_mismatch"):
            self.validate(capture, calendar, attestation)

    def test_duplicate_capture_date_rejected(self):
        capture, calendar, attestation = fixtures()
        capture["rows"].append(dict(capture["rows"][0]))
        with self.assertRaisesRegex(ValueError, "unique_ascending"):
            self.validate(capture, calendar, attestation)


if __name__ == "__main__":
    unittest.main()
