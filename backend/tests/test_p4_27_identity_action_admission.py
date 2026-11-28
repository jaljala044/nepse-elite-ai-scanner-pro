import unittest

from app.p4_27_identity_action_admission import (
    reconcile_corporate_action_assertions,
    resolve_effective_dated_identities,
)


class IdentityActionAdmissionTests(unittest.TestCase):
    cutoff = "2026-11-28T12:00:00+05:45"
    digest = "a" * 64
    archive = {"verified_documents": [{
        "event_id": "LIST1", "publisher_id": "nepse",
        "sha256": digest, "available_at": "2024-01-01T09:00:00+05:45",
    }]}

    def identity(self, **extra):
        row = {
            "symbol": "ABC", "security_id": "1001", "instrument_class": "equity",
            "effective_from": "2024-01-01", "effective_to": "2024-12-31",
            "available_at": "2024-01-01T10:00:00+05:45", "event_id": "LIST1",
            "source_tier": "primary_nepse_or_cdsc", "publisher_id": "nepse",
            "evidence_sha256": self.digest, "review_status": "approved",
            "reviewer_id": "independent-reviewer",
        }
        row.update(extra)
        return row

    def action(self, publisher, tier, **extra):
        row = {
            "action_id": "CA1", "symbol": "ABC", "security_id": "1001",
            "action_type": "bonus", "announced_at": "2024-01-01T10:00:00+05:45",
            "available_at": "2024-01-01T10:01:00+05:45", "ex_date": "2024-02-01",
            "publisher_id": publisher, "source_id": publisher + "-doc-1",
            "source_tier": tier, "evidence_sha256": ("a" * 64 if publisher == "nepse" else "b" * 64),
            "status": "confirmed", "adjustment_factor": "0.9",
            "factor_methodology_id": "bonus-method-v1",
            "review_status": "approved", "reviewer_id": "independent-reviewer",
        }
        row.update(extra)
        return row

    def test_identity_interval_resolves_only_when_hash_and_primary_doc_match(self):
        report = resolve_effective_dated_identities(
            records=[self.identity()], required_symbols=["ABC"],
            archive_report=self.archive, decision_cutoff=self.cutoff,
        )
        self.assertEqual(report["status"], "IDENTITY_INTERVALS_REVIEWED")
        self.assertFalse(report["historical_universe_join_allowed"])

    def test_identity_hash_mismatch_blocks(self):
        report = resolve_effective_dated_identities(
            records=[self.identity(evidence_sha256="b" * 64)],
            required_symbols=["ABC"], archive_report=self.archive,
            decision_cutoff=self.cutoff,
        )
        self.assertEqual(report["status"], "IDENTITY_INTERVALS_BLOCKED")
        self.assertIn("ABC", report["missing_symbols"])

    def test_overlapping_symbol_intervals_block(self):
        rows = [
            self.identity(),
            self.identity(security_id="1002", effective_from="2024-06-01",
                          effective_to="2025-01-01"),
        ]
        report = resolve_effective_dated_identities(
            records=rows, required_symbols=["ABC"],
            archive_report=self.archive, decision_cutoff=self.cutoff,
        )
        self.assertTrue(any(
            e["reason"] == "overlapping_effective_identity_intervals"
            for e in report["errors"]
        ))

    def test_future_identity_evidence_blocks(self):
        report = resolve_effective_dated_identities(
            records=[self.identity(available_at="2026-12-01T00:00:00+05:45")],
            required_symbols=["ABC"], archive_report=self.archive,
            decision_cutoff=self.cutoff,
        )
        self.assertEqual(report["status"], "IDENTITY_INTERVALS_BLOCKED")

    def test_action_requires_two_publishers_including_primary(self):
        report = reconcile_corporate_action_assertions(
            records=[self.action("nepse", "primary_nepse_or_cdsc")],
            decision_cutoff=self.cutoff,
        )
        self.assertEqual(report["status"], "ACTION_RECONCILIATION_BLOCKED")

    def test_matching_primary_and_secondary_action_assertions_reconcile(self):
        rows = [
            self.action("nepse", "primary_nepse_or_cdsc"),
            self.action("secondary", "independent_secondary"),
        ]
        report = reconcile_corporate_action_assertions(records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "ACTION_ASSERTIONS_RECONCILED")
        self.assertFalse(report["price_adjustment_admission_allowed"])

    def test_action_disagreement_and_non_independent_reviewer_block(self):
        rows = [
            self.action("nepse", "primary_nepse_or_cdsc"),
            self.action("secondary", "independent_secondary",
                        adjustment_factor="0.8", reviewer_id="secondary"),
        ]
        report = reconcile_corporate_action_assertions(records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "ACTION_RECONCILIATION_BLOCKED")
        self.assertTrue(any(
            e["reason"] in {"corporate_action_assertions_disagree", "action_reviewer_not_independent"}
            for e in report["errors"]
        ))

    def test_duplicate_source_assertion_blocks(self):
        row = self.action("nepse", "primary_nepse_or_cdsc")
        report = reconcile_corporate_action_assertions(
            records=[row, row], decision_cutoff=self.cutoff,
        )
        self.assertEqual(report["status"], "ACTION_RECONCILIATION_BLOCKED")


if __name__ == "__main__":
    unittest.main()
