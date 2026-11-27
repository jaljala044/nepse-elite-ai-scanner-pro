import unittest
from unittest.mock import patch
from datetime import date
from pydantic import ValidationError
from app.main import BrokerContextRequest,broker_context_research
from app.broker_context_server import server_context

class BrokerContextServerTests(unittest.TestCase):
    def setUp(self):
        self.days=["2026-04-"+str(x) for x in range(20,25)]
        self.ts="2026-04-24T18:00:00+05:45"
        self.request=dict(snapshot={},prices=[],memberships=[],sector_prices=[],decision_time=self.ts,expected_sessions=self.days)
    def test_client_cannot_override_quarantine(self):
        with self.assertRaises(ValidationError):
            BrokerContextRequest(**self.request,quarantine_keys=[])
    def test_missing_calendar_blocks_calculation(self):
        with patch("app.broker_context_server.load_calendar",return_value={}),patch("app.broker_context_server.build_context") as calc:
            result=broker_context_research(BrokerContextRequest(**self.request))
            self.assertEqual(result["reason"],"trusted_calendar_incomplete")
            calc.assert_not_called()
    def test_server_calendar_and_registry(self):
        rows={date.fromisoformat(d):{"scope":"market_wide","verified_at_utc":"2026-04-24T00:00:00Z","status":"verified_open"} for d in self.days}
        with patch("app.broker_context_server.load_calendar",return_value=rows),patch("app.broker_context_server.build_context",return_value={"production_eligible":False}) as calc:
            broker_context_research(BrokerContextRequest(**self.request))
            self.assertEqual(len(calc.call_args.kwargs["quarantine_keys"]),1329)
            self.assertEqual(calc.call_args.kwargs["expected_sessions"],self.days)
            with self.assertRaises(ValueError):
                server_context({},[],[],[],decision_time=self.ts,expected_sessions=[self.days[0],self.days[-1]])
    def test_late_calendar_blocks(self):
        rows={date.fromisoformat(d):{"scope":"market_wide","verified_at_utc":"2026-04-25T00:00:00Z","status":"verified_open"} for d in self.days}
        with patch("app.broker_context_server.load_calendar",return_value=rows):
            self.assertEqual(broker_context_research(BrokerContextRequest(**self.request))["reason"],"trusted_calendar_incomplete")
