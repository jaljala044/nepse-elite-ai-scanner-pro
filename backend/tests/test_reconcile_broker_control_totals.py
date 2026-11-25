import csv
import json
import tempfile
import unittest
from pathlib import Path

from reconcile_broker_control_totals import build_immutable_report


class ImmutableBrokerReportTests(unittest.TestCase):
    def test_report_pins_source_hashes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            party = root / "party.csv"
            controls = root / "controls.csv"
            output = root / "report.json"
            with party.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "source_id","trade_date","contract_id","side","amount","quantity"])
                writer.writeheader()
                writer.writerow({"source_id":"src","trade_date":"2026-11-24","contract_id":"C1",
                                 "side":"buy","amount":"100.10","quantity":"1"})
                writer.writerow({"source_id":"src","trade_date":"2026-11-24","contract_id":"C1",
                                 "side":"sell","amount":"100.10","quantity":"1"})
            with controls.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "source_id","trade_date","contract_count","gross_amount","party_observation_count"])
                writer.writeheader()
                writer.writerow({"source_id":"src","trade_date":"2026-11-24","contract_count":1,
                                 "gross_amount":"100.10","party_observation_count":2})
            first = build_immutable_report([party], controls, output)
            second = build_immutable_report([party], controls, output)
            self.assertEqual(first["report_sha256"], second["report_sha256"])
            self.assertEqual(first["reconciliation"]["failed_source_dates"], 0)
            self.assertEqual(len(first["party_input_files"][0]["sha256"]), 64)
            self.assertFalse(first["canonical_promotion_allowed"])
            self.assertEqual(json.loads(output.read_text())["report_sha256"], first["report_sha256"])

    def test_existing_output_with_different_content_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            party = root / "party.csv"
            controls = root / "controls.csv"
            output = root / "report.json"
            party.write_text("source_id,trade_date,contract_id,side,amount,quantity\n", encoding="utf-8")
            controls.write_text("source_id,trade_date,contract_count,gross_amount,party_observation_count\n", encoding="utf-8")
            output.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "different content"):
                build_immutable_report([party], controls, output)


if __name__ == "__main__":
    unittest.main()
