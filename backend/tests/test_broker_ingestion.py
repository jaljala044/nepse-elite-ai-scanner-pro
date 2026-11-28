from decimal import Decimal
import unittest
from app.broker_ingestion import ContractTotal, IngestionError, payload_hash, reconcile_broker_batch

def make_row(**overrides):
    payload = {"trade_file": "source-row-1", "value": 123}
    row = {
        "security_id": "CFCL", "broker_id": "BROKER-1", "session_date": "2026-11-25",
        "side": "BUY", "quantity": "10", "amount": "1250.00", "source_id": "SRC-A",
        "evidence_id": "E-1", "source_payload": payload,
        "source_payload_sha256": payload_hash(payload), "source_row_count": 1,
        "coverage_ratio": "1.0",
    }
    row.update(overrides)
    return row

def rights_evidence(**overrides):
    value = {
        "source_id": "SRC-A", "evidence_id": "RIGHTS-1", "status": "approved",
        "document_sha256": "c" * 64,
        "scope": ["electronic_storage", "aggregation"],
        "effective_from": "2026-01-01", "effective_to": None,
        "available_at": "2026-11-24T10:00:00+05:45",
    }
    value.update(overrides)
    return value


def run(rows=None, **kwargs):
    defaults = dict(batch_id="B-1", rows=rows or [make_row()],
        verified_brokers={"BROKER-1"}, verified_sessions={"2026-11-25"},
        expected_source_ids={"SRC-A"}, received_source_ids={"SRC-A"},
        available_at="2026-11-26T09:00:00+05:45",
        verified_session_finality={"2026-11-25": "2026-11-25T16:00:00+05:45"},
        source_rights_evidence={"SRC-A": rights_evidence()})
    defaults.update(kwargs)
    return reconcile_broker_batch(**defaults)

class BrokerIngestionTests(unittest.TestCase):
    def test_valid_complete_batch_is_descriptive_and_eligible(self):
        result = run(contracts=[ContractTotal("CFCL", "BROKER-1", "2026-11-25",
            "BUY", Decimal("10"), Decimal("1250.00"))])
        self.assertTrue(result.memory_eligible, repr(result))
        self.assertEqual(result.accepted[0]["status"], "descriptive_only")

    def test_unverified_broker_quarantined(self):
        result = run(verified_brokers=set())
        self.assertIn("unverified_broker_identity", result.quarantined[0]["reasons"])

    def test_noncanonical_trade_dates_are_quarantined(self):
        for value in ("20261125", "2026-W48-3", "2026-1-4", "2026/11/25"):
            with self.subTest(session_date=value):
                result = run([make_row(session_date=value)])
                self.assertFalse(result.memory_eligible)
                self.assertIn("unverified_or_invalid_session", result.quarantined[0]["reasons"])

    def test_noncanonical_verified_session_inventory_is_rejected(self):
        for value in ("20261125", "2026-W48-3", "2026-1-4", "2026/11/25"):
            with self.subTest(session=value), self.assertRaisesRegex(IngestionError, "invalid_verified_session_inventory"):
                run(verified_sessions={value})

    def test_non_string_trade_date_is_quarantined(self):
        result = run([make_row(session_date=20261125)])
        self.assertFalse(result.memory_eligible)
        self.assertIn("unverified_or_invalid_session", result.quarantined[0]["reasons"])

    def test_unknown_session_quarantined(self):
        result = run(verified_sessions=set())
        self.assertIn("unverified_or_invalid_session", result.quarantined[0]["reasons"])

    def test_naive_availability_rejected_and_early_availability_quarantined(self):
        with self.assertRaises(IngestionError):
            run(available_at="2026-11-26T09:00:00")
        result = run(available_at="2026-11-24T23:59:00+05:45")
        self.assertFalse(result.memory_eligible)

    def test_payload_hash_mismatch_quarantined(self):
        result = run([make_row(source_payload_sha256="0" * 64)])
        self.assertIn("source_payload_hash_mismatch", result.quarantined[0]["reasons"])

    def test_negative_quantity_quarantined(self):
        self.assertFalse(run([make_row(quantity="-1")]).memory_eligible)

    def test_exact_duplicate_is_skipped(self):
        row = make_row()
        result = run([row, row])
        self.assertEqual(result.duplicates_skipped, 1, repr(result))
        self.assertEqual(len(result.accepted), 1)

    def test_conflicting_duplicate_blocks_batch(self):
        changed_payload = {"trade_file": "source-row-1", "value": 1300}
        changed = make_row(amount="1300", source_payload=changed_payload,
                           source_payload_sha256=payload_hash(changed_payload))
        result = run([make_row(), changed])
        self.assertEqual(result.conflicts, 1)
        self.assertFalse(result.memory_eligible)

    def test_prior_exact_replay_is_noop(self):
        row = make_row()
        key = "CFCL|BROKER-1|2026-11-25|BUY|SRC-A|E-1"
        result = run([row], seen_natural_keys={key: row["source_payload_sha256"]})
        self.assertEqual(result.duplicates_skipped, 1)
        self.assertEqual(result.accepted, [])

    def test_contract_mismatch_blocks_batch(self):
        contract = ContractTotal("CFCL", "BROKER-1", "2026-11-25",
            "BUY", Decimal("11"), Decimal("1250.00"))
        result = run(contracts=[contract])
        self.assertFalse(result.memory_eligible)
        self.assertIn("contract_reconciliation_mismatch", result.quarantined[-1]["reasons"])

    def test_partial_and_unknown_coverage_never_become_zero_flow(self):
        partial = run(expected_source_ids={"SRC-A", "SRC-B"}, received_source_ids={"SRC-A"})
        unknown = run(expected_source_ids=set(), received_source_ids=set())
        self.assertEqual(partial.coverage_status, "partial")
        self.assertEqual(unknown.coverage_status, "unknown")
        self.assertFalse(partial.memory_eligible)
        self.assertFalse(unknown.memory_eligible)

    def test_missing_source_rights_evidence_blocks_batch(self):
        result = run(source_rights_evidence={})
        self.assertFalse(result.memory_eligible)
        self.assertTrue(any("source_rights_unverified:SRC-A" in reason
                            for item in result.quarantined for reason in item["reasons"]))

    def test_denied_source_rights_blocks_batch(self):
        result = run(source_rights_evidence={"SRC-A": rights_evidence(status="denied")})
        self.assertFalse(result.memory_eligible)
        self.assertTrue(any("source_rights_unverified:SRC-A" in reason
                            for item in result.quarantined for reason in item["reasons"]))

    def test_insufficient_source_rights_scope_blocks_batch(self):
        result = run(source_rights_evidence={"SRC-A": rights_evidence(scope=["display"])})
        self.assertFalse(result.memory_eligible)
        self.assertTrue(any("source_rights_scope_insufficient" in reason
                            for item in result.quarantined for reason in item["reasons"]))

    def test_late_source_rights_evidence_blocks_batch(self):
        result = run(source_rights_evidence={"SRC-A": rights_evidence(
            available_at="2026-11-27T10:00:00+05:45")})
        self.assertFalse(result.memory_eligible)
        self.assertTrue(any("source_rights_evidence_not_yet_available" in reason
                            for item in result.quarantined for reason in item["reasons"]))

    def test_rights_effective_date_must_cover_trade_session(self):
        result = run(source_rights_evidence={"SRC-A": rights_evidence(
            effective_from="2026-11-26")})
        self.assertFalse(result.memory_eligible)
        self.assertIn("source_rights_not_effective_for_session",
                      result.quarantined[0]["reasons"])

    def test_availability_timezone_is_required(self):
        with self.assertRaises(IngestionError):
            run(available_at="2026-11-26T09:00:00")

if __name__ == "__main__":
    unittest.main()
