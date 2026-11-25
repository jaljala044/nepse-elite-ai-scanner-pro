import tempfile
import unittest
from pathlib import Path

from build_ohlcv_exception_ledger import build_ledger, write_ledger


def report_fixture():
    repos = {
        "source-a": {
            "commit_sha": "a" * 40, "tree_sha": "b" * 40,
            "files": [{
                "symbol": "AAA", "path": "AAA_OHLCV.csv", "sha256": "c" * 64,
                "invalid_rows": [{
                    "line": 7, "error": "high below close",
                    "row": {"Date": "2026-01-02", "Open": "10", "High": "9", "Low": "8", "Close": "10", "Volume": "1"},
                }],
            }],
        },
        "source-b": {
            "commit_sha": "d" * 40, "tree_sha": "e" * 40,
            "files": [{
                "symbol": "AAA", "path": "AAA_OHLCV.csv", "sha256": "f" * 64,
                "invalid_rows": [],
            }],
        },
    }
    return {
        "generated_at_utc": "2026-01-03T00:00:00Z",
        "mode": "pinned_commit_read_only_row_level_audit",
        "repositories": repos,
        "cross_source": {
            "conflicts": [{
                "symbol": "AAA", "date": "2026-01-02",
                "source_rows": {
                    "source-a": {"symbol": "AAA", "date": "2026-01-02", "close": "10"},
                    "source-b": {"symbol": "AAA", "date": "2026-01-02", "close": "11"},
                },
            }],
        },
    }


class ExceptionLedgerBuilderTests(unittest.TestCase):
    def test_builds_quarantine_rows_with_full_lineage(self):
        ledger = build_ledger(report_fixture(), expected_invalid_rows=1, expected_conflicts=1)
        self.assertEqual(ledger["counts"]["total_exception_records"], 2)
        invalid, conflict = ledger["exceptions"]
        self.assertEqual(invalid["source_csv_line"], 7)
        self.assertEqual(invalid["raw_source_row"]["High"], "9")
        self.assertEqual(conflict["source_evidence"]["source-a"]["row"]["close"], "10")
        self.assertEqual(conflict["source_evidence"]["source-b"]["row"]["close"], "11")
        self.assertTrue(all(x["disposition"] == "quarantined_unresolved" for x in ledger["exceptions"]))

    def test_count_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "population drift"):
            build_ledger(report_fixture(), expected_invalid_rows=1331, expected_conflicts=8)

    def test_duplicate_conflict_ids_fail_closed(self):
        report = report_fixture()
        report["cross_source"]["conflicts"].append(report["cross_source"]["conflicts"][0])
        with self.assertRaisesRegex(ValueError, "duplicate exception IDs"):
            build_ledger(report, expected_invalid_rows=1, expected_conflicts=2)

    def test_writes_json_and_csv_with_source_report_hash(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "audit.json"
            source.write_text(json.dumps(report_fixture()), encoding="utf-8")
            jp, cp = root / "ledger.json", root / "ledger.csv"
            counts = write_ledger(source, jp, cp, expected_invalid_rows=1, expected_conflicts=1)
            saved = json.loads(jp.read_text(encoding="utf-8"))
            self.assertEqual(counts["total_exception_records"], 2)
            self.assertEqual(len(saved["source_audit"]["source_audit_report_sha256"]), 64)
            self.assertTrue(cp.read_text(encoding="utf-8").startswith("exception_id,"))


if __name__ == "__main__":
    unittest.main()
