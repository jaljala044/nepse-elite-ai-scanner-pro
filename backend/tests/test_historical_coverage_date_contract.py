import tempfile
import unittest
from datetime import date
from pathlib import Path

from nepse_shared_validation import ValidationRegistry
from app.historical_coverage import build_historical_coverage_report, build_cached_historical_coverage_report


class HistoricalCoverageDateContractTests(unittest.TestCase):
    def test_expected_sessions_require_canonical_iso_dates(self):
        for value in ("20261124", "2026-W48-2", "2026-1-4", "2026/11/24", "2026-02-30"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "canonical YYYY-MM-DD"):
                    build_historical_coverage_report(
                        [], expected_sessions=[value], expected_symbols=["NABIL"]
                    )

    def test_record_dates_require_canonical_iso_dates(self):
        for value in ("20261124", "2026-W48-2", "2026-1-4", "2026/11/24"):
            with self.subTest(value=value):
                row = {"session_date": value, "symbol": "NABIL", "source_id": "A", "close": "100"}
                with self.assertRaisesRegex(ValueError, "invalid coverage input row"):
                    build_historical_coverage_report(
                        [row], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"]
                    )

    def test_typed_date_is_allowed_for_database_record(self):
        row = {"session_date": date(2026, 11, 24), "symbol": "NABIL", "source_id": "A", "close": "100"}
        result = build_historical_coverage_report(
            [row], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"]
        )
        self.assertEqual(result["union_covered_keys"], 1)

    def test_expected_symbols_must_be_nonempty_strings(self):
        for value in ("", " ", None, 123):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "expected symbols"):
                    build_historical_coverage_report(
                        [], expected_sessions=["2026-11-24"], expected_symbols=[value]
                    )

    def test_cached_grid_rejects_noncanonical_date_before_cache_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"synthetic")
            registry = ValidationRegistry(root / "cache.sqlite3")
            with self.assertRaisesRegex(ValueError, "canonical YYYY-MM-DD"):
                build_cached_historical_coverage_report(
                    source, expected_sessions=["20261124"], expected_symbols=["NABIL"],
                    load_records=lambda path: [], registry=registry
                )

    def test_cached_grid_rejects_invalid_expected_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "history.csv"
            source.write_bytes(b"synthetic")
            registry = ValidationRegistry(root / "cache.sqlite3")
            with self.assertRaisesRegex(ValueError, "expected symbols"):
                build_cached_historical_coverage_report(
                    source, expected_sessions=["2026-11-24"], expected_symbols=[" "],
                    load_records=lambda path: [], registry=registry
                )

    def test_record_symbol_and_source_must_be_strings(self):
        for field in ("symbol", "source_id"):
            for value in (None, 123, []):
                with self.subTest(field=field, value=value):
                    row = {"session_date": "2026-11-24", "symbol": "NABIL", "source_id": "A", "close": "100"}
                    row[field] = value
                    with self.assertRaisesRegex(ValueError, "invalid coverage input row"):
                        build_historical_coverage_report(
                            [row], expected_sessions=["2026-11-24"], expected_symbols=["NABIL"]
                        )


if __name__ == "__main__":
    unittest.main()
