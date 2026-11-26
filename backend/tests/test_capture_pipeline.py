import json
import tempfile
import unittest
from pathlib import Path

from app.capture_pipeline import capture_normalize_and_build_features, normalize_json_payload\nfrom app.evidence_store import load_evidence_records


class CapturePipelineIntegrationTests(unittest.TestCase):
    def manifest_args(self):
        return {
            "source_id": "synthetic-fixture",
            "source_url": "https://example.invalid/fixture.json",
            "request_method": "GET",
            "request_metadata": {"fixture": "integration-test"},
            "requested_at": "2026-11-24T10:00:00Z",
            "received_at": "2026-11-24T10:00:05Z",
            "claimed_session_date": "2026-11-24",
            "fetch_id": "fixture-001",
        }

    def test_capture_to_normalization_to_point_in_time_features(self):
        rows = [
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
             "close":11,"previous_close":10,"volume":100,
             "available_at":"2099-01-01T00:00:00Z"},
            {"record_type":"ohlcv","symbol":"BBB","session_date":"2026-11-23",
             "close":9,"previous_close":10,"volume":200},
            {"record_type":"broker","side":"buy","amount":500,
             "identity_status":"unmapped","broker_entity_id":None},
        ]
        payload = json.dumps(rows, separators=(",", ":")).encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            result = capture_normalize_and_build_features(
                payload, storage_root=tmp, decision_time="2026-11-24T12:00:00Z",
                expected_symbols=["AAA","BBB","CCC"], **self.manifest_args()
            )
            self.assertEqual(Path(result["capture"]["payload_path"]).read_bytes(), payload)\n            self.assertEqual(result["capture"]["evidence_status"], "stored_review_required")\n            self.assertFalse(result["capture"]["production_eligible"])\n            evidence = load_evidence_records(database_path=Path(tmp) / "evidence.duckdb")\n            self.assertEqual(len(evidence), 3)\n            self.assertTrue(all(row["source_validation_status"] == "review_required" for row in evidence))
            self.assertEqual(result["capture"]["payload_bytes"], len(payload))
            self.assertEqual(result["normalized_record_count"], 3)
            features = result["feature_snapshot"]
            self.assertEqual(features["included_input_count"], 3)
            self.assertEqual(features["market_breadth"]["advancing"], 1)
            self.assertEqual(features["market_breadth"]["declining"], 1)
            self.assertEqual(features["market_breadth"]["eligible_symbols"], 3)
            self.assertEqual(features["broker_participation"]["unmapped_or_unverified_rows"], 1)
            self.assertTrue(features["point_in_time_eligible"])

    def test_receipt_after_decision_time_is_excluded(self):
        payload = b'[{"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-24","close":10,"previous_close":9,"volume":1}]'
        args = self.manifest_args()
        args["received_at"] = "2026-11-24T13:00:00Z"
        with tempfile.TemporaryDirectory() as tmp:
            result = capture_normalize_and_build_features(
                payload, storage_root=tmp, evidence_database_path=Path(tmp) / "evidence.duckdb",\n                decision_time="2026-11-24T12:00:00Z", **args
            )
            self.assertEqual(result["feature_snapshot"]["included_input_count"], 0)
            self.assertEqual(result["feature_snapshot"]["market_breadth"]["observed_symbols"], 0)

    def test_normalizer_overwrites_untrusted_available_at(self):
        payload = b'[{"record_type":"broker","side":"sell","amount":50,"identity_status":"unmapped","available_at":"2099-01-01T00:00:00Z"}]'
        rows = normalize_json_payload(payload, "2026-11-24T10:00:00Z")
        self.assertEqual(rows[0]["available_at"], "2026-11-24T10:00:00Z")

    def test_unknown_record_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_json_payload(b'[{"record_type":"mystery"}]', "2026-11-24T10:00:00Z")


if __name__ == "__main__":
    unittest.main()
