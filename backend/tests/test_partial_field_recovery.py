import unittest
from app.partial_field_recovery import build_partial_view

class PartialFieldRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.key={"symbol":"RAWA","date":"2026-04-29"}
        self.candidate={**self.key,"open":"610","high":"610","low":"587","close":"610","volume":"2840","target_errors":0,"contracts":58}
        self.chron={**self.key,"open_match":True,"close_match":False,"errors":0,"unique_contracts":True,"timestamp_rows":58,"timestamp_open_candidate":"610"}
    def test_partial_stays_out_of_canonical(self):
        row=build_partial_view([self.key],[self.candidate],[self.chron])["records"][0]
        self.assertEqual(row["research_candidates"]["open"],"610")
        self.assertIsNone(row["research_candidates"]["close"])
        self.assertTrue(all(v is None for v in row["canonical_fields"].values()))
        self.assertFalse(row["scanner_eligible"])
        self.assertFalse(row["admission_allowed"])
    def test_missing_and_duplicate_evidence(self):
        row=build_partial_view([self.key],[],[])["records"][0]
        self.assertTrue(all(v is None for v in row["research_candidates"].values()))
        with self.assertRaises(ValueError):
            build_partial_view([self.key],[self.candidate,self.candidate],[])
    def test_claimed_match_with_wrong_price(self):
        row=build_partial_view([self.key],[self.candidate],[dict(self.chron,timestamp_open_candidate="999")])["records"][0]
        self.assertIsNone(row["research_candidates"]["open"])
    def test_unvalidated_candidate(self):
        row=build_partial_view([self.key],[dict(self.candidate,target_errors=1)],[self.chron])["records"][0]
        self.assertTrue(all(v is None for v in row["research_candidates"].values()))
