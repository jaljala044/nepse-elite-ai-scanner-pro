import csv
import json
import tempfile
import unittest
from pathlib import Path

from audit_issue5_source_archive_coverage import build_report


class Issue5FullSourceCoverageTests(unittest.TestCase):
    def test_gaps_are_reported_but_not_called_missing_trades(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = {
                "repositories": {
                    "jaljala044/nepse-smc-data": {
                        "commit_sha": "a" * 40, "files_audited": 1, "file_count": 1,
                        "total_rows": 2, "duplicate_date_count": 0,
                        "out_of_order_transitions": 0, "invalid_row_count": 0,
                        "download_errors": [],
                        "files": [{"symbol": "ABC", "first_date": "2026-01-01",
                                   "last_date": "2026-01-03"}],
                        "date_coverage": [
                            {"date": "2026-01-01", "symbols": ["ABC"]},
                            {"date": "2026-01-03", "symbols": ["ABC"]},
                        ],
                    },
                    "jaljala044/nepse-history-starter": {
                        "commit_sha": "b" * 40, "files_audited": 1, "file_count": 1,
                        "total_rows": 2, "duplicate_date_count": 0,
                        "out_of_order_transitions": 0, "invalid_row_count": 0,
                        "download_errors": [],
                        "files": [{"symbol": "ABC", "first_date": "2026-01-01",
                                   "last_date": "2026-01-03"}],
                        "date_coverage": [
                            {"date": "2026-01-01", "symbols": ["ABC"]},
                            {"date": "2026-01-03", "symbols": ["ABC"]},
                        ],
                    },
                }
            }
            audit_path = root / "audit.json"
            audit_path.write_text(json.dumps(audit), encoding="utf-8")
            calendar_path = root / "calendar.csv"
            calendar_path.write_text(
                "date,status\n2026-01-01,project_accepted_open\n"
                "2026-01-02,project_accepted_open\n2026-01-03,verified_closed\n",
                encoding="utf-8",
            )
            universe_path = root / "universe.csv"
            universe_path.write_text(
                "symbol,instrument_type,status\nABC,Equity,Active\nFUND,Mutual Fund,Active\n",
                encoding="utf-8",
            )
            report, gaps = build_report(audit_path, calendar_path, universe_path)
            self.assertEqual(report["active_equity_count"], 1)
            self.assertEqual(report["unclassified_gap_count"], 2)
            self.assertEqual({g["trade_date"] for g in gaps}, {"2026-01-02"})
            self.assertTrue(all(g["gap_status"].startswith("UNCLASSIFIED") for g in gaps))
            self.assertFalse(report["canonical_or_training_promotion"])

    def test_duplicate_calendar_date_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = {"repositories": {
                "jaljala044/nepse-smc-data": {}, "jaljala044/nepse-history-starter": {}
            }}
            ap = root / "audit.json"; ap.write_text(json.dumps(audit))
            cp = root / "calendar.csv"
            cp.write_text("date,status\n2026-01-01,project_accepted_open\n2026-01-01,project_accepted_open\n")
            up = root / "universe.csv"; up.write_text("symbol,instrument_type,status\nABC,Equity,Active\n")
            with self.assertRaisesRegex(ValueError, "canonical and unique"):
                build_report(ap, cp, up)


    def _minimal_inputs(self, root):
        audit = {"repositories": {}}
        for repository in (
            "jaljala044/nepse-smc-data",
            "jaljala044/nepse-history-starter",
        ):
            audit["repositories"][repository] = {
                "commit_sha": "a" * 40, "files_audited": 1, "file_count": 1,
                "total_rows": 2, "duplicate_date_count": 0,
                "out_of_order_transitions": 0, "invalid_row_count": 0,
                "download_errors": [],
                "files": [{"symbol": "ABC", "first_date": "2026-01-01",
                           "last_date": "2026-01-03"}],
                "date_coverage": [
                    {"date": "2026-01-01", "symbols": ["ABC"]},
                    {"date": "2026-01-03", "symbols": ["ABC"]},
                ],
            }
        audit_path = root / "audit.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        calendar_path = root / "calendar.csv"
        calendar_path.write_text(
            "date,status\n2026-01-01,project_accepted_open\n"
            "2026-01-02,project_accepted_open\n2026-01-03,verified_closed\n",
            encoding="utf-8",
        )
        universe_path = root / "universe.csv"
        universe_path.write_text(
            "symbol,instrument_type,status\nABC,Equity,Active\n",
            encoding="utf-8",
        )
        return audit, audit_path, calendar_path, universe_path

    def test_duplicate_date_coverage_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"].append(
                {"date": "2026-01-01", "symbols": ["ABC"]}
            )
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate date coverage key"):
                build_report(ap, cp, up)

    def test_unknown_symbol_in_date_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"][0]["symbols"].append("GHOST")
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown source symbol"):
                build_report(ap, cp, up)

    def test_observed_date_outside_source_file_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"].append(
                {"date": "2026-01-04", "symbols": ["ABC"]}
            )
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside file range"):
                build_report(ap, cp, up)

    def test_duplicate_active_equity_symbol_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, ap, cp, up = self._minimal_inputs(root)
            up.write_text(
                "symbol,instrument_type,status\nABC,Equity,Active\nabc,Equity,Active\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "active equity symbols must be unique"):
                build_report(ap, cp, up)

    def test_nonzero_duplicate_source_date_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["duplicate_date_count"] = 1
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate source dates remain"):
                build_report(ap, cp, up)

    def test_non_string_coverage_symbol_is_rejected_without_type_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"][0]["symbols"] = [{"bad": "symbol"}]
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid symbol in date coverage"):
                build_report(ap, cp, up)

    def test_blank_coverage_symbol_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"][0]["symbols"] = [" "]
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid symbol in date coverage"):
                build_report(ap, cp, up)

    def test_case_normalized_duplicate_coverage_symbols_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"][0]["symbols"] = ["ABC", "abc"]
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate symbol in date coverage"):
                build_report(ap, cp, up)

    def test_non_list_date_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"] = {}
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "date coverage must be a list"):
                build_report(ap, cp, up)

    def test_non_object_date_coverage_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["date_coverage"][0] = []
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid date coverage row"):
                build_report(ap, cp, up)

    def test_non_object_source_file_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["files"][0] = "ABC"
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid source file entry"):
                build_report(ap, cp, up)

    def test_blank_source_file_symbol_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            audit["repositories"]["jaljala044/nepse-smc-data"]["files"][0]["symbol"] = " "
            ap.write_text(json.dumps(audit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing source symbol"):
                build_report(ap, cp, up)

    def test_universe_null_fields_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); audit, ap, cp, up = self._minimal_inputs(root)
            up.write_text("symbol,instrument_type,status\nABC,Equity,Active\n,Equity,Active\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "active equity symbol must be nonblank"):
                build_report(ap, cp, up)


if __name__ == "__main__":
    unittest.main()
