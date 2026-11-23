import tempfile
import unittest
from pathlib import Path

import duckdb

from app.ankit_warehouse import load_ankit_warehouse

class AnkitWarehouseTests(unittest.TestCase):
    def _write_parquet(self, path: Path, query: str):
        path.parent.mkdir(parents=True,exist_ok=True)
        con=duckdb.connect()
        escaped=str(path).replace("'","''")
        con.execute(f"COPY ({query}) TO '{escaped}' (FORMAT PARQUET)")
        con.close()

    def test_load_keeps_eod_sources_separate_and_reconciles_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            raw=root/"raw"
            self._write_parquet(
                raw/"eod_history_ext"/"sharesansar.parquet",
                """SELECT
                    'sharesansar'::VARCHAR AS source,
                    'NABIL'::VARCHAR AS symbol,
                    DATE '2026-08-19' AS business_date,
                    500.0::DECIMAL(18,4) AS open_price,
                    510.0::DECIMAL(18,4) AS high_price,
                    495.0::DECIMAL(18,4) AS low_price,
                    505.0::DECIMAL(18,4) AS close_price,
                    1.0::DECIMAL(12,4) AS percent_change,
                    1000::BIGINT AS traded_quantity,
                    505000.0::DECIMAL(22,4) AS traded_amount,
                    CURRENT_TIMESTAMP AS ingested_at"""
            )
            self._write_parquet(
                raw/"eod_price"/"business_date=2026-08-19"/"part-0.parquet",
                """SELECT
                    DATE '2026-08-19' AS business_date,
                    'NABIL'::VARCHAR AS symbol,
                    1::INTEGER AS security_id,
                    'Nabil Bank'::VARCHAR AS security_name,
                    500.0::DECIMAL(18,4) AS open_price,
                    510.0::DECIMAL(18,4) AS high_price,
                    495.0::DECIMAL(18,4) AS low_price,
                    506.0::DECIMAL(18,4) AS close_price,
                    1000::BIGINT AS total_traded_quantity,
                    505000.0::DECIMAL(22,4) AS total_traded_value,
                    500.0::DECIMAL(18,4) AS previous_day_close_price,
                    520.0::DECIMAL(18,4) AS fifty_two_week_high,
                    400.0::DECIMAL(18,4) AS fifty_two_week_low,
                    CURRENT_TIMESTAMP AS last_updated_time,
                    505.0::DECIMAL(18,4) AS last_updated_price,
                    10::BIGINT AS total_trades,
                    505.0::DECIMAL(18,4) AS average_traded_price,
                    1000000000.0::DECIMAL(22,4) AS market_capitalization,
                    NULL::VARCHAR AS quality_flags,
                    CURRENT_TIMESTAMP AS ingested_at
                UNION ALL
                SELECT
                    DATE '2026-08-19' AS business_date,
                    'TEST'::VARCHAR AS symbol,
                    2::INTEGER AS security_id,
                    'Test Debenture'::VARCHAR AS security_name,
                    500.0::DECIMAL(18,4) AS open_price,
                    510.0::DECIMAL(18,4) AS high_price,
                    495.0::DECIMAL(18,4) AS low_price,
                    520.0::DECIMAL(18,4) AS close_price,
                    100::BIGINT AS total_traded_quantity,
                    52000.0::DECIMAL(22,4) AS total_traded_value,
                    500.0::DECIMAL(18,4) AS previous_day_close_price,
                    520.0::DECIMAL(18,4) AS fifty_two_week_high,
                    400.0::DECIMAL(18,4) AS fifty_two_week_low,
                    CURRENT_TIMESTAMP AS last_updated_time,
                    520.0::DECIMAL(18,4) AS last_updated_price,
                    1::BIGINT AS total_trades,
                    520.0::DECIMAL(18,4) AS average_traded_price,
                    1000000000.0::DECIMAL(22,4) AS market_capitalization,
                    'close_outside_range'::VARCHAR AS quality_flags,
                    CURRENT_TIMESTAMP AS ingested_at"""
            )
            db=root/"warehouse"/"nepse.duckdb"
            report=root/"reports"/"report.json"
            result=load_ankit_warehouse(raw,db,report)
            self.assertEqual(result["tables"]["eod_price"]["quality"]["rows"],2)
            self.assertEqual(result["tables"]["eod_price"]["quality"]["flagged_close_outside_range_rows"],1)
            self.assertEqual(result["tables"]["eod_price"]["quality"]["unflagged_ohlc_outlier_rows"],0)
            self.assertEqual(result["tables"]["eod_history_ext"]["quality"]["rows"],1)
            self.assertEqual(result["overlap_reconciliation"]["matched_symbol_dates"],1)
            self.assertEqual(result["overlap_reconciliation"]["exact_volume_matches"],1)
            self.assertEqual(result["overlap_reconciliation"]["exact_close_matches"],0)
            self.assertEqual(result["overlap_reconciliation"]["close_mismatch_count"],1)
            self.assertEqual(result["overlap_reconciliation"]["close_mismatch_rows"][0]["symbol"],"NABIL")
            self.assertEqual(result["overlap_reconciliation"]["close_mismatch_rows"][0]["absolute_difference"],"1.0000")
            con=duckdb.connect(str(db),read_only=True)
            schemas=con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='ankit' ORDER BY table_name"
            ).fetchall()
            con.close()
            self.assertEqual([row[0] for row in schemas],["eod_history_ext","eod_price"])
            self.assertTrue(report.exists())

if __name__=="__main__":
    unittest.main()
