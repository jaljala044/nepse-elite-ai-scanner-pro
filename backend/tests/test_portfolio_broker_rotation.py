import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import datetime
from app.broker_memory_store import BrokerMemoryStore
from app.portfolio_broker_rotation import compare_stored_sector_flow

class StoredRotationTests(unittest.TestCase):
    def test_rotation_and_cutoff(self):
        with TemporaryDirectory() as tmp:
            store=BrokerMemoryStore(Path(tmp)/"memory.duckdb")
            for security, amounts in [("A",[(20,80),(80,20)]),("B",[(80,20),(20,80)])]:
                for day,(buy,sell) in zip(["2025-01-05","2025-01-06"],amounts):
                    store.append(dict(as_of_date=day,security_id=security,broker_entity_id="42",
                        window="daily",buy_amount=buy,sell_amount=sell,net_amount=buy-sell,
                        source_ids=["synthetic"],evidence_ids=["synthetic"],payload_hashes=["synthetic"],
                        status="descriptive_only"),idempotency_key=security+day,
                        available_at=datetime.fromisoformat(day+"T16:00:00+05:45"))
            args=dict(store=store,broker_entity_id="42",previous_sessions=["2025-01-05"],
                current_sessions=["2025-01-06"],sector_by_security={"A":"Hydro","B":"Finance"})
            result=compare_stored_sector_flow(**args,assessment_time="2025-01-06T17:00:00+05:45")
            self.assertEqual(result["coverage"],1)
            self.assertEqual(result["sectors"][1]["current_net"],60)
            self.assertAlmostEqual(result["sectors"][1]["imbalance_change"],1.2)
            result=compare_stored_sector_flow(**args,assessment_time="2025-01-06T15:00:00+05:45")
            self.assertEqual(result["status"],"UNKNOWN")
            self.assertEqual(result["coverage"],.5)
