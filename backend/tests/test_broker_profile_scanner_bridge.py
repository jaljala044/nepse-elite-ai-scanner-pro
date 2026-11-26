import unittest

from app.broker_profile_scanner_bridge import build_broker_profile_scanner_context


POLICY = "complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only"


def snapshot(rows, timestamp="2026-11-26T12:00:00+05:45", day="2026-11-26"):
    return {"policy": POLICY, "as_of_date": day, "as_of_timestamp": timestamp, "profiles": rows}


def profile(broker, label="net_buy_dominant", window="weekly"):
    return {"security_id": "SEC-1", "broker_id": broker, "window": window,
            "status": "descriptive_only", "directional_summary": label,
            "coverage_ratio": "1", "requested_sessions": 5, "expected_sessions": 5,
            "complete_source_sessions": 5}


class BrokerProfileScannerBridgeTests(unittest.TestCase):
    def test_broker_breadth_is_exposed_as_context_not_score(self):
        result = build_broker_profile_scanner_context(
            snapshot([profile("B1"), profile("B2"), profile("B3", "net_sell_dominant")]),
            decision_time="2026-11-26T13:00:00+05:45", expected_security_ids=["SEC-1"])
        item = result["securities"]["SEC-1"]["windows"]["weekly"]
        self.assertEqual(item["directional_breadth"], "buy_side_breadth")
        self.assertIsNone(item["score"])
        self.assertFalse(result["score_eligible"])

    def test_future_snapshot_is_withheld(self):
        result = build_broker_profile_scanner_context(
            snapshot([profile("B1"), profile("B2"), profile("B3")],
                     timestamp="2026-11-27T09:00:00+05:45", day="2026-11-27"),
            decision_time="2026-11-26T13:00:00+05:45", expected_security_ids=["SEC-1"])
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["reason"], "rolling_profile_is_after_scanner_decision_time")

    def test_missing_or_unrecognized_policy_fails_closed(self):
        result = build_broker_profile_scanner_context(
            {"profiles": [profile("B1")]}, decision_time="2026-11-26T13:00:00+05:45",
            expected_security_ids=["SEC-1"])
        self.assertEqual(result["reason"], "rolling_profile_policy_unrecognized")

    def test_below_minimum_broker_count_withholds_direction(self):
        result = build_broker_profile_scanner_context(
            snapshot([profile("B1"), profile("B2")]),
            decision_time="2026-11-26T13:00:00+05:45", expected_security_ids=["SEC-1"])
        self.assertEqual(result["securities"]["SEC-1"]["windows"]["weekly"]["status"],
                         "insufficient_evidence")

    def test_incomplete_coverage_is_rejected(self):
        row = profile("B1")
        row["coverage_ratio"] = "0.8"
        result = build_broker_profile_scanner_context(
            snapshot([row, profile("B2"), profile("B3")]),
            decision_time="2026-11-26T13:00:00+05:45", expected_security_ids=["SEC-1"])
        self.assertEqual(result["securities"]["SEC-1"]["windows"]["weekly"]["status"],
                         "insufficient_evidence")
        self.assertEqual(result["rejected_profile_rows"], 1)

    def test_duplicate_broker_profile_for_window_is_withheld(self):
        result = build_broker_profile_scanner_context(
            snapshot([profile("B1"), profile("B1"), profile("B2")]),
            decision_time="2026-11-26T13:00:00+05:45", expected_security_ids=["SEC-1"])
        self.assertEqual(result["securities"]["SEC-1"]["windows"]["weekly"]["reason"],
                         "duplicate_broker_window_profile")

    def test_naive_decision_time_rejected(self):
        with self.assertRaises(ValueError):
            build_broker_profile_scanner_context(None, decision_time="2026-11-26T13:00:00",
                                                 expected_security_ids=["SEC-1"])


if __name__ == "__main__":
    unittest.main()
