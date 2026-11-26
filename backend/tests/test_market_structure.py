import unittest
from datetime import date, timedelta
from backend.app.market_structure import detect_structure

def bars(values):
    return [dict(date=date(2025,1,1)+timedelta(days=i), open=c, high=h, low=l, close=c, volume=100) for i,(h,l,c) in enumerate(values)]

class MarketStructureTests(unittest.TestCase):
    def test_confirmation_and_break(self):
        rows=bars([(10,8,9),(12,9,11),(11,8,10),(14,11,13)])
        events=detect_structure(rows,1)["events"]
        self.assertTrue(any(e["type"]=="swing_high" and e["date"]=="2025-01-03" for e in events))
        self.assertTrue(any(e["type"]=="bos" and e["date"]=="2025-01-04" for e in events))
    def test_sweep_and_reversal(self):
        rows=bars([(10,8,9),(12,9,11),(11,7,9),(13,8,11),(14,10,13),(10,6,6.5)])
        events=detect_structure(rows,1)["events"]
        self.assertTrue(any(e["type"]=="liquidity_sweep" for e in events))
        self.assertTrue(any(e["type"]=="choch" and e["direction"]=="bearish" for e in events))
    def test_fvg(self):
        rows=bars([(10,8,9),(13,9,12),(15,11,14)])
        self.assertTrue(any(e["type"]=="fvg" and e["lower"]==10 and e["upper"]==11 for e in detect_structure(rows,1)["events"]))
    def test_prefix_invariance(self):
        rows=bars([(10,8,9),(12,9,11),(11,8,10),(14,11,13),(12,9,10)])
        full=detect_structure(rows,1)["events"]
        for n in range(1,len(rows)+1):
            self.assertEqual(detect_structure(rows[:n],1)["events"],[e for e in full if e["date"]<=str(rows[n-1]["date"])])
    def test_invalid(self):
        rows=bars([(10,8,9)])
        rows[0]["high"]=7
        self.assertEqual(detect_structure(rows)["status"],"data_quality_failed")
