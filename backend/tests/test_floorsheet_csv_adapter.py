import hashlib
import unittest

from app.floorsheet_csv_adapter import CsvFloorsheetMapping, parse_floorsheet_csv


MAPPING = CsvFloorsheetMapping({
    "trade_date": "Trade Date",
    "contract_id": "S.N.",
    "symbol": "Symbol",
    "buyer_broker_code": "Buyer",
    "seller_broker_code": "Seller",
    "quantity": "Qty.",
    "rate": "Rate",
    "amount": "Amount",
})


class FloorsheetCsvAdapterTests(unittest.TestCase):
    def test_explicit_mapping_parses_and_preserves_lineage(self):
        payload = (
            "Trade Date,S.N.,Symbol,Buyer,Seller,Qty.,Rate,Amount\n"
            "2026-11-24,1001,NABIL,11,42,10,100,1000\n"
        ).encode()
        result = parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 1)
        self.assertEqual(result["rows"][0].source_row_number, 2)
        self.assertEqual(result["rows"][0].source_payload_sha256, hashlib.sha256(payload).hexdigest())

    def test_missing_source_header_fails_closed(self):
        payload = b"date,id,symbol\n2026-11-24,1,NABIL\n"
        with self.assertRaisesRegex(ValueError, "mapped source headers absent"):
            parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)

    def test_bad_numeric_row_is_reported_not_silently_dropped(self):
        payload = (
            "Trade Date,S.N.,Symbol,Buyer,Seller,Qty.,Rate,Amount\n"
            "2026-11-24,1001,NABIL,11,42,not-a-number,100,1000\n"
        ).encode()
        result = parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)
        self.assertEqual(result["parsed_rows"], 0)
        self.assertEqual(result["rejected_rows"], 1)
        self.assertEqual(result["errors"][0]["source_row_number"], 2)

    def test_duplicate_headers_rejected(self):
        payload = (
            "Trade Date,S.N.,Symbol,Buyer,Seller,Qty.,Rate,Amount,Amount\n"
        ).encode()
        with self.assertRaisesRegex(ValueError, "duplicate source headers"):
            parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)

    def test_incomplete_mapping_rejected(self):
        with self.assertRaisesRegex(ValueError, "mapping missing"):
            CsvFloorsheetMapping({"symbol": "Symbol"})

    def test_unsupported_normalized_mapping_field_rejected(self):
        mapping = dict(MAPPING.columns)
        mapping["unknown_field"] = "Unknown"
        with self.assertRaisesRegex(ValueError, "unsupported normalized fields"):
            CsvFloorsheetMapping(mapping)

    def test_non_string_source_header_rejected(self):
        mapping = dict(MAPPING.columns)
        mapping["symbol"] = 123
        with self.assertRaisesRegex(ValueError, "nonblank strings"):
            CsvFloorsheetMapping(mapping)

    def test_non_bytes_payload_and_invalid_mapping_rejected(self):
        with self.assertRaisesRegex(ValueError, "payload must be bytes"):
            parse_floorsheet_csv("text", source_id="sample", mapping=MAPPING)
        with self.assertRaisesRegex(ValueError, "mapping must be"):
            parse_floorsheet_csv(b"a", source_id="sample", mapping=None)

    def test_newline_delimiter_and_blank_headers_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be a newline"):
            CsvFloorsheetMapping(dict(MAPPING.columns), delimiter="\\n")
        payload = b"Trade Date,S.N.,Symbol,Buyer,Seller,Qty.,Rate,Amount,\\n"
        with self.assertRaisesRegex(ValueError, "nonblank strings"):
            parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)

    def test_extra_unmapped_cells_are_reported(self):
        payload = (
            "Trade Date,S.N.,Symbol,Buyer,Seller,Qty.,Rate,Amount\n"
            "2026-11-24,1001,NABIL,11,42,10,100,1000,EXTRA\n"
        ).encode()
        result = parse_floorsheet_csv(payload, source_id="sample", mapping=MAPPING)
        self.assertEqual(result["rejected_rows"], 1)
        self.assertEqual(result["errors"][0]["error"], "extra_unmapped_columns")


if __name__ == "__main__":
    unittest.main()
