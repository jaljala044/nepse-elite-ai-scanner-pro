import unittest
from app.broker_context_integration import build_context, POLICY


class BrokerContextTests(unittest.TestCase):
    def fixture(self):
        days = ["2026-04-" + str(i) for i in range(20, 25)]
        timestamp = "2026-04-24T18:00:00+05:45"
        evidence = {
            "status": "verified", "source_id": "synthetic-test",
            "source_payload_sha256": "a" * 64, "available_at": timestamp,
        }
        daily = [
            dict(session_date=day, buy_amount="100", sell_amount="20",
                 net_amount="80", gross_amount="120", broker_participation=".2")
            for day in days
        ]
        snapshot = {
            "policy": POLICY, "as_of_timestamp": timestamp, "as_of_date": days[-1],
            "profiles": [dict(
                security_id="S1", broker_id="B1", requested_sessions=5,
                expected_sessions=5, complete_source_sessions=5,
                status="descriptive_only", coverage_ratio="1", daily=daily,
                buy_amount="500", sell_amount="100",
            )],
        }
        prices = [
            dict(evidence, security_id="S1", symbol="TEST", session_date=day,
                 open=100+i, high=102+i, low=99+i, close=101+i, volume=100+i*10)
            for i, day in enumerate(days)
        ]
        memberships = [
            dict(evidence, security_id="S1", symbol="TEST", sector_code="H",
                 effective_from=days[0], effective_to=None)
        ]
        sector = [
            dict(evidence, sector_code="H", session_date=day, close=1000+i)
            for i, day in enumerate(days)
        ]
        return [snapshot, prices, memberships, sector], dict(
            decision_time=timestamp, expected_sessions=days, quarantine_keys=[]
        )

    def test_research_classification_and_determinism(self):
        args, kwargs = self.fixture()
        result = build_context(*args, **kwargs)
        self.assertEqual(result, build_context(*args, **kwargs))
        self.assertEqual(result["profiles"][0]["classification"], "accumulation_research_candidate")
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["source_authentication_performed"])

    def test_late_price(self):
        args, kwargs = self.fixture()
        args[1][0]["available_at"] = "2026-04-25T00:00:00+05:45"
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["status"], "insufficient_evidence")

    def test_missing_and_ambiguous_membership(self):
        args, kwargs = self.fixture()
        args[2].append(dict(args[2][0]))
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["classification"], "UNKNOWN")

    def test_overlapping_membership_is_withheld(self):
        args, kwargs = self.fixture()
        overlap = dict(args[2][0], sector_code="OTHER", effective_from=kwargs["expected_sessions"][2])
        args[2].append(overlap)
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["classification"], "UNKNOWN")

    def test_invalid_or_reversed_membership_interval_is_rejected(self):
        args, kwargs = self.fixture()
        args[2][0]["effective_from"] = "2026-02-30"
        with self.assertRaisesRegex(ValueError, "effective_from must be an ISO date"):
            build_context(*args, **kwargs)
        args, kwargs = self.fixture()
        args[2][0]["effective_from"] = "2026-04-24"
        args[2][0]["effective_to"] = "2026-04-20"
        with self.assertRaisesRegex(ValueError, "precedes"):
            build_context(*args, **kwargs)

    def test_duplicate_and_invalid_expected_sessions_are_rejected(self):
        args, kwargs = self.fixture()
        kwargs["expected_sessions"] = kwargs["expected_sessions"] + [kwargs["expected_sessions"][-1]]
        with self.assertRaisesRegex(ValueError, "invalid session window"):
            build_context(*args, **kwargs)
        args, kwargs = self.fixture()
        kwargs["expected_sessions"][2] = "2026-02-30"
        with self.assertRaisesRegex(ValueError, "expected session must be an ISO date"):
            build_context(*args, **kwargs)

    def test_quarantine(self):
        args, kwargs = self.fixture()
        kwargs["quarantine_keys"] = [("TEST", kwargs["expected_sessions"][2])]
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["classification"], "UNKNOWN")

    def test_incomplete_coverage_and_accounting(self):
        args, kwargs = self.fixture()
        args[0]["profiles"][0]["complete_source_sessions"] = 4
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["classification"], "UNKNOWN")
        args, kwargs = self.fixture()
        args[0]["profiles"][0]["daily"][0]["gross_amount"] = "999"
        self.assertEqual(build_context(*args, **kwargs)["profiles"][0]["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
