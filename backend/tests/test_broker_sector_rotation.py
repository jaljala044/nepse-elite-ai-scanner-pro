import unittest
from app.broker_sector_rotation import BrokerRotationError, build_broker_sector_rotation


def days():
    return [f"2026-11-{n:02d}" for n in range(10,20)]


def row(day, sec, broker, side, amount, evidence):
    return {"session_date":day,"security_id":sec,"broker_id":broker,
        "side":side,"amount":str(amount),"status":"descriptive_only",
        "available_at":day+"T18:00:00+05:45","source_id":"SRC",
        "evidence_id":evidence,"source_payload_sha256":"a"*64}


class SectorRotationTests(unittest.TestCase):
    def call(self, rows, complete=None, calendar=None):
        cal=calendar or days()
        return build_broker_sector_rotation(rows,
            security_sector_map={"S1":"Hydropower","S2":"Commercial Banks"},
            verified_exchange_sessions=cal,complete_source_sessions=complete or cal,
            as_of_date=cal[-1],as_of_timestamp="2026-11-30T12:00:00+05:45",
            current_sessions=5,comparison_sessions=5)

    def test_detects_shift_in_transaction_mix(self):
        cal=days(); rows=[]
        # Prior: bank activity dominates. Current: hydro dominates.
        for i,d in enumerate(cal[:5]):
            rows.append(row(d,"S2","B1","BUY",100,f"P{i}"))
        for i,d in enumerate(cal[5:]):
            rows.append(row(d,"S1","B1","BUY",100,f"C{i}"))
        p=self.call(rows)["brokers"][0]
        self.assertEqual(p["sector_rotation_candidates"]["increased_participation"],["Hydropower"])
        self.assertEqual(p["sector_rotation_candidates"]["decreased_participation"],["Commercial Banks"])

    def test_incomplete_source_window_withholds_result(self):
        cal=days()
        result=self.call([],complete=cal[:4]+cal[5:])
        self.assertEqual(result["status"],"insufficient_evidence")

    def test_incomplete_sessions_are_not_skipped(self):
        cal=days()
        result=self.call([],complete=cal[:4]+cal[5:])
        self.assertEqual(result["prior_coverage"],"0.8")

    def test_late_rows_excluded_by_availability_cutoff(self):
        cal=days(); r=row(cal[-1],"S1","B1","BUY",100,"LATE")
        r["available_at"]="2026-12-01T10:00:00+05:45"
        result=self.call([r])
        self.assertEqual(result["excluded_rows"],1)

    def test_duplicate_natural_key_rejected(self):
        cal=days(); r=row(cal[-1],"S1","B1","BUY",100,"DUP")
        with self.assertRaises(BrokerRotationError): self.call([r,r])

    def test_unmapped_security_is_excluded(self):
        cal=days(); r=row(cal[-1],"UNKNOWN","B1","BUY",100,"U")
        self.assertEqual(self.call([r])["excluded_rows"],1)

    def test_short_calendar_withholds(self):
        cal=days()[:7]
        result=self.call([],calendar=cal)
        self.assertEqual(result["status"],"insufficient_evidence")


if __name__=="__main__": unittest.main()
