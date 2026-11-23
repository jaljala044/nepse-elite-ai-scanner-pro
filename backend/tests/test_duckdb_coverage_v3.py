import tempfile
import unittest
from datetime import date
from pathlib import Path

import duckdb

from app.duckdb_coverage_v3 import audit_duckdb_ohlcv


class DuckDBCoverageV3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "warehouse.duckdb"
        con = duckdb.connect(str(self.db))
        con.execute("CREATE SCHEMA ankit")
        con.execute("""CREATE TABLE ankit.eod_price (
            business_date DATE, symbol VARCHAR, open_price DOUBLE,
            high_price DOUBLE, low_price DOUBLE, close_price DOUBLE,
            total_traded_quantity BIGINT
        )""")
        con.execute("""INSERT INTO ankit.eod_price VALUES
            ('2026-01-05','AAA',10,12,9,11,1000),
            ('2026-01-06','AAA',11,13,10,12,1200),
            ('2026-01-05','BBB',20,22,19,21,2000)
        """)
        con.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_reads_warehouse_read_only_and_reports_coverage(self):
        report = audit_duckdb_ohlcv(self.db, target_universe_size=309)
        self.assertEqual(report["warehouse"]["source_table"], "ankit.eod_price")
        self.assertTrue(report["warehouse"]["read_only"])
        self.assertEqual(report["row_count_input"], 3)
        self.assertEqual(report["observed_symbols"], 2)
        self.assertEqual(report["expected_symbols"], 309)
        self.assertEqual(report["missing_symbol_count"], 307)
        self.assertFalse(report["session_calendar_supplied"])

    def test_as_of_cutoff_is_applied(self):
        report = audit_duckdb_ohlcv(self.db, as_of=date(2026, 1, 5))
        self.assertEqual(report["row_count_input"], 2)
        aaa = next(item for item in report["per_symbol"] if item["symbol"] == "AAA")
        self.assertEqual(aaa["latest_session"], "2026-01-05")

    def test_missing_database_is_explicit(self):
        with self.assertRaises(FileNotFoundError):
            audit_duckdb_ohlcv(Path(self.temp.name) / "missing.duckdb")


if __name__ == "__main__":
    unittest.main()
