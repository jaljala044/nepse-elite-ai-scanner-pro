import unittest
from datetime import date, timedelta

from app.idpat_accumulation_distribution import analyze_idpat_accumulation_distribution
from app.idpat_price_volume import IDPATError


def make_snapshot(last_overrides=None, volume=1000):
    bars = []
    # Stable reference period followed by a compressed, lower-volume range.
    for i in range(40):
        if i < 20:
            base = 100 + (i % 4) * 0.5
            high, low, opn, close = base + 1, base - 1, base - 0.3, base + 0.3
            vol = 1000
        else:
            base = 100 + (i % 3) * 0.1
            high, low, opn, close = base + 0.3, base - 0.3, base + 0.05, base - 0.05
            vol = 600
        bars.append({
            "date": (date(2026, 9, 1) + timedelta(days=i)).isoformat(), "open": str(opn),
            "high": str(high), "low": str(low), "close": str(close),
            "volume": str(vol),
        })
    if last_overrides:
        bars[-1].update(last_overrides)
    return {
        "symbol": "TEST",
        "price_volume": {
            "status": "verified", "source_id": "TEST_OHLCV",
            "coverage": "1", "available_at": "2026-11-26T15:00:00+05:45",
            "bars": bars,
        },
    }


class IDPATAccumulationDistributionTests(unittest.TestCase):
    def analyze(self, data):
        return analyze_idpat_accumulation_distribution(
            data, as_of_date="2026-11-26",
            as_of_timestamp="2026-11-26T16:00:00+05:45",
        )

    def test_partial_result_never_becomes_trade_recommendation(self):
        result = self.analyze(make_snapshot())
        self.assertEqual(result["status"], "partial_research_only")
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIsNone(result["overall_score"])

    def test_low_coverage_is_withheld(self):
        data = make_snapshot()
        data["price_volume"]["coverage"] = "0.7"
        result = self.analyze(data)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["reason"], "coverage_below_threshold")

    def test_insufficient_history_is_withheld(self):
        data = make_snapshot()
        data["price_volume"]["bars"] = data["price_volume"]["bars"][-25:]
        result = self.analyze(data)
        self.assertEqual(result["reason"], "at_least_40_valid_bars_required")

    def test_shakeout_reclaim_candidate(self):
        data = make_snapshot({
            "open": "99.8", "high": "100.1", "low": "98.5",
            "close": "100.0", "volume": "2500",
        })
        result = self.analyze(data)
        self.assertTrue(result["signals"]["possible_shakeout"])

    def test_upthrust_rejection_candidate(self):
        data = make_snapshot({
            "open": "100.1", "high": "103.5", "low": "99.8",
            "close": "100.0", "volume": "2500",
        })
        result = self.analyze(data)
        self.assertTrue(result["signals"]["possible_upthrust"])

    def test_climax_requires_volume_and_spread_expansion(self):
        data = make_snapshot({
            "open": "99.0", "high": "101.5", "low": "97.5",
            "close": "98.2", "volume": "3000",
        })
        result = self.analyze(data)
        self.assertTrue(result["signals"]["possible_selling_climax"])

    def test_duplicate_or_overlapping_session_window_is_rejected(self):
        data = make_snapshot()
        data["price_volume"]["bars"][-1] = dict(data["price_volume"]["bars"][-2])
        with self.assertRaisesRegex(IDPATError, "bars_must_be_unique_and_ascending"):
            self.analyze(data)

    def test_non_finite_and_negative_ohlcv_are_rejected(self):
        for field, value in (("volume", "NaN"), ("volume", "-1"), ("close", "Infinity"), ("low", "-0.1")):
            with self.subTest(field=field, value=value):
                data = make_snapshot()
                data["price_volume"]["bars"][-1][field] = value
                with self.assertRaises(IDPATError):
                    self.analyze(data)

    def test_timezone_naive_availability_is_rejected(self):
        data = make_snapshot()
        data["price_volume"]["available_at"] = "2026-11-26T15:00:00"
        with self.assertRaisesRegex(IDPATError, "timezone_aware"):
            self.analyze(data)

    def test_symbol_and_security_identity_change_is_rejected(self):
        data = make_snapshot()
        data["security_id"] = "SEC-1"
        data["price_volume"]["bars"][10]["security_id"] = "SEC-2"
        with self.assertRaisesRegex(IDPATError, "bar_security_identity_mismatch"):
            self.analyze(data)
        data = make_snapshot()
        data["price_volume"]["bars"][10]["symbol"] = "OTHER"
        with self.assertRaisesRegex(IDPATError, "bar_symbol_identity_mismatch"):
            self.analyze(data)

    def test_future_bar_is_withheld_by_upstream_validator(self):
        data = make_snapshot()
        data["price_volume"]["bars"][-1]["date"] = "2026-11-27"
        result = self.analyze(data)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["reason"], "bar_after_cutoff")


if __name__ == "__main__":
    unittest.main()
