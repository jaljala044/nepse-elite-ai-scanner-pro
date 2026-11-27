import unittest
from unittest.mock import patch

from scripts.build_ohlcv_exception_ledger import build, USER_AUTHORITATIVE_RESOLUTIONS


class LedgerBuilderTests(unittest.TestCase):
    def fixture(self):
        repos = {
            "jaljala044/nepse-smc-data": {
                "commit_sha": "a" * 40, "tree_sha": "b" * 40,
                "files": [{"symbol": "ABC", "path": "data/ABC.csv",
                    "sha256": "c" * 64, "invalid_rows": [{"line": 2,
                    "error": "high below close", "row": {"Date": "2026-01-01",
                    "Open": "10", "High": "9", "Low": "8", "Close": "10", "Volume": "1"}}]}]},
            "jaljala044/nepse-history-starter": {
                "commit_sha": "d" * 40, "tree_sha": "e" * 40,
                "files": [{"symbol": "ABC", "path": "data/ABC.csv",
                    "sha256": "f" * 64, "invalid_rows": []}]},
        }
        archive = {"generated_at_utc": "2026-01-02T00:00:00+00:00",
            "repositories": repos, "cross_source": {"conflicts": [{
                "symbol": "ABC", "date": "2026-01-01", "source_rows": {
                    "jaljala044/nepse-smc-data": {"close": "10"},
                    "jaljala044/nepse-history-starter": {"close": "11"}}}]}}
        external = {"records": [{"symbol": "ABC", "date": "2026-01-01",
            "classification": "partial_or_conflicting"}]}
        return archive, external

    def test_build_preserves_both_sides_and_quarantines(self):
        archive, external = self.fixture()
        with patch("scripts.build_ohlcv_exception_ledger.EXPECTED",
                   {"invalid_ohlc": 1, "cross_source_ohlcv_conflict": 1}):
            result = build(archive, external, 123, "a" * 64)
        self.assertEqual(result["counts"]["total_exception_records"], 2)
        conflict = next(r for r in result["exceptions"]
                        if r["exception_type"] == "cross_source_ohlcv_conflict")
        self.assertEqual(len(conflict["source_evidence"]), 2)
        self.assertIsNone(conflict["source_evidence"]["jaljala044/nepse-smc-data"]["source_csv_line"])

    def test_build_fails_closed_when_audit_counts_drift(self):
        archive, external = self.fixture()
        with self.assertRaisesRegex(ValueError, "pinned audit counts changed"):
            build(archive, external, 123, "a" * 64)


    def test_user_authoritative_july_2025_rows_are_resolved_without_promotion(self):
        expected = {
            "BGWT": ("940.00", "992.00", "933.40", "957.17", "14028", "13256345.00"),
            "MEHL": ("471.10", "480.50", "460.00", "475.63", "29753", "14008898.10"),
            "RAWA": ("796.00", "811.00", "780.30", "796.90", "3165", "2515662.50"),
            "RHGCL": ("346.70", "362.00", "341.40", "357.05", "296715", "103872614.40"),
            "ULHC": ("509.00", "515.00", "495.00", "510.75", "32288", "16273342.10"),
        }
        self.assertEqual(set(USER_AUTHORITATIVE_RESOLUTIONS),
                         {(symbol, "2025-07-28") for symbol in expected})
        for symbol, values in expected.items():
            row = USER_AUTHORITATIVE_RESOLUTIONS[(symbol, "2025-07-28")]
            self.assertEqual((row["open"], row["high"], row["low"], row["close"],
                              row["volume"], row["turnover_npr"]), values)
            self.assertIn("trades", row)

        archive, external = self.fixture()
        archive["cross_source"]["conflicts"][0]["symbol"] = "BGWT"
        archive["cross_source"]["conflicts"][0]["date"] = "2025-07-28"
        for meta in archive["repositories"].values():
            meta["files"][0]["symbol"] = "BGWT"
        with patch("scripts.build_ohlcv_exception_ledger.EXPECTED",
                   {"invalid_ohlc": 1, "cross_source_ohlcv_conflict": 1}):
            result = build(archive, external, 123, "a" * 64)
        conflict = next(r for r in result["exceptions"]
                        if r["exception_type"] == "cross_source_ohlcv_conflict")
        self.assertEqual(conflict["disposition"], "resolved_with_user_authoritative_evidence")
        self.assertFalse(conflict["resolution_evidence"]["canonical_promotion_allowed"])
        self.assertFalse(conflict["resolution_evidence"]["raw_source_rows_modified"])
        self.assertEqual(len(conflict["source_evidence"]), 2)

if __name__ == "__main__":
    unittest.main()
