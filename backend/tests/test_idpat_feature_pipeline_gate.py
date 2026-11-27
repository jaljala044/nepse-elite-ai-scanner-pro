import unittest
from app.feature_pipeline import build_feature_snapshot


class IDPATFeaturePipelineGateTests(unittest.TestCase):
    def rows(self, count=6):
        days = [f"2026-01-{day:02d}" for day in range(1, count + 1)]
        result = []
        for index, day in enumerate(days):
            result.append({
                "record_id": f"AAA-{index}", "record_type": "ohlcv", "symbol": "AAA",
                "session_date": day, "open": 10 + index, "high": 12 + index,
                "low": 9 + index, "close": 11 + index, "volume": 1000 + index * 100,
                "available_at": "2026-01-10T12:00:00+05:45",
                "source_validation_status": "verified", "source_id": "primary-fixture",
                "source_payload_sha256": "a" * 64,
                "price_basis_status": "verified_unadjusted_no_actions",
                "corporate_action_status": "clear",
            })
        return days, result

    def snapshot(self, days, rows):
        return build_feature_snapshot(
            rows, "2026-01-11T12:00:00+05:45",
            expected_symbols=["AAA"], session_dates=days,
        )

    def test_quarantined_rows_withhold_idpat_candidate(self):
        days, rows = self.rows()
        rows[2]["row_status"] = "quarantined_unresolved"
        result = self.snapshot(days, rows)
        feature = result["idpat_features"]["AAA"]
        self.assertEqual(feature["status"], "input_contract_unverified")
        self.assertEqual(feature["events"], [])
        self.assertFalse(result["input_contracts"]["ohlcv"]["symbols"]["AAA"]["score_eligible"])

    def test_late_available_expected_session_withholds_idpat(self):
        days, rows = self.rows()
        rows[5]["available_at"] = "2026-01-12T12:00:00+05:45"
        result = self.snapshot(days, rows)
        feature = result["idpat_features"]["AAA"]
        self.assertEqual(feature["status"], "input_contract_unverified")
        self.assertEqual(feature["events"], [])
        self.assertEqual(feature["missing_expected_sessions"], [days[5]])

    def test_duplicate_session_withholds_idpat(self):
        days, rows = self.rows()
        duplicate = dict(rows[2], record_id="AAA-duplicate")
        rows.append(duplicate)
        result = self.snapshot(days, rows)
        feature = result["idpat_features"]["AAA"]
        self.assertEqual(feature["status"], "input_contract_unverified")
        self.assertEqual(feature["events"], [])
        self.assertTrue(result["input_contracts"]["ohlcv"]["symbols"]["AAA"]["duplicate_sessions"])

    def test_insufficient_warmup_remains_insufficient_evidence(self):
        days, rows = self.rows(count=4)
        result = self.snapshot(days, rows)
        feature = result["idpat_features"]["AAA"]
        self.assertEqual(feature["status"], "insufficient_evidence")
        self.assertIsNone(feature["score"])


if __name__ == "__main__":
    unittest.main()
