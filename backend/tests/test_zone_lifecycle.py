import unittest
from app.zone_lifecycle import zone_lifecycle

def rows():
    values = [(9,10,8,9),(10,13,9,12),(14,15,12,14),
              (13,14,12,13),(12,13,11,12),(11,12,10,11),(10,11,9,9.5)]
    return [dict(date=f"2025-01-{i+1:02}",open=o,high=h,low=l,close=c,volume=100)
            for i,(o,h,l,c) in enumerate(values)]

def gap(bars):
    return next(z for z in zone_lifecycle(bars,eligible=True)["zones"]
                if z["zone_id"]=="fvg:bullish:2025-01-03")

class ZoneLifecycleTests(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(zone_lifecycle(rows())["status"],"unavailable")
    def test_progression(self):
        r=rows()
        for n,state in [(3,"untested"),(4,"touched"),(5,"partially_mitigated"),
                        (6,"fully_mitigated"),(7,"invalidated")]:
            self.assertEqual(gap(r[:n])["state"],state)
        self.assertEqual(gap(r[:5])["max_penetration"],0.5)
        self.assertEqual(gap(r)["touch_count"],3)
    def test_invalidation_precedence(self):
        r=rows()[:3]+[dict(date="2025-01-04",open=12,high=13,low=9,close=9,volume=100)]
        self.assertEqual(gap(r)["state"],"invalidated")
        self.assertEqual(gap(r)["touch_count"],0)
    def test_duplicate(self):
        r=rows()
        self.assertEqual(zone_lifecycle(r+[r[-1]],eligible=True)["status"],"unavailable")
    def test_prefix_history(self):
        r=rows()
        full=gap(r)["history"]
        for n in range(3,len(r)+1):
            self.assertEqual(gap(r[:n])["history"],[e for e in full if e["date"]<=r[n-1]["date"]])
