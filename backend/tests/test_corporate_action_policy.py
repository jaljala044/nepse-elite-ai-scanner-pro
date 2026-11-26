import unittest
from datetime import date
from app.corporate_action_policy import (
    CorporateActionEvidence, corporate_action_as_known, evaluate_adjustment_eligibility,
)


def action(**kwargs):
    values = dict(action_id="A1", security_id="SEC1", action_type="bonus",
                  ex_date=date(2026, 11, 30), announced_at="2026-11-20T10:00:00Z",
                  available_at="2026-11-20T10:05:00Z", source_id="issuer",
                  source_tier="primary_nepse_notice", evidence_id="DOC1", factor="1.1")
    values.update(kwargs)
    return CorporateActionEvidence(**values)


class CorporateActionPolicyTests(unittest.TestCase):
    def test_as_known_excludes_not_yet_published_action(self):
        r = corporate_action_as_known([action()], security_id="SEC1",
                                      decision_time="2026-11-19T00:00:00Z")
        self.assertEqual(r["actions"], [])

    def test_confirmed_action_visible_by_decision_time(self):
        r = corporate_action_as_known([action()], security_id="SEC1",
                                      decision_time="2026-11-25T00:00:00Z")
        self.assertEqual(len(r["actions"]), 1)
        self.assertEqual(r["evidence_ids"], ["DOC1"])

    def test_visible_provisional_action_is_reported_as_unconfirmed(self):
        provisional = action(action_id="A2", status="provisional",
                             evidence_id="DOC2", available_at="2026-11-22T10:00:00Z")
        report = corporate_action_as_known([action(), provisional], security_id="SEC1",
                                            decision_time="2026-11-25T00:00:00Z")
        self.assertEqual(report["visible_action_count"], 2)
        self.assertEqual([item.action_id for item in report["actions"]], ["A1"])
        self.assertFalse(report["all_visible_actions_confirmed"])
        self.assertEqual(report["excluded_visible_actions"], [{
            "action_id":"A2","status":"provisional","evidence_id":"DOC2"
        }])
        self.assertEqual(report["evidence_ids"], ["DOC1", "DOC2"])

    def test_adjustment_never_applied_by_eligibility_check(self):
        r = evaluate_adjustment_eligibility(action(), policy_version="raw_unadjusted_v1",
                                            decision_time="2026-11-25T00:00:00Z",
                                            independently_reviewed=True)
        self.assertTrue(r["eligible_for_adjustment_review"])
        self.assertFalse(r["adjustment_applied"])
        self.assertFalse(r["raw_price_series_mutated"])

    def test_secondary_source_cannot_authorize_adjustment(self):
        r = evaluate_adjustment_eligibility(
            action(source_tier="secondary_notice"),
            policy_version="raw_unadjusted_v1",
            decision_time="2026-11-25T00:00:00Z",
            independently_reviewed=True,
        )
        self.assertFalse(r["eligible_for_adjustment_review"])
        self.assertEqual(r["reason"], "primary_source_required")
        self.assertFalse(r["adjustment_applied"])

    def test_missing_adjustment_factor_blocks_review(self):
        r = evaluate_adjustment_eligibility(
            action(factor=None),
            policy_version="raw_unadjusted_v1",
            decision_time="2026-11-25T00:00:00Z",
            independently_reviewed=True,
        )
        self.assertFalse(r["eligible_for_adjustment_review"])
        self.assertEqual(r["reason"], "verified_adjustment_factor_required")

    def test_unknown_source_tier_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported corporate action source tier"):
            action(source_tier="exchange_telegram")

    def test_unreviewed_or_unapproved_policy_blocks_adjustment(self):
        r = evaluate_adjustment_eligibility(action(), policy_version="unknown-v9",
                                            decision_time="2026-11-25T00:00:00Z")
        self.assertFalse(r["eligible_for_adjustment_review"])

    def test_available_before_announcement_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            action(available_at="2026-11-19T00:00:00Z")

    def test_non_date_ex_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "ex_date must be a date"):
            action(ex_date="2026-11-30")

    def test_unparseable_factor_rejected_as_value_error(self):
        with self.assertRaisesRegex(ValueError, "finite positive decimal"):
            action(factor="not-a-number")

    def test_missing_source_tier_rejected(self):
        with self.assertRaisesRegex(ValueError, "source tier"):
            action(source_tier="")

    def test_invalid_factor_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite positive"):
            action(factor="NaN")


if __name__ == "__main__":
    unittest.main()
