import unittest
from app.idpat_price_volume import IDPATError, analyze_idpat_price_volume


def snapshot():
    bars = []
    for i in range(21):
        close = 100 + i * 0.2
        bars.append({
            "date": f"2026-10-{i + 1:02d}", "open": str(close - 0.1),
            "high": str(close + 0.3), "low": str(close - 0.3),
            "close": str(close), "volume": "1000",
        })
    bars[-1].update({"open": "103.8", "high": "106", "low": "103.5",
                     "close": "105.8", "volume": "2000"})
    return {
        "symbol": "TEST",
        "price_volume": {
            "status": "verified", "source_id": "OHLCV_SOURCE",
            "coverage": "1", "available_at": "2026-11-26T15:00:00+05:45",
            "bars": bars,
        },
    }


class IDPATPriceVolumeTests(unittest.TestCase):
    def run_engine(self, data):
        return analyze_idpat_price_volume(
            data, as_of_date="2026-11-26",
            as_of_timestamp="2026-11-26T16:00:00+05:45",
        )

    def test_partial_result_never_emits_trade_signal_or_overall_score(self):
        result = self.run_engine(snapshot())
        self.assertEqual(result["status"], "partial_research_only")
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIsNone(result["overall_score"])
        self.assertIsNone(result.get("probability"))

    def test_breakout_requires_close_and_volume(self):
        result = self.run_engine(snapshot())
        self.assertTrue(result["signals"]["breakout_confirmed_by_close_and_volume"])

    def test_unverified_evidence_is_withheld(self):
        data = snapshot()
        data["price_volume"]["status"] = "unverified"
        self.assertEqual(self.run_engine(data)["status"], "withheld")

    def test_low_coverage_is_withheld(self):
        data = snapshot()
        data["price_volume"]["coverage"] = "0.8"
        self.assertEqual(self.run_engine(data)["reason"], "coverage_below_threshold")

    def test_future_bar_is_withheld(self):
        data = snapshot()
        data["price_volume"]["bars"][-1]["date"] = "2026-11-27"
        self.assertEqual(self.run_engine(data)["reason"], "bar_after_cutoff")

    def test_duplicate_or_unsorted_bars_rejected(self):
        data = snapshot()
        data["price_volume"]["bars"][-1]["date"] = data["price_volume"]["bars"][-2]["date"]
        with self.assertRaises(IDPATError):
            self.run_engine(data)

    def test_cutoff_and_bar_dates_must_be_canonical_iso(self):
        data = snapshot()
        with self.assertRaisesRegex(IDPATError, "noncanonical_as_of_date"):
            analyze_idpat_price_volume(
                data, as_of_date="20261126",
                as_of_timestamp="2026-11-26T16:00:00+05:45",
            )
        data["price_volume"]["bars"][-1]["date"] = "20261021"
        with self.assertRaisesRegex(IDPATError, "noncanonical_bar_date"):
            self.run_engine(data)

    def test_zero_or_fractional_share_volume_is_rejected(self):
        for volume in ("0", "1.5"):
            data = snapshot()
            data["price_volume"]["bars"][-1]["volume"] = volume
            with self.subTest(volume=volume), self.assertRaisesRegex(
                IDPATError, "bar_volume_must_be_positive_whole_shares"
            ):
                self.run_engine(data)

    def test_late_evidence_is_withheld(self):
        data = snapshot()
        data["price_volume"]["available_at"] = "2026-11-27T10:00:00+05:45"
        self.assertEqual(self.run_engine(data)["reason"], "evidence_not_available_as_of_cutoff")


if __name__ == "__main__":
    unittest.main()
