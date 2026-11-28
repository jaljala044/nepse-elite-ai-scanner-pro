import unittest
from datetime import date,timedelta
from unittest.mock import patch
from app.broker_mode_research import mode_research
from app.broker_context_integration import POLICY

class ModeResearchTests(unittest.TestCase):
    def fixture(self,count):
        days=[(date(2026,4,1)+timedelta(days=i)).isoformat() for i in range(count)]
        ts=days[-1]+"T18:00:00+05:45"
        evidence=dict(status="verified",source_id="synthetic",source_payload_sha256="a"*64,available_at=ts)
        daily=[dict(session_date=d,buy_amount="100",sell_amount="20",net_amount="80",gross_amount="120",broker_participation=".2") for d in days]
        snap=dict(policy=POLICY,as_of_timestamp=ts,as_of_date=days[-1],profiles=[dict(security_id="S1",broker_id="B1",requested_sessions=count,expected_sessions=count,complete_source_sessions=count,status="descriptive_only",coverage_ratio="1",daily=daily,buy_amount=str(100*count),sell_amount=str(20*count))])
        prices=[dict(evidence,security_id="S1",symbol="TEST",session_date=d,open=100+i,high=102+i,low=99+i,close=101+i,volume=100+i*10) for i,d in enumerate(days)]
        memberships=[dict(evidence,security_id="S1",symbol="TEST",sector_code="H",effective_from=days[0],effective_to=None)]
        sector=[dict(evidence,sector_code="H",session_date=d,close=1000+i) for i,d in enumerate(days)]
        cal={date.fromisoformat(d):dict(scope="market_wide",status="verified_open",verified_at_utc=d+"T06:00:00Z") for d in days}
        return [snap,prices,memberships,sector],dict(decision_time=ts,expected_sessions=days),cal
    def test_both_modes_never_promote(self):
        for mode,count in [("swing",5),("positional",21)]:
            args,kw,cal=self.fixture(count)
            with self.subTest(mode=mode),patch("app.broker_context_server.load_calendar",return_value=cal):
                r=mode_research(*args,mode=mode,**kw)
                self.assertEqual(r["evaluated_profiles"],1)
                self.assertEqual(r["reason"],"historical_identity_not_certified")
                self.assertIsNone(r["confirmation"])
                self.assertIsNone(r["score"])
                self.assertEqual(r["profiles"],[])
                self.assertFalse(r["signals_enabled"])
                self.assertFalse(r["production_eligible"])
    def test_wrong_window_and_unknown_mode(self):
        args,kw,_=self.fixture(5)
        self.assertEqual(mode_research(*args,mode="positional",**kw)["reason"],"mode_session_count_mismatch")
        with self.assertRaises(ValueError): mode_research(*args,mode="invalid",**kw)
    def test_missing_calendar(self):
        args,kw,_=self.fixture(21)
        with patch("app.broker_context_server.load_calendar",return_value={}):
            self.assertEqual(mode_research(*args,mode="positional",**kw)["reason"],"trusted_calendar_candidate_missing")
    def test_quarantine_real_registry_both_modes(self):
        import json
        from app.broker_context_server import ROOT
        q=json.loads((ROOT/"data/reference/p443_equity_quarantine.json").read_text())["records"]
        for mode,count in [("swing",5),("positional",21)]:
            args,kw,cal=self.fixture(count)
            # Use a known quarantined date as first day in the otherwise synthetic window.
            target=next(r for r in q if r["date"]=="2026-04-24")
            days=[(date.fromisoformat(target["date"])+timedelta(days=i)).isoformat() for i in range(count)]
            ts=days[-1]+"T18:00:00+05:45"
            snap,prices,memberships,sector=args
            snap.update(as_of_date=days[-1],as_of_timestamp=ts)
            for i,d in enumerate(days):
                snap["profiles"][0]["daily"][i]["session_date"]=d
                prices[i].update(symbol=target["symbol"],session_date=d,available_at=ts)
                sector[i].update(session_date=d,available_at=ts)
            memberships[0].update(symbol=target["symbol"],effective_from=days[0],available_at=ts)
            cal={date.fromisoformat(d):dict(scope="market_wide",status="verified_open",verified_at_utc=d+"T06:00:00Z") for d in days}
            with patch("app.broker_context_server.load_calendar",return_value=cal):
                r=mode_research(*args,mode=mode,decision_time=ts,expected_sessions=days)
                self.assertEqual(r["reason"],"no_eligible_profiles")
                self.assertFalse(r["score_eligible"])
