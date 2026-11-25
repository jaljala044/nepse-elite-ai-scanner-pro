import unittest
from app.instrument_manifest import validate_instrument_manifest


def row(i, kind="equity"):
    return {"security_id": f"SEC{i}", "symbol": f"SYM{i}", "instrument_type": kind,
            "status": "active", "valid_from": "2020-01-01", "valid_to": None,
            "evidence_id": f"E{i}", "source_id": "official-register",
            "source_tier": "primary", "source_record_id": f"R{i}"}


class InstrumentManifestTests(unittest.TestCase):
    def test_empty_manifest_does_not_pass_target_counts(self):
        result = validate_instrument_manifest([], as_of="2026-11-25")
        self.assertFalse(result["manifest_verified"])
        self.assertFalse(result["promotion_allowed"])
        self.assertEqual(result["active_counts_by_type"], {})

    def test_target_counts_and_primary_evidence_pass(self):
        records = [row(i) for i in range(281)] + [row(1000+i, "mutual_fund") for i in range(47)]
        result = validate_instrument_manifest(records, as_of="2026-11-25")
        self.assertTrue(result["manifest_verified"])
        self.assertEqual(result["active_target_rows"], 328)

    def test_suspended_and_delisted_not_counted_active(self):
        r = row(1)
        r["status"] = "suspended"
        result = validate_instrument_manifest([r], as_of="2026-11-25")
        self.assertEqual(result["active_target_rows"], 0)

    def test_duplicate_active_symbol_rejected(self):
        a, b = row(1), row(2)
        b["symbol"] = a["symbol"]
        result = validate_instrument_manifest([a, b], as_of="2026-11-25",
                                              require_primary_evidence=False)
        self.assertTrue(result["duplicate_active_symbols"])

    def test_non_primary_evidence_blocks_promotion(self):
        r = row(1)
        r["source_tier"] = "secondary"
        result = validate_instrument_manifest([r], as_of="2026-11-25")
        self.assertFalse(result["promotion_allowed"])

    def test_future_instrument_not_active_as_of(self):
        r = row(1)
        r["valid_from"] = "2027-01-01"
        result = validate_instrument_manifest([r], as_of="2026-11-25")
        self.assertEqual(result["active_target_rows"], 0)


if __name__ == "__main__":
    unittest.main()
