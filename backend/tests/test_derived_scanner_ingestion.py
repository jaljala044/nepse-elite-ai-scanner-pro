import unittest,hashlib
from app.derived_scanner_ingestion import load_candidate,horizon_eligibility,RELEASE
class DerivedTests(unittest.TestCase):
    def test_blob(self):
        b=b"Date,Open,High,Low,Close,Volume\n2026-01-01,10,11,9,10,100\n"
        h=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
        m=("symbol,derived_blob_sha,rows\nABC,"+h+",1\n").encode()
        self.assertEqual(load_candidate("ABC",m,b,RELEASE)["audit"]["rows"],1)
        with self.assertRaises(ValueError): load_candidate("ABC",m,b+b" ",RELEASE)
    def test_gate(self):
        r=horizon_eligibility(horizon="swing",expected_sessions=[],verified_bars=[],benchmark_dates=[],broker_dates=[],action_basis_verified=False)
        self.assertFalse(r["candidate_ready"])
