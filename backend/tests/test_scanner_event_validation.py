import unittest
from app.scanner_event_validation import review_events,idpat_proxy_direction
class EventTests(unittest.TestCase):
    def test_alias(self):
        e=dict(session_date="2026-11-18",direction="bullish",reference_level=100)
        rows=[dict(date="2026-11-18",close=105),dict(date="2026-11-19",close=99)]
        r=review_events([dict(e,event="sos"),dict(e,event="jump_across_creek")],rows,"2026-11-19")
        self.assertEqual(r["unique_count"],1)
        self.assertEqual(r["active_count"],0)
    def test_conflict(self):
        self.assertEqual(idpat_proxy_direction(["SHAKEOUT_PROXY","FAILED_BREAKOUT_PROXY"]),"UNKNOWN")
        self.assertEqual(idpat_proxy_direction(["BREAKOUT_PROXY"]),"BULLISH")
