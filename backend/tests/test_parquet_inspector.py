import tempfile
import unittest
from pathlib import Path

import duckdb

from app.parquet_inspector import inspect_directory, inspect_one, sql_path

class ParquetInspectorTests(unittest.TestCase):
    def test_inspects_schema_rows_dates_and_nulls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            table=root/"eod_price"
            table.mkdir()
            path=table/"sample.parquet"
            con=duckdb.connect()
            con.execute(f"""
                COPY (
                    SELECT DATE '2026-11-20' AS business_date,
                           'NABIL'::VARCHAR AS symbol,
                           10.0::DOUBLE AS open,
                           12.0::DOUBLE AS high,
                           9.0::DOUBLE AS low,
                           11.0::DOUBLE AS close,
                           100::BIGINT AS volume,
                           NULL::VARCHAR AS note
                ) TO {sql_path(path)} (FORMAT PARQUET)
            """)
            con.close()
            result=inspect_directory(root)
            self.assertEqual(result["files_inspected"],1)
            self.assertEqual(result["files_failed"],0)
            record=result["files"][0]
            self.assertEqual(record["row_count"],1)
            self.assertEqual(record["date_ranges"]["business_date"]["min"],"2026-11-20")
            self.assertEqual(record["null_counts"]["note"],1)
            self.assertIn("eod_price",result["tables"])

if __name__=="__main__":
    unittest.main()
