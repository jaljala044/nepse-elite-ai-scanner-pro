import unittest
from app.universe_snapshot import validate_universe_snapshot


class UniverseSnapshotTests(unittest.TestCase):
    def snapshot(self):
        return {
            "source_id": "NEPSE-LIST-2026-11-25",
            "source_url": "https://www.nepalstock.com.np/stocklist",
            "retrieved_at_utc": "2026-11-25T00:00:00Z",
            "raw_payload_sha256": "a" * 64,
            "snapshot_as_of": "2026-11-25",
            "records": [
                {"security_id":"S1","symbol":"AAA","instrument_type":"equity","status":"active",
                 "target_in_scope":True,"valid_from":"2020-01-01","valid_to":None},
                {"security_id":"S2","symbol":"BBB","instrument_type":"equity","status":"active",
                 "target_in_scope":True,"valid_from":"2021-01-01","valid_to":None},
                {"security_id":"F1","symbol":"FUND1","instrument_type":"mutual_fund","status":"active",
                 "target_in_scope":True,"valid_from":"2022-01-01","valid_to":None},
                {"security_id":"D1","symbol":"DEBT1","instrument_type":"non_convertible_debenture","status":"active",
                 "target_in_scope":False,"valid_from":"2020-01-01","valid_to":None},
            ],
        }

    def test_exact_target_counts_and_provenance_pass(self):
        result = validate_universe_snapshot(self.snapshot(), expected_equities=2, expected_mutual_funds=1)
        self.assertTrue(result["manifest_verified"])
        self.assertFalse(result["promotion_allowed"])
        self.assertEqual(result["target_security_count"], 3)

    def test_target_count_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "target universe count mismatch"):
            validate_universe_snapshot(self.snapshot())

    def test_non_official_source_rejected(self):
        item = self.snapshot()
        item["source_url"] = "https://example.com/stocklist"
        with self.assertRaisesRegex(ValueError, "approved official"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_invalid_payload_hash_rejected(self):
        item = self.snapshot()
        item["raw_payload_sha256"] = "missing"
        with self.assertRaisesRegex(ValueError, "64-character hex"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_suspended_target_rejected(self):
        item = self.snapshot()
        item["records"][0]["status"] = "suspended"
        with self.assertRaisesRegex(ValueError, "only active equity"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_duplicate_target_symbol_rejected(self):
        item = self.snapshot()
        item["records"][1]["symbol"] = "AAA"
        with self.assertRaisesRegex(ValueError, "duplicate target"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_promoter_share_must_remain_outside_target_universe(self):
        item = self.snapshot()
        item["records"].append({
            "security_id": "P1", "symbol": "HIDCLP", "instrument_type": "promoter_share",
            "status": "active", "target_in_scope": False,
            "valid_from": "2020-01-01", "valid_to": None,
        })
        result = validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)
        self.assertEqual(result["target_security_count"], 3)
        self.assertTrue(result["manifest_verified"])
        item["records"][-1]["target_in_scope"] = True
        with self.assertRaisesRegex(ValueError, "only active equity/mutual_fund"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_non_object_record_rejected(self):
        item = self.snapshot()
        item["records"][0] = None
        with self.assertRaisesRegex(ValueError, "expected object"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_non_string_symbol_rejected(self):
        item = self.snapshot()
        item["records"][0]["symbol"] = 123
        with self.assertRaisesRegex(ValueError, "symbol must be a nonblank string"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_non_string_instrument_type_rejected(self):
        item = self.snapshot()
        item["records"][0]["instrument_type"] = []
        with self.assertRaisesRegex(ValueError, "unknown instrument_type"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_source_url_credentials_and_nonstandard_port_rejected(self):
        for url in (
            "https://user@www.nepalstock.com.np/stocklist",
            "https://www.nepalstock.com.np:8443/stocklist",
        ):
            with self.subTest(url=url):
                item = self.snapshot()
                item["source_url"] = url
                with self.assertRaisesRegex(ValueError, "approved official"):
                    validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_non_iso_snapshot_date_rejected(self):
        item = self.snapshot()
        item["snapshot_as_of"] = "20261125"
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)

    def test_naive_retrieval_timestamp_rejected(self):
        item = self.snapshot()
        item["retrieved_at_utc"] = "2026-11-25T00:00:00"
        with self.assertRaisesRegex(ValueError, "UTC timezone"):
            validate_universe_snapshot(item, expected_equities=2, expected_mutual_funds=1)


if __name__ == "__main__":
    unittest.main()
