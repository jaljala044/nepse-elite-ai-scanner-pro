import hashlib
import unittest

from app.floorsheet_source_profiles import (
    UREK_CANONICAL_COLUMNS,
    UREK_DECLARED_HEADERS,
    UREK_PINNED_REVISION,
    UREK_SOURCE_ONLY_HEADERS,
    review_urek_floorsheet_headers,
    urek_floorsheet_mapping,
    SAMIR_CANONICAL_COLUMNS,
    SAMIR_DECLARED_HEADERS,
    SAMIR_PINNED_COMMIT,
    SAMIR_RAW_SHA256,
    SAMIR_SOURCE_ONLY_HEADERS,
    review_samir_merolagani_headers,
    samir_merolagani_capture_mapping,
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


class SamirMerolaganiCaptureProfileTests(unittest.TestCase):
    def test_exact_observed_header_and_capture_date_warning(self):
        review = review_samir_merolagani_headers(SAMIR_DECLARED_HEADERS)
        self.assertTrue(review.valid)
        self.assertEqual(
            review.evidence_status,
            "raw_header_observed_capture_date_semantics_unverified",
        )
        self.assertEqual(SAMIR_PINNED_COMMIT, "e6160adc6bdf3d19562167388e3d9d4f645c455a")
        self.assertEqual(
            SAMIR_RAW_SHA256,
            "2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55",
        )
        self.assertEqual(set(SAMIR_SOURCE_ONLY_HEADERS), {"sn"})
        self.assertEqual(SAMIR_CANONICAL_COLUMNS["contract_id"], "contract_no")

    def test_header_mismatch_and_duplicate_fail_closed(self):
        missing = review_samir_merolagani_headers(SAMIR_DECLARED_HEADERS[:-1])
        self.assertFalse(missing.valid)
        self.assertIn("amount", missing.missing_headers)
        duplicate = review_samir_merolagani_headers(SAMIR_DECLARED_HEADERS + ("buyer",))
        self.assertFalse(duplicate.valid)
        self.assertEqual(duplicate.duplicate_headers, ("buyer",))

    def test_contract_date_maps_from_capture_date_only_provisionally(self):
        raw = (
            "date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-24,1,2026112405013267,BBC,58,11,10,3878.00,38780.00\n"
        ).encode("utf-8")
        parsed = parse_floorsheet_csv(
            raw,
            source_id="SamirWagle/Nepse-All-Scraper@"
                      + SAMIR_PINNED_COMMIT + "/data/floorsheet/floorsheet_2026-11-24.csv",
            mapping=samir_merolagani_capture_mapping(),
        )
        self.assertEqual(parsed["parsed_rows"], 1)
        self.assertEqual(parsed["rejected_rows"], 0)
        self.assertFalse(parsed["source_specific_mapping_verified"])
        contract = parsed["rows"][0]
        self.assertEqual(contract.trade_date, "2026-11-24")
        self.assertEqual(contract.contract_id, "2026112405013267")
        self.assertEqual(contract.symbol, "BBC")
        self.assertEqual(contract.buyer_broker_code, "58")
        self.assertEqual(str(contract.amount), "38780.00")



if __name__ == "__main__":
    unittest.main()


class SocrateAIFloorsheetSourceProfileTests(unittest.TestCase):
    def test_exact_pinned_schema_and_unverified_lineage_status(self):
        from app.floorsheet_source_profiles import (
            SOCRATEAI_BLOB_SHA1, SOCRATEAI_CANONICAL_COLUMNS,
            SOCRATEAI_DECLARED_HEADERS, SOCRATEAI_PINNED_COMMIT,
            SOCRATEAI_RAW_SIZE_BYTES, review_socrateai_floorsheet_headers,
        )
        review = review_socrateai_floorsheet_headers(SOCRATEAI_DECLARED_HEADERS)
        self.assertTrue(review.valid)
        self.assertEqual(
            review.evidence_status,
            "pinned_header_profile_lineage_and_completeness_unverified",
        )
        self.assertEqual(SOCRATEAI_PINNED_COMMIT,
                         "cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3")
        self.assertEqual(SOCRATEAI_BLOB_SHA1,
                         "e7150873219d66a21345df2dfbd78f6c5a4b1152")
        self.assertEqual(SOCRATEAI_RAW_SIZE_BYTES, 3058892)
        self.assertEqual(SOCRATEAI_CANONICAL_COLUMNS["contract_id"], "transaction")

    def test_schema_mismatch_and_duplicate_headers_fail_closed(self):
        from app.floorsheet_source_profiles import (
            SOCRATEAI_DECLARED_HEADERS, review_socrateai_floorsheet_headers,
        )
        missing = review_socrateai_floorsheet_headers(SOCRATEAI_DECLARED_HEADERS[:-1])
        self.assertFalse(missing.valid)
        self.assertIn("date", missing.missing_headers)
        duplicate = review_socrateai_floorsheet_headers(
            SOCRATEAI_DECLARED_HEADERS + ("buyer",)
        )
        self.assertFalse(duplicate.valid)
        self.assertEqual(duplicate.duplicate_headers, ("buyer",))

    def test_pinned_schema_parses_without_promoting_source_trust(self):
        from app.floorsheet_source_profiles import (
            SOCRATEAI_PINNED_COMMIT, socrateai_floorsheet_mapping,
        )
        raw = (
            "transaction,symbol,buyer,seller,quantity,rate,amount,date\\n"
            "2026112405013267,BBC,58,11,10,3878.00,38780.00,2026-11-24\\n"
        ).encode("utf-8")
        parsed = parse_floorsheet_csv(
            raw,
            source_id="socrateai-official/nepse-open-data@"
                      + SOCRATEAI_PINNED_COMMIT
                      + "/floorsheet/floorsheet_2026-11-24.csv",
            mapping=socrateai_floorsheet_mapping(),
        )
        self.assertEqual(parsed["parsed_rows"], 1)
        self.assertEqual(parsed["rejected_rows"], 0)
        self.assertFalse(parsed["source_specific_mapping_verified"])
        row = parsed["rows"][0]
        self.assertEqual(row.trade_date, "2026-11-24")
        self.assertEqual(row.contract_id, "2026112405013267")
        self.assertEqual(row.symbol, "BBC")
        self.assertEqual(row.buyer_broker_code, "58")
        self.assertEqual(str(row.amount), "38780.00")
