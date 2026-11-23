import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi.testclient import TestClient

from app.main import app


class StrictCoverageApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "strict.duckdb"
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
        con.execute("CREATE TABLE reference_symbols(symbol VARCHAR)")
        con.execute("INSERT INTO reference_symbols VALUES ('AAA'), ('BBB'), ('CCC')")
        con.execute("CREATE TABLE reference_sessions(session_date DATE)")
        con.execute("INSERT INTO reference_sessions VALUES ('2026-01-05'), ('2026-01-06')")
        con.close()
        self.client = TestClient(app)

    def tearDown(self):
        self.temp.cleanup()

    def test_requires_verified_reference_tables_to_be_configured(self):
        with patch.dict(os.environ, {"NEPSE_DUCKDB_PATH": str(self.db)}, clear=False):
            os.environ.pop("NEPSE_SYMBOL_MASTER_TABLE", None)
            os.environ.pop("NEPSE_SESSION_CALENDAR_TABLE", None)
            response = self.client.get("/v3/audit/coverage/strict")
        self.assertEqual(response.status_code, 503)
        self.assertIn("no reference data will be guessed", response.text)

    def test_reports_per_symbol_calendar_gaps(self):
        config = {
            "NEPSE_DUCKDB_PATH": str(self.db),
            "NEPSE_SYMBOL_MASTER_TABLE": "reference_symbols",
            "NEPSE_SESSION_CALENDAR_TABLE": "reference_sessions",
        }
        with patch.dict(os.environ, config, clear=False):
            response = self.client.get("/v3/audit/coverage/strict")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["universe_symbols"], 3)
        self.assertEqual(body["calendar_sessions"], 2)
        self.assertEqual(body["expected_symbol_sessions"], 6)
        self.assertEqual(body["observed_symbol_sessions"], 3)
        self.assertEqual(body["overall_coverage_pct"], 50.0)
        ccc = next(row for row in body["results"] if row["symbol"] == "CCC")
        self.assertEqual(ccc["missing_sessions"], ["2026-01-05", "2026-01-06"])
        self.assertEqual(ccc["status"], "review")


if __name__ == "__main__":
    unittest.main()
