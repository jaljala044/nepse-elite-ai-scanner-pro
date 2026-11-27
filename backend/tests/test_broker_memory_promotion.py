import unittest

from backend.broker_memory.promotion import (
    PromotionStatus,
    ReconciliationEvidence,
    promote_reconciled_batch,
)


class FakeStore:
    def __init__(self, result="APPENDED"):
        self.result = result
        self.calls = []

    def append_batch(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def evidence(**overrides):
    values = dict(
        batch_id="session-2026-11-26-source-a",
        source_payload_sha256="a" * 64,
        session_date="2026-11-26",
        available_at="2026-11-26T16:00:00+05:45",
        coverage_status="COMPLETE",
        accepted_row_count=1,
        quarantined_row_count=0,
        validation_passed=True,
        source_rights_cleared=True,
        session_verified=True,
        point_in_time_valid=True,
        source_manifest_sha256="b" * 64,
    )
    values.update(overrides)
    return ReconciliationEvidence(**values)


class PromotionTests(unittest.TestCase):
    def test_complete_batch_reaches_store(self):
        store = FakeStore("APPENDED")
        result = promote_reconciled_batch(evidence(), [{"symbol": "ABC", "net": "10"}], store)
        self.assertEqual(result.status, PromotionStatus.PROMOTED)
        self.assertEqual(len(store.calls), 1)

    def test_partial_coverage_is_blocked_without_store_write(self):
        store = FakeStore()
        result = promote_reconciled_batch(
            evidence(coverage_status="PARTIAL"), [{"symbol": "ABC"}], store
        )
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("COVERAGE_NOT_COMPLETE", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_quarantine_blocks_entire_batch(self):
        store = FakeStore()
        result = promote_reconciled_batch(
            evidence(quarantined_row_count=1), [{"symbol": "ABC"}], store
        )
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("QUARANTINE_PRESENT", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_rights_or_point_in_time_failure_blocks(self):
        store = FakeStore()
        result = promote_reconciled_batch(
            evidence(source_rights_cleared=False, point_in_time_valid=False),
            [{"symbol": "ABC"}], store
        )
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("SOURCE_RIGHTS_NOT_CLEARED", result.reason_codes)
        self.assertIn("POINT_IN_TIME_GATE_FAILED", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_non_hex_digests_are_blocked(self):
        store = FakeStore()
        result = promote_reconciled_batch(
            evidence(source_payload_sha256="g" * 64, source_manifest_sha256="z" * 64),
            [{"symbol": "ABC"}], store)
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("INVALID_SOURCE_PAYLOAD_DIGEST", result.reason_codes)
        self.assertIn("INVALID_SOURCE_MANIFEST_DIGEST", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_noncanonical_session_and_naive_availability_are_blocked(self):
        store = FakeStore()
        result = promote_reconciled_batch(
            evidence(session_date="20261126", available_at="2026-11-26T16:00:00"),
            [{"symbol": "ABC"}], store)
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("INVALID_SESSION_DATE", result.reason_codes)
        self.assertIn("INVALID_AVAILABLE_AT", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_row_count_mismatch_blocks(self):
        store = FakeStore()
        result = promote_reconciled_batch(evidence(), [], store)
        self.assertEqual(result.status, PromotionStatus.BLOCKED)
        self.assertIn("ROW_COUNT_MISMATCH_OR_EMPTY_BATCH", result.reason_codes)
        self.assertEqual(store.calls, [])

    def test_replay_is_reported_as_replay(self):
        store = FakeStore("REPLAYED")
        result = promote_reconciled_batch(evidence(), [{"symbol": "ABC"}], store)
        self.assertEqual(result.status, PromotionStatus.REPLAYED)
        self.assertEqual(result.snapshot_count, 0)

    def test_conflicting_idempotency_key_is_not_reported_as_success(self):
        store = FakeStore("CONFLICT")
        result = promote_reconciled_batch(evidence(), [{"symbol": "ABC"}], store)
        self.assertEqual(result.status, PromotionStatus.CONFLICT)
        self.assertEqual(result.snapshot_count, 0)


if __name__ == "__main__":
    unittest.main()
