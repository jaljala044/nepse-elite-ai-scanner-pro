import unittest
from app.scanner_broker_rotation_bridge import sector_rotation
class RotationTests(unittest.TestCase):
    def test_rotation(self):
        t="2026-11-19T17:00:00+05:45"
        m=dict(symbol="API",sector="Hydro Power",status="verified",source_id="synthetic",available_at="2026-11-16T17:00:00+05:45")
        rows=[dict(symbol="API",session=d,broker_ids=[1],coverage_complete=True,status="verified",source_id="synthetic",available_at=d+"T16:00:00+05:45",buy_turnover=b,sell_turnover=s) for d,b,s in [("2026-11-17",20,100),("2026-11-18",100,20)]]
        args=dict(memberships=[m],previous_sessions=["2026-11-17"],current_sessions=["2026-11-18"],cohort=[1],decision_time=t)
        self.assertEqual(sector_rotation(records=rows,**args)["sectors"][0]["current_net"],"80")
        self.assertEqual(sector_rotation(records=rows[:1],**args)["status"],"UNKNOWN")
