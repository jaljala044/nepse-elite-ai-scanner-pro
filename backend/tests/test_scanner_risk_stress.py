import unittest
from app.scanner_risk_stress import stress_holding
from app.scanner_direction_outcomes import evaluate_directions
from app.scanner_common_cohort import METHODS
class RiskTests(unittest.TestCase):
    def test_gap(self):
        r=stress_holding(quantity=2500,entry=490,stop=480,shock_fractions=["0.1"])
        self.assertEqual(r["planned_risk"],"25000")
        self.assertEqual(r["scenarios"][0]["loss_to_planned_risk"],4.9)
        self.assertIsNone(r["scenarios"][0]["exit_fill"])
    def test_duplicate(self):
        row=dict(key=["API","swing","2026-11-19T16:00:00+05:45"],reviews={m:dict(direction="UNKNOWN") for m in METHODS})
        with self.assertRaises(ValueError):
            evaluate_directions(dict(rows=[row,row]),{},"2026-11-20T16:00:00+05:45")
