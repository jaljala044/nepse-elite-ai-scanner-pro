import unittest
from datetime import date, timedelta

from app.broker_pattern_detector import detect_broker_patterns


HASH = "a" * 64


def fixture_rows(direction="accumulation"):
    start = date(2026, 11, 2)
    sessions = [(start + timedelta(days=i)).isoformat() for i in range(5)]
    broker_rows, price_rows, context_rows = [], [], []
    for day_index, day in enumerate(sessions):
        digest = format(day_index + 1, "064x")
        available = day + "T16:00:00Z"
        if direction == "accumulation":
            close = 100 + day_index * 0.3
        else:
            close = 100 - day_index * 0.8
        if day_index < 2:
            # Neutral broker breadth establishes a prior baseline.
            trades = [
                ("C1", "A", "C", "100"),
                ("C2", "C", "A", "100"),
                ("C3", "B", "C", "100"),
                ("C4", "C", "B", "100"),
            ]
        elif direction == "accumulation":
            trades = [
                ("C1", "A", "C", "100"),
                ("C2", "B", "C", "100"),
                ("C3", "C", "A", "20"),
                ("C4", "C", "B", "20"),
            ]
        else:
            trades = [
                ("C1", "C", "A", "100"),
                ("C2", "C", "B", "100"),
                ("C3", "A", "C", "20"),
                ("C4", "B", "C", "20"),
            ]
        row_number = 1
        for contract, buyer, seller, amount in trades:
            for side, broker in (("buy", buyer), ("sell", seller)):
                broker_rows.append({
                    "trade_date": day, "available_at": available, "symbol": "TEST",
                    "side": side, "amount": amount, "quantity": "1",
                    "identity_status": "verified", "broker_entity_id": broker,
                    "source_broker_code": broker, "contract_id": contract,
                    "source_id": "floorsheet-" + day, "source_payload_sha256": digest,
                    "source_row_number": row_number,
                    "source_validation_status": "verified",
                    "session_calendar_status": "confirmed_open",
                    "floorsheet_coverage_status": "verified_complete",
                })
                row_number += 1
        volume = 1000 if day_index < 2 else 1500
        price_rows.append({
            "symbol": "TEST", "session_date": day, "available_at": available,
            "close": str(close), "high": str(close + 1), "low": str(close - 1),
            "volume": str(volume), "turnover": str(volume * close),
            "source_validation_status": "verified", "source_id": "ohlcv-" + day,
            "source_payload_sha256": digest,
            "price_basis_status": "verified_unadjusted_no_actions",
            "corporate_action_status": "clear",
        })
        context_rows.append({
            "session_date": day, "available_at": available,
            "validation_status": "verified", "market_return_pct": "0.1",
            "sector_return_pct": "0.1", "source_id": "context-" + day,
            "source_payload_sha256": digest,
        })
    return sessions, broker_rows, price_rows, context_rows


class BrokerPatternDetectorTests(unittest.TestCase):
    def run_detector(self, direction="accumulation"):
        sessions, brokers, prices, context = fixture_rows(direction)
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        return result, (sessions, brokers, prices, context)

    def test_repeated_broker_breadth_emits_descriptive_accumulation_candidate(self):
        result, _ = self.run_detector()
        self.assertEqual(result["status"], "CANDIDATE")
        self.assertEqual(result["pattern"], "EARLY_ACCUMULATION_CANDIDATE")
        self.assertEqual(result["trading_action"], "NONE")
        self.assertFalse(result["production_eligible"])
        self.assertEqual(result["calibration_status"], "UNCALIBRATED")

    def test_persistent_selling_and_price_weakness_emits_distribution_candidate(self):
        result, _ = self.run_detector("distribution")
        self.assertEqual(result["status"], "CANDIDATE")
        self.assertEqual(result["pattern"], "EARLY_DISTRIBUTION_CANDIDATE")
        self.assertEqual(result["trading_action"], "NONE")

    def test_incomplete_broker_inventory_fails_closed(self):
        sessions, brokers, prices, context = fixture_rows()
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions[:-1],
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("complete_broker_session_inventory", result["missing_features"])

    def test_late_available_future_evidence_is_excluded(self):
        sessions, brokers, prices, context = fixture_rows()
        brokers[0]["available_at"] = "2026-11-10T19:00:00Z"
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("matched_contract_buyer_seller_parties", result["missing_features"])

    def test_duplicate_contract_side_cannot_inflate_persistence(self):
        sessions, brokers, prices, context = fixture_rows()
        brokers.append(dict(brokers[0]))
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("duplicate_or_conflicting_broker_party", result["missing_features"])


    def test_unmatched_contract_parties_fail_closed(self):
        sessions, brokers, prices, context = fixture_rows()
        brokers.pop()
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("matched_contract_buyer_seller_parties", result["missing_features"])

    def test_unverified_floorsheet_rows_fail_closed(self):
        sessions, brokers, prices, context = fixture_rows()
        brokers[0]["floorsheet_coverage_status"] = "partial"
        result = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("verified_complete_broker_source_session", result["missing_features"])

    def test_later_price_data_does_not_change_historical_snapshot(self):
        result, (sessions, brokers, prices, context) = self.run_detector()
        future = dict(prices[-1])
        future["available_at"] = "2026-11-10T19:00:00Z"
        future["close"] = "9999"
        prices.append(future)
        replay = detect_broker_patterns(
            "TEST", brokers, prices, context,
            expected_sessions=sessions, complete_broker_sessions=sessions,
            decision_at=sessions[-1] + "T18:00:00Z",
        )
        self.assertEqual(replay["status"], result["status"])
        self.assertEqual(replay["pattern"], result["pattern"])
        self.assertEqual(replay["features"], result["features"])


if __name__ == "__main__":
    unittest.main()
