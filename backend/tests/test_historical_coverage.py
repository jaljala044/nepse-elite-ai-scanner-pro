import tempfile
import unittest
from pathlib import Path

from nepse_shared_validation import ValidationRegistry
from app.historical_coverage import build_historical_coverage_report, build_cached_historical_coverage_report


def row(source, symbol, close, day="2026-11-24"):
    return {"source_id": source, "symbol": symbol, "session_date": day, "close": close}


class HistoricalCoverageTests(unittest.TestCase):
    def test_coverage_uses_only_supplied_expected_grid(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100")],
            expected_sessions=["2026-11-24", "2026-11-25"],
            expected_symbols=["NABIL", "NICA"])
        self.assertEqual(r["expected_symbol_session_keys"], 4)
        self.assertEqual(r["source_reports"]["A"]["covered_keys"], 1)
        self.assertEqual(r["source_reports"]["A"]["coverage_ratio"], "0.25")

    def test_cross_source_disagreement_flagged_without_preference(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("B", "NABIL", "101")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["cross_source_close_conflict_count"], 1)
        self.assertFalse(r["canonical_promotion_allowed"])

    def test_duplicate_rows_reported(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("A", "NABIL", "100")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(len(r["source_reports"]["A"]["duplicate_keys"]), 1)

    def test_missing_session_and_symbol_not_inferred(self):
        r = build_historical_coverage_report(
            [], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["union_missing_keys"], 1)
        self.assertFalse(r["unverified_weekday_inference_used"])

    def test_same_source_duplicate_difference_is_not_called_cross_source_conflict(self):
        r = build_historical_coverage_report(
            [row("A", "NABIL", "100"), row("A", "NABIL", "101")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["cross_source_close_conflict_count"], 0)
        self.assertEqual(len(r["source_reports"]["A"]["duplicate_keys"]), 1)

    def test_rows_outside_verified_grid_are_reported(self):
        r = build_historical_coverage_report(
            [row("A", "OUTSIDE", "100"), row("A", "NABIL", "100", "2026-11-23")],
            expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(r["source_reports"]["A"]["covered_keys"], 0)
        self.assertEqual(r["source_reports"]["A"]["unexpected_rows"], [
            {"session_date":"2026-11-23","symbol":"NABIL",
             "reason":"session_not_in_verified_expected_grid"},
            {"session_date":"2026-11-24","symbol":"OUTSIDE",
             "reason":"symbol_not_in_expected_universe"},
        ])

    def test_non_finite_or_non_positive_close_rejected(self):
        for value in ("NaN", "Infinity", "0", "-1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite positive"):
                    build_historical_coverage_report(
                        [row("A", "NABIL", value)],
                        expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])

    def test_empty_expected_grid_rejected(self):
        with self.assertRaisesRegex(ValueError, "verified expected"):
            build_historical_coverage_report([], expected_sessions=[], expected_symbols=["NABIL"])

    def test_identical_file_reuses_cached_coverage_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "a.csv", root / "b.csv"
            first.write_bytes(b"same source bytes")
            second.write_bytes(first.read_bytes())
            registry = ValidationRegistry(root / "cache.sqlite3")
            calls = []
            def load_records(path):
                calls.append(path)
                return [row("A", "NABIL", "100")]
            kwargs = dict(expected_sessions=["2026-11-24"], expected_symbols=["NABIL"],
                          load_records=load_records, registry=registry)
            a = build_cached_historical_coverage_report(first, **kwargs)
            b = build_cached_historical_coverage_report(second, **kwargs)
            self.assertFalse(a["cache_hit"])
            self.assertTrue(b["cache_hit"])
            self.assertEqual(a["report"], b["report"])
            self.assertEqual(len(calls), 1)

    def test_changed_expected_grid_invalidates_cached_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"same source bytes")
            registry = ValidationRegistry(root / "cache.sqlite3")
            calls = []
            def load_records(path):
                calls.append(path)
                return [row("A", "NABIL", "100")]
            common = dict(expected_symbols=["NABIL"], load_records=load_records, registry=registry)
            first = build_cached_historical_coverage_report(source, expected_sessions=["2026-11-24"], **common)
            second = build_cached_historical_coverage_report(source, expected_sessions=["2026-11-24", "2026-11-25"], **common)
            self.assertFalse(first["cache_hit"])
            self.assertFalse(second["cache_hit"])
            self.assertEqual(len(calls), 2)

    def test_changed_file_bytes_revalidate_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"first")
            registry = ValidationRegistry(root / "cache.sqlite3")
            calls = []
            def load_records(path):
                calls.append(path.read_bytes())
                return [row("A", "NABIL", "100")]
            kwargs = dict(expected_sessions=["2026-11-24"], expected_symbols=["NABIL"],
                          load_records=load_records, registry=registry)
            first = build_cached_historical_coverage_report(source, **kwargs)
            source.write_bytes(b"second")
            second = build_cached_historical_coverage_report(source, **kwargs)
            self.assertFalse(first["cache_hit"])
            self.assertFalse(second["cache_hit"])
            self.assertEqual(calls, [b"first", b"second"])
            self.assertFalse(second["report"]["coverage_report"]["canonical_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()

    def test_noncanonical_expected_session_dates_are_rejected(self):
        for value in ("20261124", "2026-W48-2", "2026-1-4", "2026/11/24"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "canonical YYYY-MM-DD"):
                    build_historical_coverage_report(
                        [], expected_sessions=[value], expected_symbols=["NABIL"])

    def test_noncanonical_record_dates_are_rejected(self):
        for value in ("20261124", "2026-W48-2", "2026-1-4", "2026/11/24"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid coverage input row"):
                    build_historical_coverage_report(
                        [row("A", "NABIL", "100", day=value)],
                        expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])

    def test_expected_symbols_must_be_nonempty_strings(self):
        for value in ("", "   ", None, 123):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "expected symbols"):
                    build_historical_coverage_report(
                        [], expected_sessions=["2026-11-24"], expected_symbols=[value])


    def test_native_date_objects_are_accepted_for_database_rows(self):
        from datetime import date
        record = {"source_id": "A", "symbol": "NABIL",
                  "session_date": date(2026, 11, 24), "close": "100"}
        report = build_historical_coverage_report(
            [record], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"])
        self.assertEqual(report["union_covered_keys"], 1)

    def test_cached_coverage_rejects_noncanonical_grid_before_cache_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"unchanged")
            registry = ValidationRegistry(root / "cache.sqlite3")
            with self.assertRaisesRegex(ValueError, "canonical YYYY-MM-DD"):
                build_cached_historical_coverage_report(
                    source, expected_sessions=["20261124"], expected_symbols=["NABIL"],
                    load_records=lambda path: [], registry=registry)

    def test_cached_coverage_rejects_invalid_expected_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"unchanged")
            registry = ValidationRegistry(root / "cache.sqlite3")
            with self.assertRaisesRegex(ValueError, "expected symbols"):
                build_cached_historical_coverage_report(
                    source, expected_sessions=["2026-11-24"], expected_symbols=[" "],
                    load_records=lambda path: [], registry=registry)

