import unittest
from datetime import date, timedelta

from app.wyckoff_features import wyckoff_event_features


def flat_history(count=45):
    start = date(2026, 1, 1)
    return [{
        "session_date": (start + timedelta(days=i)).isoformat(),
        "open": 100.0, "high": 101.0, "low": 99.0,
        "close": 100.0, "volume": 1000,
    } for i in range(count)]


class WyckoffFeatureTests(unittest.TestCase):
    def test_insufficient_history_is_not_scored(self):
        result = wyckoff_event_features(flat_history(40))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])
        self.assertEqual(result["events"], [])

    def test_spring_candidate_requires_sweep_reclaim_and_volume(self):
        rows = flat_history()
        rows.append({
            "session_date": "2026-02-15", "open": 99.5, "high": 101.0,
            "low": 98.0, "close": 100.5, "volume": 1500,
        })
        result = wyckoff_event_features(rows)
        self.assertIn("spring", [e["event"] for e in result["events"]])
        spring = next(e for e in result["events"] if e["event"] == "spring")
        self.assertEqual(spring["status"], "candidate")
        self.assertIn("subsequent close below", spring["invalidation_rule"])

    def test_upthrust_candidate_requires_sweep_rejection(self):
        rows = flat_history()
        rows.append({
            "session_date": "2026-02-15", "open": 100.5, "high": 102.0,
            "low": 99.0, "close": 99.5, "volume": 1500,
        })
        result = wyckoff_event_features(rows)
        self.assertIn("upthrust", [e["event"] for e in result["events"]])

    def test_sos_and_jump_across_creek_on_confirmed_volume_expansion(self):
        rows = flat_history()
        rows.append({
            "session_date": "2026-02-15", "open": 101.0, "high": 103.0,
            "low": 100.5, "close": 102.8, "volume": 2000,
        })
        result = wyckoff_event_features(rows)
        names = [e["event"] for e in result["events"]]
        self.assertIn("sos", names)
        self.assertIn("jump_across_creek", names)

    def test_lps_and_backup_require_prior_sos_then_low_volume_retest(self):
        rows = flat_history()
        rows.append({
            "session_date": "2026-02-15", "open": 101.0, "high": 103.0,
            "low": 100.5, "close": 102.8, "volume": 2000,
        })
        rows.append({
            "session_date": "2026-02-16", "open": 102.0, "high": 102.5,
            "low": 100.8, "close": 101.5, "volume": 800,
        })
        result = wyckoff_event_features(rows)
        names = [e["event"] for e in result["events"]]
        self.assertIn("lps", names)
        self.assertIn("backup_to_creek", names)

    def test_duplicate_sessions_are_rejected(self):
        rows = flat_history()
        rows[-1] = dict(rows[-2])
        with self.assertRaisesRegex(ValueError, "duplicate session_date"):
            wyckoff_event_features(rows)

    def test_invalid_ohlc_is_rejected(self):
        rows = flat_history()
        rows[-1]["low"] = 100.5
        with self.assertRaisesRegex(ValueError, "inconsistent low"):
            wyckoff_event_features(rows)

    def test_sow_and_lpsy_sequence(self):
        rows = flat_history()
        rows.append({
            "session_date": "2026-02-15", "open": 99.0, "high": 99.5,
            "low": 97.0, "close": 97.5, "volume": 2000,
        })
        rows.append({
            "session_date": "2026-02-16", "open": 98.0, "high": 99.0,
            "low": 97.5, "close": 98.5, "volume": 800,
        })
        result = wyckoff_event_features(rows)
        names = [e["event"] for e in result["events"]]
        self.assertIn("sow", names)
        self.assertIn("lpsy", names)


if __name__ == "__main__":
    unittest.main()
