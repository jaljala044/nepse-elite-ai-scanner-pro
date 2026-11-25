import tempfile
import unittest
from pathlib import Path

import duckdb

from app.coverage_audit import audit_coverage


class CoverageAuditTests(unittest.TestCase):
    def test_coverage_missing_duplicate_and_invalid_rows_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "fixture.duckdb")
            con = duckdb.connect(db)
            con.execute("""CREATE TABLE daily_bars (
                symbol VARCHAR, date DATE, open DOUBLE, high DOUBLE,
                low DOUBLE, close DOUBLE, volume BIGINT)""")
            con.execute("""INSERT INTO daily_bars VALUES
                ('AAA','2025-01-02',10,12,9,11,100),
                ('AAA','2025-01-03',11,13,10,12,120),
                ('AAA','2025-01-03',11,13,10,12,120),
                ('BBB','2025-01-02',20,19,18,19,100)""")
            con.execute("CREATE TABLE symbol_master(symbol VARCHAR)")
            con.execute("INSERT INTO symbol_master VALUES ('AAA'),('BBB'),('CCC')")
            con.execute("CREATE TABLE exchange_calendar(session_date DATE)")
            con.execute("""INSERT INTO exchange_calendar VALUES
                ('2025-01-02'),('2025-01-03'),('2025-01-06')""")
            con.close()

            result = audit_coverage(db, "daily_bars", "symbol_master", "exchange_calendar")
            self.assertEqual(result["universe_symbols"], 3)
            self.assertEqual(result["calendar_sessions"], 2)
            self.assertEqual(result["expected_symbol_sessions"], 6)
            self.assertEqual(result["observed_symbol_sessions"], 3)
            self.assertEqual(result["overall_coverage_pct"], 50.0)
            by_symbol = {x["symbol"]: x for x in result["results"]}
            self.assertEqual(by_symbol["AAA"]["duplicate_sessions"], ["2025-01-03"])
            self.assertEqual(by_symbol["BBB"]["invalid_ohlcv_sessions"], ["2025-01-02"])
            self.assertEqual(by_symbol["CCC"]["missing_sessions"], ["2025-01-02", "2025-01-03"])

    def test_unsafe_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_coverage(":memory:", "daily_bars; DROP TABLE x", "master", "calendar")


if __name__ == "__main__":
    unittest.main()
