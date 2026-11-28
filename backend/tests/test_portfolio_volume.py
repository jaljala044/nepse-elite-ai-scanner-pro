import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from app.portfolio_volume import portfolio_volume

class PortfolioVolumeTests(unittest.TestCase):
    def setUp(self):
        self.end = date(2026, 11, 20)
        self.cutoff = "2026-11-21T12:00:00Z"
        self.calendar = {}
        self.reviewed = {}
        for i in range(20):
            day = self.end - timedelta(days=i)
            self.calendar[day] = {"status":"verified_open","scope":"all_securities",
                                  "verified_at_utc":"2026-11-21T00:00:00Z"}
            self.reviewed[("AAA",str(day))] = {
                "symbol":"AAA","date":str(day),"security_id":"id1","instrument_type":"equity",
                "security_status":"active","lifecycle_evidence_id":"l1","session_status":"verified_open",
                "session_evidence_id":"s1","source_id":"nepse","evidence_id":"e1",
                "source_payload_sha256":"a"*64,"price_basis_reviewed":True,
                "price_basis_status":"verified_unadjusted_no_actions","corporate_action_status":"clear",
                "corporate_action_evidence_id":"c1","open":100,"high":105,"low":95,"close":101,
                "volume":1000,"available_at":"2026-11-21T01:00:00Z",
                "canonical_promotion_allowed":True,"finality_status":"final",
            }

    def run_window(self):
        return portfolio_volume("AAA",self.end,self.reviewed,self.calendar,self.cutoff)

    def test_complete_window(self):
        result=self.run_window()
        self.assertEqual(result["status"],"research_only")
        self.assertEqual(Decimal(result["average_daily_quantity"]),Decimal(1000))
        self.assertEqual(len(result["rows"]),20)
        self.assertFalse(result["production_eligible"])

    def test_missing_calendar(self):
        del self.calendar[self.end]
        self.assertIsNone(self.run_window()["average_daily_quantity"])

    def test_missing_record(self):
        del self.reviewed[("AAA",str(self.end))]
        self.assertEqual(self.run_window()["reason"],"canonical_record_missing")

    def test_unverified_finality(self):
        self.reviewed[("AAA",str(self.end))]["finality_status"]="provisional"
        self.assertEqual(self.run_window()["reason"],"finality_unverified")

    def test_future_availability(self):
        self.reviewed[("AAA",str(self.end))]["available_at"]="2026-11-22T00:00:00Z"
        self.assertEqual(self.run_window()["status"],"unavailable")

    def test_project_calendar_not_admitted(self):
        self.calendar[self.end]["status"]="project_accepted_open"
        self.assertEqual(self.run_window()["status"],"unavailable")

    def test_identity_change(self):
        self.reviewed[("AAA",str(self.end))]["security_id"]="id2"
        self.assertEqual(self.run_window()["reason"],"security_identity_changed")

    def test_endpoint_universe_gate(self):
        from app.main import portfolio_volume_endpoint
        with patch("app.main.EQUITY_UNIVERSE",None):
            self.assertEqual(portfolio_volume_endpoint("AAA",self.end)["reason"],"equity_universe_gate")
