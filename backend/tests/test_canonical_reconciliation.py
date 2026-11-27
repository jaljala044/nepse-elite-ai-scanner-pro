import tempfile
import unittest
from pathlib import Path
from app.canonical_reconciliation import reconcile_ohlcv_batches, persist_reconciliation_ledger

CUTOFF = "2026-11-27T16:00:00+05:45"
EXPECTED = [{"security_id": "SEC-1", "session_date": "2026-11-26"}]

def batch(source, group, values=None, **overrides):
    row = {"status": "valid_candidate", "security_id": "SEC-1", "session_date": "2026-11-26",
           "line_number": 2, "values": values or {"open": "100", "high": "110", "low": "95",
           "close": "108", "volume": "1000", "turnover": "108000"}}
    result = {"source_id": source, "independence_group": group, "independence_review_status": "approved",
              "source_validation_status": "verified", "rights_status": "approved", "finality_status": "final",
              "available_at": "2026-11-26T16:05:00+05:45", "raw_sha256": (source.encode().hex() * 32)[:64],
              "rows": [row]}
    result.update(overrides)
    return result

class CanonicalReconciliationTests(unittest.TestCase):
    def test_two_independent_sources_reconcile(self):
        r = reconcile_ohlcv_batches(batches=[batch("SRC-A","publisher-a"),batch("SRC-B","publisher-b")],
                                    expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        self.assertEqual(r["status"],"research_only_reconciled")
        self.assertEqual(r["reconciled_pair_count"],1)
        self.assertFalse(r["canonical_promotion_allowed"])

    def test_same_independence_group_does_not_count_twice(self):
        r = reconcile_ohlcv_batches(batches=[batch("SRC-A","same"),batch("SRC-B","same")],
                                    expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        self.assertEqual(r["quarantined"][0]["reason"],"insufficient_independently_reviewed_sources")

    def test_conflict_quarantines_pair(self):
        other={"open":"100","high":"112","low":"95","close":"109","volume":"1000","turnover":"109000"}
        r=reconcile_ohlcv_batches(batches=[batch("SRC-A","a"),batch("SRC-B","b",other)],
                                  expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        self.assertEqual(r["quarantined"][0]["reason"],"cross_source_value_conflict")
        self.assertEqual(r["reconciled_pair_count"],0)

    def test_late_or_unlicensed_sources_rejected(self):
        r=reconcile_ohlcv_batches(batches=[batch("SRC-A","a",rights_status="unknown"),
            batch("SRC-B","b",available_at="2026-11-27T17:00:00+05:45")],
            expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        self.assertEqual(r["rejected_source_count"],2)
        self.assertEqual(r["missing_pair_count"],1)

    def test_single_source_is_quarantined_not_missing(self):
        r=reconcile_ohlcv_batches(batches=[batch("SRC-A","a")],expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        self.assertEqual(r["missing_pair_count"],0)
        self.assertEqual(r["quarantined_pair_count"],1)

    def test_content_addressed_persistence_is_idempotent(self):
        ledger=reconcile_ohlcv_batches(batches=[batch("SRC-A","a"),batch("SRC-B","b")],
                                       expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        with tempfile.TemporaryDirectory() as tmp:
            first=persist_reconciliation_ledger(tmp,ledger)
            second=persist_reconciliation_ledger(tmp,ledger)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertTrue(Path(first["path"]).exists())

    def test_ledger_tampering_is_rejected(self):
        ledger=reconcile_ohlcv_batches(batches=[batch("SRC-A","a"),batch("SRC-B","b")],
                                       expected_pairs=EXPECTED,decision_cutoff=CUTOFF)
        ledger["status"]="approved"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): persist_reconciliation_ledger(tmp,ledger)

if __name__ == "__main__": unittest.main()
