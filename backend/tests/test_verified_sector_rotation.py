import unittest
from datetime import date, timedelta

from app.verified_sector_rotation import build_verified_sector_rotation

DIGEST = "a" * 64
CUTOFF = "2026-11-26T18:00:00+05:45"


def fixture(count=127):
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    members = {"BANK": ["AAA", "BBB"], "HYDRO": ["CCC", "DDD"]}
    membership = {
        symbol: {"status": "verified", "source_id": "master-v1",
                 "source_payload_sha256": DIGEST, "effective_from": dates[0],
                 "effective_to": None, "sector_code": sector, "available_at": CUTOFF}
        for sector, symbols in members.items() for symbol in symbols
    }
    stock_rows = []
    multipliers = {"AAA": 2.0, "BBB": 1.8, "CCC": 0.5, "DDD": 0.4}
    for symbol, multiplier in multipliers.items():
        for i, day in enumerate(dates):
            stock_rows.append({
                "symbol": symbol, "session_date": day, "close": 100 + i * multiplier,
                "source_validation_status": "verified",
                "price_basis_status": "verified_unadjusted_no_actions",
                "corporate_action_status": "clear", "source_id": "stock-" + symbol,
                "source_payload_sha256": DIGEST, "available_at": CUTOFF,
            })
    benchmark_rows = [{
        "record_type": "index_ohlcv", "index_code": "NEPSE",
        "session_date": day, "close": 100 + i,
        "source_validation_status": "verified", "finality_status": "final",
        "source_id": "nepse-index", "source_payload_sha256": DIGEST,
        "available_at": CUTOFF,
    } for i, day in enumerate(dates)]
    return dates, members, membership, stock_rows, benchmark_rows


class VerifiedSectorRotationTests(unittest.TestCase):
    def call(self, data, **kwargs):
        dates, members, membership, stocks, benchmark = data
        args = dict(expected_sector_members=members, sector_membership=membership,
                    verified_session_dates=dates, decision_time=CUTOFF)
        args.update(kwargs)
        return build_verified_sector_rotation(stocks, benchmark, **args)

    def test_sector_returns_rs_and_classification(self):
        result = self.call(fixture())
        self.assertEqual(result["status"], "observed")
        self.assertFalse(result["signals_enabled"])
        self.assertGreater(result["sectors"]["BANK"]["weighted_excess_return_pct"],
                           result["sectors"]["HYDRO"]["weighted_excess_return_pct"])
        self.assertEqual(result["sectors"]["BANK"]["classification"], "Leading")
        self.assertEqual(result["sectors"]["HYDRO"]["classification"], "Lagging")
        self.assertIsNotNone(result["sectors"]["BANK"]["windows"]["1W"]["median_return_pct"])

    def test_constituent_rankings_and_withholding(self):
        data = fixture()
        result = self.call(data)
        rows = result["sectors"]["BANK"]["windows"]["1M"]["constituents"]
        self.assertEqual([r["symbol"] for r in rows], ["AAA", "BBB"])
        self.assertGreater(rows[0]["excess_return_pct"], rows[1]["excess_return_pct"])
        data[2]["AAA"]["status"] = "unverified"
        self.assertIsNone(self.call(data)["sectors"]["BANK"]["windows"]["1M"]["constituents"])

    def test_unverified_membership_withholds_sector_score(self):
        data = fixture()
        data[2]["AAA"]["status"] = "unverified"
        result = self.call(data)
        self.assertEqual(result["sectors"]["BANK"]["score_status"], "insufficient_evidence")

    def test_missing_stock_session_is_not_filled(self):
        data = list(fixture())
        dates = data[0]
        data[3] = [row for row in data[3] if not (
            row["symbol"] == "AAA" and row["session_date"] == dates[-10])]
        result = self.call(data)
        self.assertEqual(result["sectors"]["BANK"]["windows"]["1M"]["status"],
                         "insufficient_evidence")

    def test_missing_benchmark_session_withholds_all(self):
        data = list(fixture())
        dates = data[0]
        data[4] = [row for row in data[4] if row["session_date"] != dates[-1]]
        result = self.call(data)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["reason"], "nepse_benchmark_missing_exact_sessions")

    def test_future_data_is_excluded(self):
        data = fixture()
        data[3][0]["available_at"] = "2026-11-26T18:01:00+05:45"
        result = self.call(data)
        self.assertEqual(result["excluded_rows"]["stock"]["late_or_out_of_calendar"], 1)
        self.assertEqual(result["sectors"]["BANK"]["score_status"], "insufficient_evidence")

    def test_duplicate_stock_session_rejected(self):
        data = fixture()
        data[3].append(dict(data[3][0]))
        with self.assertRaisesRegex(ValueError, "duplicate_price_session"):
            self.call(data)

    def test_duplicate_calendar_rejected(self):
        data = fixture()
        data[0].append(data[0][-1])
        with self.assertRaisesRegex(ValueError, "unique_ascending"):
            self.call(data)

    def test_late_membership_withholds(self):
        data = fixture()
        data[2]["AAA"]["available_at"] = "2026-11-26T18:01:00+05:45"
        self.assertEqual(self.call(data)["sectors"]["BANK"]["score_status"], "insufficient_evidence")

    def test_missing_membership_timestamp_withholds(self):
        data = fixture()
        del data[2]["AAA"]["available_at"]
        self.assertEqual(self.call(data)["sectors"]["BANK"]["score_status"], "insufficient_evidence")

    def test_recent_reclassification_not_backdated(self):
        data = fixture()
        data[2]["AAA"]["effective_from"] = data[0][-6]
        result = self.call(data)["sectors"]["BANK"]["windows"]
        self.assertEqual(result["1W"]["status"], "observed")
        self.assertEqual(result["1M"]["status"], "insufficient_evidence")
        self.assertIn("AAA", result["1M"]["missing_members"])

    def test_short_calendar_withholds(self):
        data = fixture(100)
        result = self.call(data)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertFalse(result["signals_enabled"])


if __name__ == "__main__":
    unittest.main()
