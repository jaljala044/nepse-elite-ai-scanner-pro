import unittest

from crosscheck_ohlcv_socrateai import compare_ohlcv, load_candidates, unmatched_classification


class SocrateAiCrosscheckTests(unittest.TestCase):
    def test_unmatched_external_outcomes_always_have_classification(self):
        self.assertEqual(unmatched_classification("not_published"), "external_file_not_published")
        self.assertEqual(unmatched_classification("symbol_not_in_external_file"), "symbol_not_in_external_file")
        self.assertEqual(unmatched_classification("download_error"), "external_download_error")

    def test_numeric_formatting_does_not_create_false_difference(self):
        result = compare_ohlcv(
            {"open": "179.70", "high": "193.8", "low": "179.70", "close": "193.80", "volume": "14812.0"},
            {"open": "179.7", "high": "193.80", "low": "179.7", "close": "193.8", "volume": "14812"},
        )
        self.assertEqual(result["status"], "full_match")
        self.assertEqual(result["differences"], {})

    def test_partial_match_reports_each_different_field(self):
        result = compare_ohlcv(
            {"open": "331", "high": "334.2", "low": "330.2", "close": "333", "volume": "26717"},
            {"open": "331", "high": "334.2", "low": "330", "close": "331.8", "volume": "105326"},
        )
        self.assertEqual(result["status"], "partial_match")
        self.assertEqual(set(result["differences"]), {"low", "close", "volume"})

    def test_candidates_include_invalid_rows_and_source_conflicts(self):
        audit = {
            "repositories": {
                "owner/a": {
                    "files": [{
                        "symbol": "API",
                        "invalid_rows": [{
                            "error": "bad OHLC",
                            "row": {"Date": "2026-11-19", "Open": "331", "High": "334.2",
                                    "Low": "330.2", "Close": "333", "Volume": "26717"},
                        }],
                    }]
                }
            },
            "cross_source": {
                "conflicts": [{
                    "symbol": "API", "date": "2026-11-19",
                    "source_rows": {
                        "owner/a": {"open": "331", "high": "334.2", "low": "330.2", "close": "333", "volume": "26717"},
                        "owner/b": {"open": "331", "high": "334.2", "low": "330", "close": "331.8", "volume": "105340"},
                    },
                }]
            },
        }
        result = load_candidates(audit)
        self.assertEqual(len(result), 1)
        item = result[("2026-11-19", "API")]
        self.assertEqual(set(item["source_rows"]), {"owner/a", "owner/b"})
        self.assertIn("cross_source_conflict", item["reasons"])


if __name__ == "__main__":
    unittest.main()
