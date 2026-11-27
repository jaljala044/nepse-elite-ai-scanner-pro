"""Synthetic reconstruction regression tests; never evidence of market activity."""
import unittest
from unittest.mock import MagicMock, patch
from app.broker_daily_history import BrokerDailyHistoryStore
from app.broker_memory_reconstruction import reconstruct_broker_memory

class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.ledger=MagicMock(spec=BrokerDailyHistoryStore)
        self.days=["2026-11-23","2026-11-24","2026-11-25","2026-11-26"]
        self.ledger.complete_sessions_as_of.return_value=self.days
        self.rows=[dict(security_id="S1",symbol="ABC",broker_id="B1",session_date=d,
            side=side,amount=amount,quantity=qty,source_id="fixture",evidence_id=d+side,
            source_payload_sha256="a"*64,batch_id=d,available_at=d+"T10:00:00+00:00",
            coverage_ratio="1",source_row_count=1)
            for d in self.days for side,amount,qty in [("BUY","1000","10"),("SELL","400","4")]]
        self.ledger.observations_as_of.return_value=self.rows
    def run_rebuild(self,holds=None):
        with patch("app.broker_memory_reconstruction.configured_holds",return_value=holds or {}):
            return reconstruct_broker_memory(self.ledger,as_of_date="2026-11-26",as_of_timestamp="2026-11-26T20:00:00+00:00")
    def test_daily_totals_and_lineage(self):
        result=self.run_rebuild()
        self.assertEqual(result["admitted_observations"],8)
        self.assertEqual(len(result["snapshots"]),1)
        snap=result["snapshots"][0]
        self.assertEqual(snap["window"],"daily")
        self.assertEqual(snap["net_amount"],"600")
        self.assertEqual(snap["net_quantity"],"6")
        self.assertEqual(snap["constituent_sessions"],["2026-11-26"])
        self.assertEqual(len(snap["constituent_lineage"]),2)
        self.assertFalse(result["promotion_allowed"])
        self.assertEqual(result["persisted"],0)
        self.assertEqual(len(result["withheld"]),3)
    def test_held_observation(self):
        with self.assertRaises(ValueError):self.run_rebuild({("ABC","2026-11-25"):"HOLD"})
    def test_duplicate(self):
        self.rows.append(self.rows[0])
        with self.assertRaises(ValueError):self.run_rebuild()
    def test_incomplete_session(self):
        self.ledger.complete_sessions_as_of.return_value=self.days[:-1]
        with self.assertRaises(ValueError):self.run_rebuild()
    def test_no_observations(self):
        self.ledger.observations_as_of.return_value=[]
        result=self.run_rebuild()
        self.assertEqual(result["snapshots"],[])
        self.assertEqual(result["persisted"],0)
if __name__=="__main__":unittest.main()
