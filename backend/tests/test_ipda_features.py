import unittest
from datetime import date, timedelta
from app.ipda_features import ipda_ranges

class IPDARangeTests(unittest.TestCase):
    def rows(self, n):
        return [dict(date=(date(2025,1,1)+timedelta(days=i)).isoformat(),
                     open=100+i, high=102+i, low=99+i, close=101+i, volume=100)
                for i in range(n)]
    def test_gate(self):
        self.assertEqual(ipda_ranges(self.rows(60))["status"], "unavailable")
    def test_windows(self):
        r=ipda_ranges(self.rows(60),eligible=True)
        self.assertEqual(r["windows"]["20"]["low"],139)
        self.assertEqual(r["windows"]["60"]["high"],161)
        self.assertEqual(r["windows"]["40"]["location"],"premium")
        self.assertIsNone(r["production_score"])
        self.assertEqual(r["action"],"NO TRADE")
    def test_short_history(self):
        r=ipda_ranges(self.rows(20),eligible=True)
        self.assertEqual(r["windows"]["40"]["status"],"insufficient_history")
        self.assertEqual(r["windows"]["60"]["status"],"insufficient_history")
    def test_duplicate(self):
        rows=self.rows(60)
        rows.append(dict(rows[-1]))
        self.assertEqual(ipda_ranges(rows,eligible=True)["status"],"unavailable")
    def test_prefix(self):
        rows=self.rows(61)
        r=ipda_ranges(rows[:-1],eligible=True)
        self.assertEqual(r["windows"]["60"]["end"],rows[59]["date"])
        self.assertTrue(all(z["date"] <= rows[59]["date"] for z in r["windows"]["60"]["zones"]))
