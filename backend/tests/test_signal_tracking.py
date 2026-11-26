import unittest
from app.signal_tracking import freeze_signal,verify_signal
class SignalTests(unittest.TestCase):
    def fixture(self):
        return dict(symbol="TEST",decision_time="2025-01-01T12:00:00Z",horizon="swing",action="NO TRADE",methodology="research_v1",evidence=[{"evidence_id":"synthetic","available_at":"2025-01-01T11:00:00Z"}],details={"score":None})
    def test_hash_and_tamper(self):
        args=self.fixture()
        a=freeze_signal(**args)
        self.assertEqual(a,freeze_signal(**args))
        self.assertTrue(verify_signal(a))
        a["record"]["action"]="BUY"
        self.assertFalse(verify_signal(a))
    def test_future_evidence(self):
        args=self.fixture()
        args["evidence"][0]["available_at"]="2025-01-02T11:00:00Z"
        with self.assertRaises(ValueError): freeze_signal(**args)
    def test_unauthorized_buy(self):
        args=self.fixture()
        args["action"]="BUY"
        with self.assertRaises(ValueError): freeze_signal(**args)
