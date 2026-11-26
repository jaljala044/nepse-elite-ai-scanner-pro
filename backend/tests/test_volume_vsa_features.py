import unittest
from datetime import date, timedelta

from app.volume_vsa_features import volume_vsa_features


def rows(n, final_volume=1000, final_close=None):
    start = date(2025, 1, 1)
    result = []
    for i in range(n):
        close = 100 + i * 0.1
        result.append({
            "session_date": (start + timedelta(days=i)).isoformat(),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000,
        })
    if final_volume is not None:
        result[-1]["volume"] = final_volume
    if final_close is not None:
        result[-1]["close"] = final_close
        result[-1]["high"] = max(result[-1]["high"], final_close)
    return result


class VolumeVSATests(unittest.TestCase):
    def test_insufficient_history_returns_null_score(self):
        result = volume_vsa_features(rows(20))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_volume_expansion_and_strong_close_detected(self):
        data = rows(21, final_volume=2500, final_close=105)
        result = volume_vsa_features(data)
        self.assertEqual(result["status"], "observed")
        self.assertTrue(result["checks"]["volume_expansion"])
        self.assertTrue(result["checks"]["close_near_high"])
        self.assertEqual(result["interpretation"], "demand_response_observed")

    def test_volume_dry_up_and_narrow_spread_reported(self):
        data = rows(21, final_volume=500)
        data[-1]["high"] = data[-1]["close"] + 0.1
        data[-1]["low"] = data[-1]["open"] - 0.1
        result = volume_vsa_features(data)
        self.assertTrue(result["checks"]["volume_dry_up"])
        self.assertTrue(result["checks"]["narrow_spread"])

    def test_missing_ohlc_is_unavailable_not_exception(self):
        data = rows(21)
        del data[-1]["high"]
        result = volume_vsa_features(data)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_duplicate_dates_rejected(self):
        data = rows(21)
        data.append(dict(data[-1]))
        with self.assertRaises(ValueError):
            volume_vsa_features(data)

    def test_non_finite_volume_rejected(self):
        data = rows(21)
        data[-1]["volume"] = float("nan")
        with self.assertRaises(ValueError):
            volume_vsa_features(data)


if __name__ == "__main__":
    unittest.main()
