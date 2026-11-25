import csv
import tempfile
import unittest
from pathlib import Path

from audit_ohlcv_adjustment_basis import audit_adjustment_basis


class AdjustmentBasisAuditTests(unittest.TestCase):
    def write(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "source_id","symbol","date","open","high","low","close","volume","adjustment_basis"])
            writer.writeheader()
            writer.writerows(rows)

    def row(self, source, basis, day="2026-11-24"):
        return {"source_id":source,"symbol":"AAA","date":day,"open":"10","high":"11",
                "low":"9","close":"10.5","volume":"100","adjustment_basis":basis}

    def test_single_consistent_basis_has_no_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            self.write(path, [self.row("A","unadjusted"), self.row("A","unadjusted","2026-11-25")])
            report = audit_adjustment_basis([path])
            self.assertEqual(report["source_symbol_basis_issue_count"], 0)
            self.assertFalse(report["adjustments_applied"])

    def test_mixed_basis_within_source_symbol_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            self.write(path, [self.row("A","unadjusted"), self.row("A","adjusted","2026-11-25")])
            report = audit_adjustment_basis([path])
            self.assertEqual(report["source_symbol_basis_issue_count"], 1)

    def test_cross_source_basis_difference_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a.csv", Path(tmp)/"b.csv"
            self.write(a, [self.row("A","unadjusted")])
            self.write(b, [self.row("B","adjusted")])
            report = audit_adjustment_basis([a,b])
            self.assertEqual(report["cross_source_basis_conflict_count"], 1)

    def test_unknown_basis_is_not_accepted_as_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            self.write(path, [self.row("A","unknown")])
            report = audit_adjustment_basis([path])
            self.assertEqual(report["source_symbol_basis_issue_count"], 1)

    def test_unsupported_basis_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.csv"
            self.write(path, [self.row("A","maybe")])
            with self.assertRaisesRegex(ValueError, "unsupported adjustment_basis"):
                audit_adjustment_basis([path])


if __name__ == "__main__":
    unittest.main()
