import unittest
from app.native_independent_scanners import momentum

class NativeMomentumTests(unittest.TestCase):
    def test_warmup(self):
        self.assertIsNone(momentum([100]*10)["rsi14"])
        self.assertIsNone(momentum([100]*26)["histogram"])
    def test_flat(self):
        r=momentum([100]*40)
        self.assertEqual(r["rsi14"],50)
        self.assertEqual(r["histogram"],0)
    def test_rising(self):
        self.assertEqual(momentum(list(range(1,41)))["rsi14"],100)
