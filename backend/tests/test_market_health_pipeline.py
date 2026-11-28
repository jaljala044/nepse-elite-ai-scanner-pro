import unittest
from datetime import date, timedelta

from app.market_health_pipeline import build_market_health_snapshot

DIGEST = "e" * 64
DECISION_TIME = "2027-01-01T16:00:00+05:45"


def sessions(count):
    start = date(2025, 1, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


def index_rows(calendar):
    return [{
        "record_type": "index_ohlcv", "index_code": "NEPSE",
        "session_date": day, "open": 100, "high": 101, "low": 99, "close": 100,
        "source_validation_status": "verified", "finality_status": "final",
        "source_id": "verified-nepse-index-v1", "source_payload_sha256": DIGEST,
        "available_at": "2026-12-31T15:00:00+05:45",
    } for day in calendar]


def equity_rows(symbols, calendar):
    return [{
        "record_type": "ohlcv", "symbol": symbol, "session_date": day,
        "open": 100, "high": 101, "low": 99, "close": 100,
        "source_validation_status": "verified", "finality_status": "final",
        "source_id": "verified-equity-eod-v1", "source_payload_sha256": DIGEST,
        "available_at": "2026-12-31T15:00:00+05:45",
    } for symbol in symbols for day in calendar[-200:]]


def turnover_rows(calendar):
    return [{
        "record_type": "market_summary", "market_code": "NEPSE",
        "session_date": day, "total_turnover": 1000,
        "source_validation_status": "verified", "finality_status": "final",
        "source_id": "verified-nepse-market-summary-v1",
        "source_payload_sha256": DIGEST,
        "available_at": "2026-12-31T15:00:00+05:45",
    } for day in calendar[-21:]]


def manifest(source_id, as_of_session, **extra):
    return {
        "status": "verified", "source_id": source_id,
        "source_payload_sha256": DIGEST, "as_of_session": as_of_session, **extra,
    }


def sector_features(as_of_session):
    names = ["Banking", "Development Banks", "Finance", "Hydropower", "Insurance"]
    return {
        "status": "observed", "as_of_session": as_of_session,
        "method": "median_constituent_return_cross_sector_percentile",
        "sectors": {
            name: {"windows": {
                "1W": {"status": "observed", "median_return_pct": 0.5},
                "1M": {"status": "observed", "median_return_pct": 1.0},
                "3M": {"status": "observed", "median_return_pct": 2.0},
                "6M": {"status": "observed", "median_return_pct": 3.0},
            }} for name in names
        },
    }


class MarketHealthPipelineTests(unittest.TestCase):
    def make_snapshot(self, full=True):
        calendar = sessions(271)
        symbols = ["AAA", "BBB", "CCC", "DDD", "EEE"]
        as_of = calendar[-1]
        return build_market_health_snapshot(
            index_rows=index_rows(calendar) if full else [],
            equity_ohlcv_rows=equity_rows(symbols, calendar) if full else [],
            market_summary_rows=turnover_rows(calendar) if full else [],
            session_dates=calendar,
            expected_symbols=symbols,
            equity_universe_provenance=manifest("verified-mature-equity-universe-v1", as_of),
            sector_features=sector_features(as_of) if full else {
                "status": "insufficient_evidence", "as_of_session": as_of, "sectors": {},
            },
            sector_universe_provenance=manifest(
                "verified-sector-master-v1", as_of, expected_sector_count=5
            ),
            sector_price_evidence=manifest("verified-sector-price-manifest-v1", as_of),
            decision_time=DECISION_TIME,
        )

    def test_all_five_verified_components_produce_integrated_snapshot(self):
        result = self.make_snapshot()
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["market_health"]["coverage_pct"], 100.0)
        self.assertEqual(result["data_quality"]["verified_component_count"], 5)
        self.assertEqual(result["market_health"]["regime"], "markdown")
        self.assertEqual(result["market_health"]["trading_posture"], "preserve_capital")
        self.assertIsNone(result["market_health"]["probability"])
        self.assertFalse(result["data_quality"]["production_data_claim"])

    def test_missing_live_evidence_fails_closed_to_unknown(self):
        result = self.make_snapshot(full=False)
        self.assertEqual(result["market_health"]["regime"], "unknown")
        self.assertEqual(result["market_health"]["trading_posture"], "preserve_capital")
        self.assertIsNone(result["market_health"]["market_health_score"])
        self.assertEqual(result["market_health"]["coverage_pct"], 0.0)
        self.assertEqual(result["data_quality"]["verified_component_count"], 0)

    def test_market_health_never_treats_synthetic_snapshot_as_production_claim(self):
        result = self.make_snapshot()
        self.assertFalse(result["data_quality"]["production_data_claim"])
        self.assertIn("synthetic tests", result["data_quality"]["note"])


if __name__ == "__main__":
    unittest.main()
