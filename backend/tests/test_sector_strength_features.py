import unittest
from datetime import date, timedelta

from app.sector_strength_features import sector_strength_features

DIGEST = "a" * 64


def fixture(count=127):
    dates = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    members = {"BANK": ["AAA", "BBB"], "HYDRO": ["CCC", "DDD"]}
    mapping = {symbol: {"sector_code": sector, "status": "verified",
                        "source_id": "security-master-v1", "source_payload_sha256": DIGEST}
               for sector, symbols in members.items() for symbol in symbols}
    rows = []
    for symbol, multiplier in (("AAA", 1.8), ("BBB", 1.5), ("CCC", 1.2), ("DDD", 1.1)):
        for index, day in enumerate(dates):
            rows.append({"symbol": symbol, "session_date": day, "close": 100 + index * multiplier})
    return dates, members, mapping, rows


class SectorStrengthTests(unittest.TestCase):
    def test_sector_returns_and_cross_sector_scores_observed(self):
        dates, members, mapping, rows = fixture()
        result = sector_strength_features(rows, sector_membership=mapping,
            expected_sector_members=members, session_dates=dates)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["sectors"]["BANK"]["score_status"], "observed")
        self.assertGreater(result["sectors"]["BANK"]["score"], result["sectors"]["HYDRO"]["score"])

    def test_unverified_membership_is_not_counted(self):
        dates, members, mapping, rows = fixture()
        mapping["AAA"]["status"] = "unverified"
        result = sector_strength_features(rows, sector_membership=mapping,
            expected_sector_members=members, session_dates=dates)
        self.assertEqual(result["sectors"]["BANK"]["mapped_members"], 1)
        self.assertIsNone(result["sectors"]["BANK"]["score"])

    def test_missing_intermediate_session_withholds_window(self):
        dates, members, mapping, rows = fixture()
        rows = [row for row in rows if not (row["symbol"] == "AAA" and row["session_date"] == dates[-10])]
        result = sector_strength_features(rows, sector_membership=mapping,
            expected_sector_members=members, session_dates=dates)
        self.assertEqual(result["sectors"]["BANK"]["windows"]["1M"]["status"], "insufficient_evidence")

    def test_duplicate_symbol_session_rejected(self):
        dates, members, mapping, rows = fixture()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate symbol/session"):
            sector_strength_features(rows, sector_membership=mapping,
                expected_sector_members=members, session_dates=dates)

    def test_no_verified_universe_fails_closed(self):
        dates, _, mapping, rows = fixture()
        result = sector_strength_features(rows, sector_membership=mapping,
            expected_sector_members={}, session_dates=dates)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["reason"], "verified_sector_universe_missing")

    def test_short_calendar_fails_closed(self):
        dates, members, mapping, rows = fixture(20)
        result = sector_strength_features(rows, sector_membership=mapping,
            expected_sector_members=members, session_dates=dates)
        self.assertEqual(result["reason"], "canonical_session_calendar_too_short")


if __name__ == "__main__":
    unittest.main()
