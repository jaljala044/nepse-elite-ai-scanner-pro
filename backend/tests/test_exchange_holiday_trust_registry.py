from __future__ import annotations

import unittest

from app.source_trust_registry import (
    REQUIRED_CHECKS,
    RECORD_TYPES,
    SourcePolicy,
    build_source_registry,
    resolve_source_policy,
    validate_promotion_evidence,
)


class ExchangeHolidayTrustRegistryTests(unittest.TestCase):
    def test_exchange_holiday_is_a_supported_record_type(self):
        self.assertIn("exchange_holiday", RECORD_TYPES)
        self.assertIn("exchange_holiday", REQUIRED_CHECKS)

    def test_holiday_promotion_requires_all_safety_checks_and_evidence(self):
        required = {
            "payload_integrity",
            "source_identity",
            "schema_mapping",
            "date_validity",
            "duplicate_detection",
            "instrument_scope",
            "point_in_time",
            "official_notice",
        }
        self.assertEqual(REQUIRED_CHECKS["exchange_holiday"], required)

        record = {
            "record_type": "exchange_holiday",
            "source_payload_sha256": "a" * 64,
            "available_at": "2026-11-25T13:13:17Z",
        }
        reasons = validate_promotion_evidence(
            record,
            raw_payload_sha256="a" * 64,
            validation={
                "payload_sha256": "a" * 64,
                "validated_at": "2026-11-25T13:14:00Z",
                "reviewer": "reviewer-a",
                "validation_id": "holiday-validation-001",
                "checks": {},
                "evidence_refs": {},
            },
            decision_time="2026-11-25T14:00:00Z",
        )
        for check in required:
            self.assertIn(f"required_check_not_passed:{check}", reasons)
            self.assertIn(f"independent_evidence_reference_missing:{check}", reasons)

    def test_review_required_holiday_source_cannot_be_canonical_promoted(self):
        policy = SourcePolicy(
            source_id="NEPSE_OFFICIAL_HOLIDAY_API_2026",
            publisher_name="Nepal Stock Exchange",
            trust_tier="exchange_primary",
            allowed_record_types=("exchange_holiday",),
            canonical_record_types=(),
            status="review_required",
            effective_from="2026-01-01",
            effective_to=None,
            reviewer="pending-human-review",
            reviewed_at="2026-11-25T14:00:00Z",
            evidence_refs=("data/evidence/acquired/calendar-evidence-manifest-2026.json",),
            rights_state="review_required",
            redistribution_allowed=False,
        )
        registry = build_source_registry([policy])
        resolved, reasons = resolve_source_policy(
            registry,
            source_id="NEPSE_OFFICIAL_HOLIDAY_API_2026",
            record_type="exchange_holiday",
            session_date="2026-11-25",
            decision_time="2026-11-26T00:00:00Z",
        )
        self.assertIsNotNone(resolved)
        self.assertIn("source_policy_not_active", reasons)
        self.assertIn("source_not_approved_for_canonical_record_type", reasons)
        self.assertEqual(policy.rights_state, "review_required")
        self.assertFalse(policy.redistribution_allowed)

    def test_holiday_type_does_not_imply_approval_of_other_record_types(self):
        policy = SourcePolicy(
            source_id="NEPSE_OFFICIAL_HOLIDAY_API_2026",
            publisher_name="Nepal Stock Exchange",
            trust_tier="exchange_primary",
            allowed_record_types=("exchange_holiday",),
            canonical_record_types=(),
            status="review_required",
            effective_from="2026-01-01",
            effective_to=None,
            reviewer="pending-human-review",
            reviewed_at="2026-11-25T14:00:00Z",
            evidence_refs=("holiday-capture-manifest",),
            rights_state="review_required",
            redistribution_allowed=False,
        )
        registry = build_source_registry([policy])
        _, reasons = resolve_source_policy(
            registry,
            source_id="NEPSE_OFFICIAL_HOLIDAY_API_2026",
            record_type="ohlcv",
            session_date="2026-11-25",
            decision_time="2026-11-26T00:00:00Z",
        )
        self.assertIn("record_type_not_allowed_for_source", reasons)
        self.assertIn("source_not_approved_for_canonical_record_type", reasons)


if __name__ == "__main__":
    unittest.main()
