import unittest
from datetime import date

from app.temporal_registry import (
    SecurityMasterRecord, CorporateActionRecord,
    security_as_of, corporate_actions_as_of, validate_security_master_snapshot,
)


def security(security_id="S1", symbol="ABC", valid_from=date(2020, 1, 1),
             valid_to=None, evidence_id="e1", evidence_tier="primary_nepse_notice",
             stable_id_verified=True, effective_date_verified=True,
             instrument_type="equity", status="active"):
    return SecurityMasterRecord(
        security_id, symbol, instrument_type, status, valid_from, valid_to,
        evidence_id, evidence_tier, stable_id_verified, effective_date_verified,
    )


def action(action_id="A1", security_id="S1", action_type="bonus",
           ex_date=date(2026, 11, 20), announced_at="2026-11-18T09:00:00Z",
           available_at="2026-11-18T09:00:00Z", factor=1.1, evidence_id="e1",
           evidence_tier="primary_nepse_notice", verification_status="verified_primary",
           adjustment_factor_verified=True):
    return CorporateActionRecord(
        action_id, security_id, action_type, ex_date, announced_at, available_at,
        factor, evidence_id, evidence_tier, verification_status, adjustment_factor_verified,
    )


class TemporalRegistryTests(unittest.TestCase):
    def test_security_lifecycle_is_effective_dated(self):
        rows = [
            security(symbol="OLD", valid_from=date(2020, 1, 1), valid_to=date(2024, 12, 31), evidence_id="e1"),
            security(symbol="NEW", valid_from=date(2025, 1, 1), valid_to=None, evidence_id="e2"),
        ]
        self.assertEqual(security_as_of(rows, date(2024, 6, 1))["record"].symbol, "OLD")
        self.assertEqual(security_as_of(rows, date(2025, 6, 1))["record"].symbol, "NEW")

    def test_conflicting_overlapping_security_records_are_ambiguous(self):
        rows = [
            security(symbol="ABC", valid_from=date(2020, 1, 1), evidence_id="e1"),
            security(symbol="XYZ", valid_from=date(2022, 1, 1), evidence_id="e2"),
        ]
        self.assertEqual(security_as_of(rows, date(2023, 1, 1))["status"], "ambiguous")

    def test_invalid_security_date_range_rejected(self):
        with self.assertRaises(ValueError):
            security(valid_from=date(2025, 1, 2), valid_to=date(2025, 1, 1))

    def test_security_master_snapshot_reports_identity_admission_counts(self):
        rows = [
            security(security_id="S1", symbol="ABC", evidence_id="e1"),
            security(security_id="S2", symbol="FUND1", evidence_id="e2",
                     instrument_type="mutual_fund", evidence_tier="current_snapshot_only",
                     stable_id_verified=False, effective_date_verified=False),
            security(security_id="S3", symbol="OLD1", evidence_id="e3",
                     instrument_type="non_convertible_debenture", status="delisted",
                     valid_from=date(2018, 1, 1), valid_to=date(2020, 12, 31),
                     evidence_tier="secondary_notice", stable_id_verified=False,
                     effective_date_verified=False),
        ]
        result = validate_security_master_snapshot(rows)
        self.assertEqual(result["unique_security_ids"], 3)
        self.assertEqual(result["instrument_type_counts"]["equity"], 1)
        self.assertEqual(result["instrument_type_counts"]["mutual_fund"], 1)
        self.assertEqual(result["primary_verified_identity_count"], 1)
        self.assertEqual(result["unverified_identity_count"], 2)
        self.assertEqual(result["identity_admission_status"], "partial_or_unverified")

    def test_current_snapshot_only_identity_is_not_resolved(self):
        row = security(evidence_tier="current_snapshot_only",
                       stable_id_verified=False, effective_date_verified=False)
        result = security_as_of([row], date(2024, 1, 1))
        self.assertEqual(result["status"], "unverified_identity")
        self.assertIsNone(result["record"])
        self.assertFalse(result["stable_id_verified"])

    def test_secondary_first_trade_evidence_does_not_verify_historical_stable_id(self):
        row = security(evidence_tier="secondary_first_trade_archive_match",
                       stable_id_verified=False, effective_date_verified=False)
        result = security_as_of([row], date(2024, 1, 1))
        self.assertEqual(result["status"], "unverified_identity")
        self.assertEqual(result["evidence_tiers"], ["secondary_first_trade_archive_match"])

    def test_primary_notice_without_stable_id_does_not_resolve(self):
        row = security(evidence_tier="primary_nepse_notice",
                       stable_id_verified=False, effective_date_verified=True)
        self.assertEqual(security_as_of([row], date(2024, 1, 1))["status"], "unverified_identity")

    def test_primary_cdsc_identity_evidence_can_resolve(self):
        row = security(evidence_tier="primary_cdsc_record",
                       stable_id_verified=True, effective_date_verified=True)
        result = security_as_of([row], date(2024, 1, 1))
        self.assertEqual(result["status"], "resolved")
        self.assertTrue(result["stable_id_verified"])

    def test_primary_cdsc_corporate_action_factor_can_be_adjustment_eligible(self):
        row = action(evidence_tier="cdsc_notice",
                     verification_status="verified_primary",
                     adjustment_factor_verified=True)
        result = corporate_actions_as_of([row], "S1", "2026-11-22T12:00:00Z")
        self.assertEqual(result["adjustment_eligible_count"], 1)

    def test_unknown_instrument_type_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported instrument_type"):
            security(instrument_type="ticker_guess")

    def test_overlapping_conflicting_lifecycle_rows_fail(self):
        rows = [
            security(symbol="ABC", valid_from=date(2020, 1, 1), evidence_id="e1"),
            security(symbol="XYZ", valid_from=date(2022, 1, 1), evidence_id="e2"),
        ]
        with self.assertRaisesRegex(ValueError, "overlapping conflicting"):
            validate_security_master_snapshot(rows)

    def test_symbol_overlap_across_security_ids_fails(self):
        rows = [
            security(security_id="S1", symbol="ABC", evidence_id="e1"),
            security(security_id="S2", symbol="ABC", evidence_id="e2",
                     instrument_type="mutual_fund"),
        ]
        with self.assertRaisesRegex(ValueError, "overlaps across distinct"):
            validate_security_master_snapshot(rows)

    def test_noncanonical_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "uppercase"):
            security(symbol="abc")

    def test_late_known_corporate_action_is_excluded(self):
        actions = [
            action(action_id="A1"),
            action(action_id="A2", action_type="right", ex_date=date(2026, 11, 21),
                   announced_at="2026-11-24T09:00:00Z",
                   available_at="2026-11-24T09:00:00Z", factor=1.2, evidence_id="e2"),
        ]
        result = corporate_actions_as_of(actions, "S1", "2026-11-22T12:00:00Z")
        self.assertEqual([a.action_id for a in result["actions"]], ["A1"])
        self.assertEqual([a.action_id for a in result["adjustment_actions"]], ["A1"])
        self.assertEqual(result["late_action_count"], 1)
        self.assertTrue(result["point_in_time_eligible"])

    def test_secondary_action_is_context_only_not_adjustment_eligible(self):
        action_record = action(evidence_tier="secondary_notice",
                               verification_status="verified_secondary",
                               adjustment_factor_verified=False)
        result = corporate_actions_as_of([action_record], "S1", "2026-11-22T12:00:00Z")
        self.assertEqual(result["included_count"], 1)
        self.assertEqual(result["adjustment_eligible_count"], 0)
        self.assertEqual(result["actions"][0].evidence_tier, "secondary_notice")

    def test_unverified_known_action_is_excluded_and_blocks_complete_context(self):
        action_record = action(evidence_tier="unverified",
                               verification_status="unverified",
                               adjustment_factor_verified=False)
        result = corporate_actions_as_of([action_record], "S1", "2026-11-22T12:00:00Z")
        self.assertEqual(result["included_count"], 0)
        self.assertEqual(result["excluded_unverified_count"], 1)
        self.assertFalse(result["point_in_time_eligible"])

    def test_non_finite_corporate_action_factor_rejected(self):
        for factor in (float("nan"), float("inf"), 0.0, -1.0):
            with self.subTest(factor=factor), self.assertRaisesRegex(ValueError, "finite and positive"):
                action(factor=factor)

    def test_available_at_cannot_precede_announcement(self):
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            action(announced_at="2026-11-20T09:00:00Z",
                   available_at="2026-11-19T09:00:00Z")

    def test_naive_announcement_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "announced_at must be timezone-aware"):
            action(announced_at="2026-11-18T09:00:00",
                   available_at="2026-11-18T09:00:00Z")

    def test_naive_available_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "available_at must be timezone-aware"):
            action(announced_at="2026-11-18T09:00:00Z",
                   available_at="2026-11-18T09:00:00")


if __name__ == "__main__":
    unittest.main()
