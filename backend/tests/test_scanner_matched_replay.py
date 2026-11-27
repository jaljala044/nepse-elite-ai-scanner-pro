import unittest
from unittest.mock import patch
from app.scanner_matched_replay import matched_replay
from app.scanner_common_cohort import METHODS
class ReplayTests(unittest.TestCase):
    @patch("app.scanner_matched_replay.replay_research")
    def test_unknown(self,replay):
        t="2026-11-19T17:00:00+05:45"
        replay.return_value={"reviews":[{"reviews":{m:{"direction":"UNKNOWN"} for m in METHODS}}]}
        r=matched_replay([dict(symbol="API",horizon="T+2",decision_time=t)],{},t)
        self.assertEqual(r["cohort"]["decision_count"],1)
        self.assertTrue(all(v["withheld"]==1 for v in r["outcomes"]["metrics"].values()))
    def test_future(self):
        with self.assertRaises(ValueError):
            matched_replay([dict(symbol="API",horizon="T+2",decision_time="2026-11-20T17:00:00+05:45")],{},"2026-11-19T17:00:00+05:45")
