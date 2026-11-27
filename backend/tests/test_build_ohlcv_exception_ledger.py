import tempfile
import unittest
from pathlib import Path

from build_ohlcv_exception_ledger import build_ledger, write_ledger, USER_AUTHORITATIVE_RESOLUTIONS, FIELD_SCOPED_NEPSE_RESOLUTIONS


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
                    "source-a": {"symbol": "AAA", "date": "2026-01-02", "close": "10", "source_csv_line": 2},
                    "source-b": {"symbol": "AAA", "date": "2026-01-02", "close": "11", "source_csv_line": 2},
                },
            }],
        },
    }


class ExceptionLedgerBuilderTests(unittest.TestCase):
    def test_builds_quarantine_rows_with_full_lineage(self):
        ledger = build_ledger(report_fixture(), expected_invalid_rows=1, expected_conflicts=1)
        self.assertEqual(ledger["counts"]["total_exception_records"], 2)
        invalid = next(x for x in ledger["exceptions"] if x["exception_type"] == "invalid_ohlc")
        conflict = next(x for x in ledger["exceptions"] if x["exception_type"] == "cross_source_ohlcv_conflict")
        self.assertEqual(invalid["source_csv_line"], 7)
        self.assertEqual(invalid["raw_source_row"]["High"], "9")
        self.assertEqual(conflict["source_evidence"]["source-a"]["row"]["close"], "10")
        self.assertEqual(conflict["source_evidence"]["source-b"]["row"]["close"], "11")
        self.assertEqual(conflict["source_evidence"]["source-a"]["source_csv_line"], 2)
        self.assertEqual(conflict["source_evidence"]["source-b"]["source_csv_line"], 2)
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
            original_source_bytes = source.read_bytes()
            jp, cp = root / "ledger.json", root / "ledger.csv"
            counts = write_ledger(source, jp, cp, expected_invalid_rows=1, expected_conflicts=1)
            saved = json.loads(jp.read_text(encoding="utf-8"))
            import hashlib
            self.assertEqual(saved["source_audit"]["source_audit_report_sha256"], hashlib.sha256(original_source_bytes).hexdigest())
            self.assertEqual(source.read_bytes(), original_source_bytes)
            self.assertEqual(counts["total_exception_records"], 2)
            self.assertEqual(len(saved["source_audit"]["source_audit_report_sha256"]), 64)
            with cp.open(encoding="utf-8", newline="") as stream:
                import csv
                self.assertIn("exception_id", csv.DictReader(stream).fieldnames)


    def test_user_authoritative_2025_07_28_conflict_is_resolved_only_for_exact_key(self):
        report = report_fixture()
        report["repositories"]["source-a"]["files"][0]["symbol"] = "BGWT"
        report["repositories"]["source-a"]["files"][0]["path"] = "BGWT_OHLCV.csv"
        report["repositories"]["source-b"]["files"][0]["symbol"] = "BGWT"
        report["repositories"]["source-b"]["files"][0]["path"] = "BGWT_OHLCV.csv"
        report["cross_source"]["conflicts"][0]["symbol"] = "BGWT"
        report["cross_source"]["conflicts"][0]["date"] = "2025-07-28"
        for repo in ("source-a", "source-b"):
            report["repositories"][repo]["files"][0]["invalid_rows"] = []
        ledger = build_ledger(report, expected_invalid_rows=0, expected_conflicts=1)
        conflict = ledger["exceptions"][0]
        self.assertEqual(conflict["disposition"], "resolved_with_user_authoritative_evidence")
        self.assertIn("conversation-memory://user-final-authoritative-2025-07-28-records", conflict["evidence_pointer"])
        self.assertEqual(ledger["counts"]["resolved_with_user_authoritative_evidence"], 1)
        self.assertEqual(ledger["counts"]["unresolved"], 0)
        self.assertEqual(conflict["resolution_evidence"]["authoritative_values"]["close"], "957.17")
        self.assertFalse(conflict["resolution_evidence"]["canonical_promotion_allowed"])
        self.assertFalse(conflict["resolution_evidence"]["raw_source_rows_modified"])

    def test_five_user_records_and_two_nepse_field_scoped_records_are_allowlisted(self):
        expected = {
            ("BGWT", "2025-07-28"), ("MEHL", "2025-07-28"),
            ("RAWA", "2025-07-28"), ("RHGCL", "2025-07-28"),
            ("ULHC", "2025-07-28"),
        }
        self.assertEqual(set(USER_AUTHORITATIVE_RESOLUTIONS), expected)
        self.assertEqual(set(FIELD_SCOPED_NEPSE_RESOLUTIONS), {("API", "2026-11-19"), ("RHGCL", "2026-11-19")})
        self.assertEqual(FIELD_SCOPED_NEPSE_RESOLUTIONS[("RHGCL", "2026-11-19")]["supported_fields"]["close"], "258.00")
        self.assertNotIn("open", FIELD_SCOPED_NEPSE_RESOLUTIONS[("RHGCL", "2026-11-19")]["supported_fields"])

    def test_external_corroboration_is_attached_without_source_selection(self):
        report = report_fixture()
        external = {"records": [{
            "symbol": "AAA", "date": "2026-01-02", "external_status": "matched_symbol",
            "external_file_sha256": "f" * 64, "classification": "partial_or_conflicting",
            "external_row": {"close": "12"}, "source_comparisons": {"source-a": {"status": "partial_match"}}
        }]}
        ledger = build_ledger(report, external_report=external, expected_invalid_rows=1, expected_conflicts=1)
        invalid = next(row for row in ledger["exceptions"] if row["exception_type"] == "invalid_ohlc")
        conflict = next(row for row in ledger["exceptions"] if row["exception_type"] == "cross_source_ohlcv_conflict")
        self.assertEqual(invalid["external_corroboration"]["classification"], "partial_or_conflicting")
        self.assertEqual(conflict["external_corroboration"]["external_file_sha256"], "f" * 64)
        self.assertEqual(invalid["disposition"], "quarantined_unresolved")
        self.assertEqual(conflict["disposition"], "quarantined_unresolved")


    def test_hrl_2026_11_19_remains_a_source_conflict(self):
        report = report_fixture()
        for repo in ("source-a", "source-b"):
            report["repositories"][repo]["files"][0]["symbol"] = "HRL"
            report["repositories"][repo]["files"][0]["path"] = "HRL_OHLCV.csv"
            report["repositories"][repo]["files"][0]["invalid_rows"] = []
        report["cross_source"]["conflicts"][0]["symbol"] = "HRL"
        report["cross_source"]["conflicts"][0]["date"] = "2026-11-19"
        ledger = build_ledger(report, expected_invalid_rows=0, expected_conflicts=1)
        conflict = ledger["exceptions"][0]
        self.assertEqual(conflict["disposition"], "quarantined_unresolved")
        self.assertNotIn("resolution_evidence", conflict)
        self.assertEqual(conflict["project_owner_context"]["project_designated"], {"open": "483.00", "low": "483.90"})
        self.assertEqual(conflict["project_owner_context"]["exchange_observed"], {"low": "480.00"})
        self.assertEqual(conflict["project_owner_context"]["sharehub_observed"], {"low": "480.00"})
        self.assertFalse(conflict["project_owner_context"]["canonical_promotion_allowed"])

    def test_rhgcl_nepse_evidence_is_field_scoped_and_omits_open(self):
        report = report_fixture()
        for repo in ("source-a", "source-b"):
            report["repositories"][repo]["files"][0]["symbol"] = "RHGCL"
            report["repositories"][repo]["files"][0]["path"] = "RHGCL_OHLCV.csv"
            report["repositories"][repo]["files"][0]["invalid_rows"] = []
        report["cross_source"]["conflicts"][0]["symbol"] = "RHGCL"
        report["cross_source"]["conflicts"][0]["date"] = "2026-11-19"
        ledger = build_ledger(report, expected_invalid_rows=0, expected_conflicts=1)
        conflict = ledger["exceptions"][0]
        self.assertEqual(conflict["disposition"], "resolved_with_nepse_field_evidence")
        self.assertEqual(conflict["resolution_evidence"]["supported_fields"]["volume"], "9054")
        self.assertEqual(conflict["resolution_evidence"]["omitted_fields"], ["open"])
        self.assertFalse(conflict["resolution_evidence"]["canonical_promotion_allowed"])

if __name__ == "__main__":
    unittest.main()
