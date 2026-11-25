import csv
import tempfile
import unittest
from pathlib import Path

from report_broker_identity_coverage import build_broker_identity_coverage


class BrokerIdentityCoverageReportTests(unittest.TestCase):
    def test_coverage_uses_observation_and_gross_amount_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.csv"
            fields = ["trade_date","symbol","side","amount","quantity","identity_status",
                      "broker_entity_id","source_id","contract_id","source_payload_sha256",
                      "source_row_number","identity_evidence_ids"]
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"trade_date":"2026-11-24","symbol":"AAA","side":"buy","amount":"100.10",
                    "quantity":"1","identity_status":"verified","broker_entity_id":"B1","source_id":"src",
                    "contract_id":"C1","source_payload_sha256":"a"*64,"source_row_number":2,
                    "identity_evidence_ids":"[\"e1\"]"})
                writer.writerow({"trade_date":"2026-11-24","symbol":"AAA","side":"buy","amount":"50",
                    "quantity":"1","identity_status":"unmapped","broker_entity_id":"","source_id":"src",
                    "contract_id":"C2","source_payload_sha256":"b"*64,"source_row_number":3,
                    "identity_evidence_ids":"[]"})
            report = build_broker_identity_coverage(path)
            row = report["coverage"][0]
            self.assertEqual(row["party_observation_count"], 2)
            self.assertEqual(row["verified_observation_count"], 1)
            self.assertEqual(row["unresolved_observation_count"], 1)
            self.assertEqual(row["total_amount"], "150.10")
            self.assertEqual(row["verified_amount"], "100.10")
            self.assertFalse(report["promotion_allowed"])
            self.assertEqual(len(report["source_file_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
