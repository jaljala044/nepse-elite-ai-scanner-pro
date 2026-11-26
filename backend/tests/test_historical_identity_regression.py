"""Fail-closed identity regression checks. Dates are inclusive ISO calendar dates."""
import csv
import json
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def validate_intervals(rows):
    """Validate asserted mappings only, not inferred merger relationships."""
    parsed = []
    for row in rows:
        symbol, sid = row["symbol"], row["security_id"]
        if not isinstance(symbol, str) or not symbol or symbol != symbol.strip().upper():
            raise ValueError("invalid symbol")
        if not isinstance(sid, str) or not sid.isascii() or not sid.isdecimal() or int(sid) <= 0 or str(int(sid)) != sid:
            raise ValueError("invalid security ID")
        if not row.get("source"):
            raise ValueError("missing evidence")
        start = date.fromisoformat(row["start"])
        end = date.fromisoformat(row["end"]) if row.get("end") else date.max
        if start > end:
            raise ValueError("reversed interval")
        for s, i, a, b in parsed:
            if start <= b and a <= end and (s == symbol or i == sid):
                raise ValueError("overlapping symbol or security ID")
        parsed.append((symbol, sid, start, end))
    return parsed

def require_same_history(left, right):
    """Merger relationships alone never authorize raw price concatenation."""
    validate_intervals([left, right])
    if left["symbol"] != right["symbol"] or left["security_id"] != right["security_id"]:
        raise ValueError("distinct instrument history")
    if left.get("event") == "merger" or right.get("event") == "merger":
        raise ValueError("merger history requires separate reviewed transformation")

def mapping(symbol="AAA", sid="1", start="2024-01-01", end="2024-01-31", **extra):
    return dict(symbol=symbol, security_id=sid, start=start, end=end, source="synthetic test evidence", **extra)

class IdentityRegressionTests(unittest.TestCase):
    def test_duplicate_id_overlaps(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(), mapping(symbol="BBB")])

    def test_symbol_conflict_overlaps(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(), mapping(sid="2")])

    def test_exact_duplicate(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(), mapping()])

    def test_inclusive_boundary(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(), mapping(start="2024-01-31", end=None)])

    def test_nonoverlapping_observations(self):
        self.assertEqual(len(validate_intervals([mapping(), mapping(start="2024-02-01", end=None)])), 2)

    def test_reversed_dates(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(end="2023-12-31")])

    def test_unknown_id(self):
        with self.assertRaises(ValueError):
            validate_intervals([mapping(sid=None)])

    def test_missing_source(self):
        row = mapping()
        row["source"] = ""
        with self.assertRaises(ValueError):
            validate_intervals([row])

    def test_merger_does_not_authorize_splice(self):
        with self.assertRaises(ValueError):
            require_same_history(mapping(), mapping(symbol="BBB", sid="2", start="2024-02-01", end=None, event="merger"))

    def test_same_id_merger_still_blocked(self):
        with self.assertRaises(ValueError):
            require_same_history(mapping(), mapping(start="2024-02-01", end=None, event="merger"))

    def test_same_identity_nonoverlap(self):
        require_same_history(mapping(), mapping(start="2024-02-01", end=None))

    def test_current_snapshot_conflicts(self):
        path = ROOT / "data/reference/nepse_security_id_snapshot_2026-11-25.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertEqual({r["snapshot_date"] for r in rows}, {"2026-11-25"})
        validate_intervals([dict(symbol=r["symbol"], security_id=r["security_id"],
                                 start=r["snapshot_date"], end=r["snapshot_date"],
                                 source=r["source_blob_sha"]) for r in rows])

    def test_current_successor_ids_are_resolved_from_dated_snapshot(self):
        path = ROOT / "data/reference/nepse_security_id_snapshot_2026-11-25.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = {r["symbol"]: r for r in csv.DictReader(handle)}
        expected = {
            "SLBSL": "2804",
            "NMLBBL": "396",
            "MATRI": "694",
            "SMATA": "2761",
            "SMPDA": "2896",
            "GBLBS": "583",
            "PFL": "236",
        }
        retired_aliases = {
            "BPW", "MMFDB", "NLBBL", "JALPA", "KLBSL",
            "MKLB", "SABSL", "SDLBSL", "SAMAJ", "SFCL",
        }
        for symbol, security_id in expected.items():
            self.assertIn(symbol, rows)
            self.assertEqual(rows[symbol]["security_id"], security_id)
            self.assertEqual(rows[symbol]["snapshot_date"], "2026-11-25")
            self.assertEqual(rows[symbol]["active_status"], "A")
            self.assertEqual(rows[symbol]["ohlcv_file_present"], "yes")
        self.assertTrue(retired_aliases.isdisjoint(rows))

    def test_merger_predecessors_quarantined(self):
        path = ROOT / "data/reference/nepse_historical_identity_evidence_2026-11-26.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        records = [r for r in evidence["records"] if r["instrument_class"] == "equity"]
        symbols = [r["symbol"] for r in records]
        self.assertEqual(len(symbols), len(set(symbols)))
        unresolved = set(evidence["security_id_recovery"]["historical_predecessor_ids"]["symbols"])
        self.assertTrue(unresolved <= set(symbols))
        for row in records:
            if row["symbol"] in unresolved:
                self.assertIsNone(row["stable_id"])
                self.assertTrue(row["raw_history_preserved"])
        self.assertFalse(evidence["security_id_recovery"]["promotion"]["history_splicing_authorized"])

if __name__ == "__main__":
    unittest.main()
