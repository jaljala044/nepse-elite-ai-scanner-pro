import unittest
from app.scanner_market_regime import rotation_proxy
class RotationTests(unittest.TestCase):
    def test_leading(self):
        self.assertEqual(rotation_proxy([100]*21+list(range(101,121)),[100]*41)["quadrant"],"LEADING")
    def test_short(self):
        self.assertIsNone(rotation_proxy([100],[100])["quadrant"])
