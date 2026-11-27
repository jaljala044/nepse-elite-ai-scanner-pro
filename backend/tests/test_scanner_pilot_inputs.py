import unittest
from app.scanner_pilot_inputs import sector_key
from app.scanner_session_alignment import coverage_report
class PilotTests(unittest.TestCase):
    def test_alias(self):
        self.assertEqual(sector_key("Hydro Power"),sector_key("Hydropower"))
        self.assertEqual(sector_key("Non-Life Insurance"),sector_key("Non Life Insurance"))
    def test_alignment(self):
        r=coverage_report(sessions=["2026-11-19"],stock_dates=["2026-11-19"],benchmark_dates=[],sector_dates=[],broker_dates=[])
        self.assertEqual(r["T+2"]["missing"]["benchmark"],["2026-11-19"])
        self.assertFalse(r["T+2"]["backtest_eligible"])
