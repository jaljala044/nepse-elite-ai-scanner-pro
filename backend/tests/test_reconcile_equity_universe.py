from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from backend.reconcile_equity_universe import _load, reconcile_snapshots

def row(symbol, security_id, instrument_type="Equity", status="Active"):
    return {"symbol": symbol, "security_id": security_id, "instrument_type": instrument_type, "status": status}

class EquityUniverseReconciliationTests(unittest.TestCase):
    def call(self, a, b):
        return reconcile_snapshots(a, b, candidate_sha256="a"*64, provider_sha256="b"*64,
                                   candidate_observed_on="2026-11-26", provider_observed_on="2026-11-28")
    def test_extras_missing_and_identity_conflict(self):
        r = self.call([row("AAA","1"),row("BBB","2"),row("CCC","3")],
                      [row("AAA","1"),row("BBB","22"),row("DDD","4","Mutual Fund")])
        by = {x["symbol"]:x["classification"] for x in r["matrix"]}
        self.assertEqual(by["AAA"],"matched")
        self.assertEqual(by["BBB"],"identity_or_scope_conflict:security_id")
        self.assertEqual(by["CCC"],"candidate_only")
        self.assertEqual(by["DDD"],"provider_only")
    def test_duplicate_rows_preserved(self):
        r = self.call([row("AAA","1"),row("AAA","1")],[row("AAA","1")])
        self.assertEqual(r["summary"]["duplicate_candidate_symbol_count"],1)
        self.assertIn("duplicate_candidate_rows",r["matrix"][0]["classification"])
    def test_type_and_status_conflicts(self):
        r = self.call([row("AAA","1")],[row("AAA","1","Mutual Fund","Suspended")])
        self.assertEqual(r["matrix"][0]["classification"],
                         "identity_or_scope_conflict:instrument_type,status")
    def test_no_membership_or_promotion_claim(self):
        r = self.call([row("AAA","1")],[row("AAA","1")])
        self.assertFalse(r["summary"]["membership_authoritatively_verified"])
        self.assertFalse(r["summary"]["canonical_promotion_allowed"])
    def test_csv_loader_hashes_bytes_and_requires_columns(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.csv"
            p.write_text("symbol,security_id,instrument_type,status\nAAA,1,Equity,Active\n")
            rows,digest=_load(p)
            self.assertEqual(rows[0]["symbol"],"AAA")
            self.assertEqual(len(digest),64)
            p.write_text("symbol,security_id\nAAA,1\n")
            with self.assertRaisesRegex(ValueError,"missing columns"): _load(p)

if __name__ == "__main__": unittest.main()
