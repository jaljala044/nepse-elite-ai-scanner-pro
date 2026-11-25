import hashlib
import unittest

from app.floorsheet_source_profiles import (
    UREK_CANONICAL_COLUMNS,
    UREK_DECLARED_HEADERS,
    UREK_PINNED_REVISION,
    UREK_SOURCE_ONLY_HEADERS,
    review_urek_floorsheet_headers,
    urek_floorsheet_mapping,
)
from app.floorsheet_csv_adapter import parse_floorsheet_csv


class UrekFloorsheetSourceProfileTests(unittest.TestCase):
    def test_declared_header_set_matches_public_dataset_schema(self):
        review = review_urek_floorsheet_headers(UREK_DECLARED_HEADERS)
        self.assertTrue(review.valid)
        self.assertEqual(review.evidence_status,
                         "publisher_schema_declared_raw_header_not_yet_reviewed")
        self.assertEqual(review.missing_headers, ())
        self.assertEqual(review.unexpected_headers, ())

    def test_header_order_may_differ_but_field_identity_must_match(self):
        headers = tuple(reversed(UREK_DECLARED_HEADERS))
        self.assertTrue(review_urek_floorsheet_headers(headers).valid)

    def test_missing_extra_and_duplicate_headers_fail_closed(self):
        missing = review_urek_floorsheet_headers(UREK_DECLARED_HEADERS[:-1])
        self.assertFalse(missing.valid)
        self.assertIn("id", missing.missing_headers)

        extra = review_urek_floorsheet_headers(
            UREK_DECLARED_HEADERS + ("unexpected",)
        )
        self.assertFalse(extra.valid)
        self.assertEqual(extra.unexpected_headers, ("unexpected",))

        duplicate = review_urek_floorsheet_headers(
            UREK_DECLARED_HEADERS + ("buyer",)
        )
        self.assertFalse(duplicate.valid)
        self.assertEqual(duplicate.duplicate_headers, ("buyer",))

    def test_rejects_text_instead_of_header_sequence(self):
        with self.assertRaisesRegex(ValueError, "iterable of header strings"):
            review_urek_floorsheet_headers("contract_no,calculation_date")

    def test_explicit_mapping_keeps_contract_number_as_string(self):
        self.assertEqual(UREK_CANONICAL_COLUMNS["contract_id"], "contract_no")
        self.assertEqual(UREK_PINNED_REVISION,
                         "11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0")
        self.assertEqual(set(UREK_SOURCE_ONLY_HEADERS), {"time", "sector", "id"})

        raw = (
            "contract_no,calculation_date,time,stock_symbol,sector,buyer,seller,"
            "quantity,rate,amount,id\n"
            "000123456789,2026-08-26,,TEST,Hydro Power,12,34,10,25.5,255,987654\n"
        ).encode("utf-8")
        parsed = parse_floorsheet_csv(
            raw,
            source_id="urekmazino69/Nepse-floorsheet-and-indices@"
                      + UREK_PINNED_REVISION + "/floorsheet/2026-08-26.csv",
            mapping=urek_floorsheet_mapping(),
        )
        self.assertEqual(parsed["parsed_rows"], 1)
        self.assertEqual(parsed["rejected_rows"], 0)
        self.assertFalse(parsed["source_specific_mapping_verified"])
        self.assertEqual(parsed["source_payload_sha256"], hashlib.sha256(raw).hexdigest())
        row = parsed["rows"][0]
        self.assertEqual(row.contract_id, "000123456789")
        self.assertEqual(row.trade_date, "2026-08-26")
        self.assertEqual(row.symbol, "TEST")
        self.assertEqual(row.buyer_broker_code, "12")
        self.assertEqual(row.seller_broker_code, "34")
        self.assertEqual(str(row.amount), "255")


if __name__ == "__main__":
    unittest.main()
