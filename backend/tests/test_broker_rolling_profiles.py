import unittest
from app.broker_rolling_profiles import (
    BrokerProfileError, build_rolling_broker_profiles,
)


def obs(day, evidence, side="BUY", amount="100", broker="B17", security="CFCL"):
    return {"security_id":security,"broker_id":broker,"session_date":day,
        "side":side,"amount":amount,"quantity":"1","source_id":"SRC",
        "evidence_id":evidence,"source_payload_sha256":"a"*64,
        "available_at":day+"T18:00:00+05:45","status":"descriptive_only",
        "coverage_ratio":"1"}


def sessions(start, count):
    # Test-only dates; the caller supplies the verified exchange calendar.
    import datetime
    first=datetime.date.fromisoformat(start)
    return [(first+datetime.timedelta(days=i)).isoformat() for i in range(count)]


class RollingBrokerProfilesTests(unittest.TestCase):
    def test_five_session_profile_counts_complete_zero_activity_sessions(self):
        days=sessions("2026-11-20",5)
        rows=[obs(days[0],"E1","BUY","100"),obs(days[1],"E2","SELL","30"),
              obs(days[3],"E3","BUY","50")]
        result=build_rolling_broker_profiles(rows,verified_exchange_sessions=days,
            complete_source_sessions=days,as_of_date=days[-1],
            as_of_timestamp="2026-11-26T12:00:00+05:45",windows={"weekly":5})
        p=result["profiles"][0]
        self.assertEqual(p["coverage_ratio"],"1")
        self.assertEqual(p["buy_amount"],"150")
        self.assertEqual(p["sell_amount"],"30")
        self.assertEqual(p["zero_activity_sessions"],2)
        self.assertEqual(p["directional_summary"],"net_buy_dominant")

    def test_incomplete_session_not_zero_filled_and_withholds_direction(self):
        days=sessions("2026-11-20",5)
        complete=days[:-1]
        result=build_rolling_broker_profiles([obs(days[0],"E1")],
            verified_exchange_sessions=days,complete_source_sessions=complete,
            as_of_date=days[-1],as_of_timestamp="2026-11-26T12:00:00+05:45",
            windows={"weekly":5})
        p=result["profiles"][0]
        self.assertEqual(p["coverage_ratio"],"0.8")
        self.assertEqual(p["status"],"insufficient_evidence")
        self.assertEqual(p["directional_summary"],"insufficient_evidence")
        self.assertEqual(p["zero_activity_sessions"],3)

    def test_late_available_rows_are_excluded(self):
        days=sessions("2026-11-20",5)
        row=obs(days[0],"E1")
        row["available_at"]="2026-11-27T10:00:00+05:45"
        result=build_rolling_broker_profiles([row],verified_exchange_sessions=days,
            complete_source_sessions=days,as_of_date=days[-1],
            as_of_timestamp="2026-11-26T12:00:00+05:45",windows={"weekly":5})
        self.assertEqual(result["admitted_observation_rows"],0)
        self.assertEqual(result["excluded_observation_rows"],1)
        self.assertEqual(result["profiles"],[])

    def test_buy_sell_persistence_and_broker_participation(self):
        days=sessions("2026-11-20",5)
        rows=[obs(days[0],"E1","BUY","100"),obs(days[1],"E2","BUY","100"),
              obs(days[2],"E3","SELL","100"),obs(days[3],"E4","BUY","100"),
              obs(days[4],"E5","BUY","100"),
              obs(days[0],"OTHER","BUY","100",broker="B18")]
        result=build_rolling_broker_profiles(rows,verified_exchange_sessions=days,
            complete_source_sessions=days,as_of_date=days[-1],
            as_of_timestamp="2026-11-26T12:00:00+05:45",windows={"weekly":5})
        p=next(x for x in result["profiles"] if x["broker_id"]=="B17")
        self.assertEqual(p["positive_net_sessions"],4)
        self.assertEqual(p["negative_net_sessions"],1)
        self.assertEqual(p["broker_participation_ratio"],"0.8333333333333333333333333333")

    def test_twenty_one_and_252_windows_require_full_exchange_calendar(self):
        days=sessions("2025-11-01",252)
        rows=[obs(days[-1],"E1")]
        result=build_rolling_broker_profiles(rows,verified_exchange_sessions=days,
            complete_source_sessions=days,as_of_date=days[-1],
            as_of_timestamp="2026-11-26T12:00:00+05:45",
            windows={"weekly":5,"monthly":21,"yearly":252})
        self.assertEqual([p["window"] for p in result["profiles"]],["weekly","monthly","yearly"])
        self.assertTrue(all(p["status"]=="descriptive_only" for p in result["profiles"]))

    def test_duplicate_natural_key_rejected(self):
        days=sessions("2026-11-20",5)
        row=obs(days[0],"E1")
        with self.assertRaises(BrokerProfileError):
            build_rolling_broker_profiles([row,row],verified_exchange_sessions=days,
                complete_source_sessions=days,as_of_date=days[-1],
                as_of_timestamp="2026-11-26T12:00:00+05:45",windows={"weekly":5})

    def test_complete_sessions_must_be_verified_exchange_sessions(self):
        with self.assertRaises(BrokerProfileError):
            build_rolling_broker_profiles([],verified_exchange_sessions=["2026-11-25"],
                complete_source_sessions=["2026-11-24"],as_of_date="2026-11-25",
                as_of_timestamp="2026-11-26T12:00:00+05:45")

    def test_naive_as_of_timestamp_rejected(self):
        with self.assertRaises(BrokerProfileError):
            build_rolling_broker_profiles([],verified_exchange_sessions=[],
                complete_source_sessions=[],as_of_date="2026-11-25",
                as_of_timestamp="2026-11-26T12:00:00",windows={"weekly":5})


if __name__=="__main__": unittest.main()
