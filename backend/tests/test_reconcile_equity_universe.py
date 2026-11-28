from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reconcile_equity_universe import _load, reconcile_snapshots


def row(symbol, security_id, instrument_type="Equity", status="Active"):
    return {"symbol": symbol, "security_id": security_id,
            "instrument_type": instrument_type, "status": status}


class EquityUniverseReconciliationTests(unittest.TestCase):
    def call(self, candidate, provider, **kwargs):
        values = {
            "candidate_sha256": "a" * 64, "provider_sha256": "b" * 64,
            "candidate_observed_on": "2026-11-26", "provider_observed_on": "2026-11-28",
        }
        values.update(kwargs)
        return reconcile_snapshots(candidate, provider, **values)

    def test_extras_missing_and_identity_conflict(self):
        report = self.call(
            [row("AAA", "1"), row("BBB", "2"), row("CCC", "3")],
            [row("AAA", "1"), row("BBB", "22"), row("DDD", "4", "Mutual Fund")],
        )
        by_symbol = {item["symbol"]: item["classification"] for item in report["matrix"]}
        self.assertEqual(by_symbol["AAA"], "matched")
        self.assertEqual(by_symbol["BBB"], "identity_or_scope_conflict:security_id")
        self.assertEqual(by_symbol["CCC"], "candidate_only")
        self.assertEqual(by_symbol["DDD"], "provider_only")

    def test_duplicate_rows_are_preserved(self):
        report = self.call([row("AAA", "1"), row("AAA", "1")], [row("AAA", "1")])
        self.assertEqual(report["summary"]["duplicate_candidate_symbol_count"], 1)
        self.assertIn("duplicate_candidate_rows", report["matrix"][0]["classification"])

    def test_type_and_status_conflicts(self):
        report = self.call([row("AAA", "1")], [row("AAA", "1", "Mutual Fund", "Suspended")])
        self.assertEqual(report["matrix"][0]["classification"],
                         "identity_or_scope_conflict:instrument_type,status")

    def test_security_id_reused_across_different_symbols_is_flagged(self):
        report = self.call(
            [row("AAA", "1"), row("BBB", "1")],
            [row("AAA", "1"), row("BBB", "2")],
        )
        self.assertEqual(report["summary"]["candidate_security_id_collision_count"], 1)
        by_symbol = {item["symbol"]: item for item in report["matrix"]}
        self.assertIn("candidate_security_id_reused_across_symbols",
                      by_symbol["AAA"]["classification"])
        self.assertIn("candidate_security_id_reused_across_symbols",
                      by_symbol["BBB"]["classification"])

    def test_no_membership_or_promotion_claim(self):
        report = self.call([row("AAA", "1")], [row("AAA", "1")])
        self.assertFalse(report["summary"]["membership_authoritatively_verified"])
        self.assertFalse(report["summary"]["canonical_promotion_allowed"])

    def test_snapshot_dates_and_hashes_are_validated(self):
        with self.assertRaisesRegex(ValueError, "candidate_observed_on"):
            self.call([row("AAA", "1")], [row("AAA", "1")],
                      candidate_observed_on="2026-1-2")
        with self.assertRaisesRegex(ValueError, "provider_sha256"):
            self.call([row("AAA", "1")], [row("AAA", "1")], provider_sha256="bad")

    def test_empty_snapshots_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "candidate snapshot must not be empty"):
            self.call([], [row("AAA", "1")])
        with self.assertRaisesRegex(ValueError, "provider snapshot must not be empty"):
            self.call([row("AAA", "1")], [])

    def test_csv_loader_hashes_bytes_and_requires_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.csv"
            path.write_text(
                "symbol,security_id,instrument_type,status\nAAA,1,Equity,Active\n",
                encoding="utf-8",
            )
            rows, digest = _load(path)
            self.assertEqual(rows[0]["symbol"], "AAA")
            self.assertEqual(len(digest), 64)
            path.write_text("symbol,security_id\nAAA,1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                _load(path)


if __name__ == "__main__":
    unittest.main()
