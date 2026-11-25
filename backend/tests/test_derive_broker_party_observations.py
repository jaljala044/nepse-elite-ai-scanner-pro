from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from derive_broker_party_observations import derive


class BrokerPartyDerivationTests(unittest.TestCase):
    def test_derives_two_unmapped_execution_channel_observations_per_contract(self):
        payload = (
            "date,transaction_no,symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-19,1001,ABC,08,12,2,10.5,21.0\n"
            "2026-11-19,1002,XYZ,12,08,3,20,60\n"
        ).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "floorsheet.csv"
            path.write_bytes(payload)
            parties, report = derive(
                path,
                source_id="test-source",
                expected_sha256=hashlib.sha256(payload).hexdigest(),
                expected_date="2026-11-19",
                expected_rows=2,
            )

        self.assertEqual(len(parties), 4)
        self.assertEqual(report["contract_count"], 2)
        self.assertEqual(report["party_observation_count"], 4)
        self.assertEqual(report["distinct_broker_codes"], 2)
        self.assertEqual(report["total_quantity_once_per_contract"], "5")
        self.assertEqual(report["gross_amount_once_per_contract"], "81.0")
        self.assertEqual(report["quantity_rate_amount_exception_count"], 0)
        self.assertEqual({row["identity_status"] for row in parties}, {"unmapped"})
        self.assertEqual({row["broker_entity_id"] for row in parties}, {None})
        self.assertEqual({row["source_broker_code"] for row in parties}, {"08", "12"})
        self.assertEqual(report["aggregation"]["input_party_observation_rows"], 4)

    def test_rejects_source_hash_mismatch(self):
        payload = (
            "date,transaction_no,symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-19,1001,ABC,8,12,2,10.5,21.0\n"
        ).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "floorsheet.csv"
            path.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                derive(
                    path,
                    source_id="test-source",
                    expected_sha256="0" * 64,
                    expected_date="2026-11-19",
                    expected_rows=1,
                )

    def test_rejects_duplicate_contract_ids(self):
        payload = (
            "date,transaction_no,symbol,buyer,seller,quantity,rate,amount\n"
            "2026-11-19,1001,ABC,8,12,2,10.5,21.0\n"
            "2026-11-19,1001,XYZ,12,8,3,20,60\n"
        ).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "floorsheet.csv"
            path.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "duplicate transaction_no"):
                derive(
                    path,
                    source_id="test-source",
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_date="2026-11-19",
                    expected_rows=2,
                )


if __name__ == "__main__":
    unittest.main()
