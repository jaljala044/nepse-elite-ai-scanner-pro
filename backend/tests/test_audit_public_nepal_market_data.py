import unittest

from audit_public_nepal_market_data import audit_symbol_csv


HEADER = b"published_date,open,high,low,close,per_change,traded_quantity,traded_amount,status\n"


class PublicNepalMarketDataAuditTests(unittest.TestCase):
    def test_valid_rows_and_normal_date_range(self):
        data = HEADER + (
            b"2024-01-02,10,11,9,10.5,nan,100,1050,A\n"
            b"2024-01-03,10.5,12,10,11,4.76,200,2200,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["invalid_ohlc"], 0)
        self.assertEqual(result["first_date"], "2024-01-02")
        self.assertEqual(result["last_date"], "2024-01-03")

    def test_duplicate_date_and_out_of_order_are_detected(self):
        data = HEADER + (
            b"2024-01-03,10,11,9,10,0,100,1000,A\n"
            b"2024-01-03,10,11,9,10,0,100,1000,A\n"
            b"2024-01-02,10,11,9,10,0,100,1000,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["duplicate_dates"], 1)
        self.assertEqual(result["out_of_order_transitions"], 1)

    def test_ohlc_bounds_and_fractional_volume_are_detected(self):
        data = HEADER + (
            b"2024-01-02,10,9,8,10,0,100.5,1000,A\n"
        )
        result = audit_symbol_csv(data, "TEST", "data/nepse/TEST.csv")
        self.assertEqual(result["invalid_ohlc"], 1)
        self.assertEqual(result["fractional_volume"], 1)
        self.assertEqual(result["valid_rows"], 0)

    def test_header_mismatch_fails_closed(self):
        result = audit_symbol_csv(
            b"date,open,high,low,close,volume\n2024-01-02,10,11,9,10,100\n",
            "TEST", "data/nepse/TEST.csv",
        )
        self.assertIn("header_mismatch", result)
        self.assertEqual(result["rows"], 0)


if __name__ == "__main__":
    unittest.main()
