import unittest
from app.broker_behavior_memory import build_broker_behavior_memory


def obs(day="2026-11-24", side="buy", amount="100", available="2026-11-24T12:00:00+05:45", **extra):
    row = {
        "trade_date": day, "available_at": available, "security_id": "SEC-1",
        "broker_entity_id": "BROKER-1", "identity_status": "verified",
        "session_status": "verified", "side": side, "amount": amount,
        "quantity": "2", "coverage_ratio": "1", "source_row_count": 2,
        "source_id": "SRC-1", "evidence_id": "E-1", "source_payload_sha256": "a" * 64,
    }
    row.update(extra)
    return row


class BrokerBehaviorMemoryTests(unittest.TestCase):
    def test_builds_daily_weekly_monthly_yearly_descriptors(self):
        result = build_broker_behavior_memory(
            [obs(), obs(side="sell", amount="30")], as_of_date="2026-11-24"
        )
        self.assertEqual([r["window"] for r in result["memory_rows"]],
                         ["daily", "weekly", "monthly", "yearly"])
        self.assertEqual(result["memory_rows"][0]["net_amount"], "70")
        self.assertEqual(result["memory_rows"][0]["status"], "descriptive_only")

    def test_future_and_late_available_rows_are_excluded(self):
        result = build_broker_behavior_memory(
            [obs(day="2026-11-25"), obs(available="2026-11-25T12:00:00+05:45")],
            as_of_date="2026-11-24"
        )
        self.assertEqual(result["admitted_observation_rows"], 0)
        self.assertEqual({x["reason"] for x in result["exclusions"]},
                         {"future_event", "not_yet_available_as_of"})

    def test_unverified_identity_session_and_low_coverage_fail_closed(self):
        result = build_broker_behavior_memory([
            obs(identity_status="unmapped"),
            obs(session_status="unknown"),
            obs(coverage_ratio="0.80"),
        ], as_of_date="2026-11-24")
        self.assertEqual(result["admitted_observation_rows"], 0)
        self.assertEqual(result["excluded_observation_rows"], 3)

    def test_no_data_is_not_synthesized(self):
        result = build_broker_behavior_memory([], as_of_date="2026-11-24")
        self.assertEqual(result["memory_rows"], [])
        self.assertEqual(result["admitted_observation_rows"], 0)

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            build_broker_behavior_memory([], as_of_date="2026-11-24",
                                         windows={"weekly": 0})


if __name__ == "__main__":
    unittest.main()
