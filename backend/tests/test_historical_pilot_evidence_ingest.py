import hashlib
import unittest
from app.historical_pilot_evidence_ingest import ingest_captured_evidence_csv

class EvidenceIngestTests(unittest.TestCase):
    def test_explicit_calendar_mapping_preserves_raw_provenance(self):
        raw=b"date,open,kind\n2025-01-02,true,regular\n"
        digest=hashlib.sha256(raw).hexdigest()
        manifest={"capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","available_at":"2025-01-02T12:00:00+05:45","pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}
        package={"status":"CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION","capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","manifest_sha256":"manifest-hash","validation_report":{"verified_pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}}
        out=ingest_captured_evidence_csv(dataset_kind="official_market_calendar",package_report=package,manifest=manifest,payloads={"P1":raw},column_map={"session_date":"date","is_open":"open","session_type":"kind"},decision_cutoff="2025-01-03T00:00:00+05:45")
        self.assertEqual(out["status"],"INGESTED",msg=repr(out["errors"]))
        self.assertEqual(out["rows"][0]["session_date"],"2025-01-02")
        self.assertEqual(out["rows"][0]["payload_id"],"P1")
        self.assertFalse(out["backtest_admission_allowed"])

    def test_column_map_missing_required_key_with_extra_key_is_rejected(self):
        raw=b"date,open,kind,extra\\n2025-01-02,true,regular,x\\n"
        digest=hashlib.sha256(raw).hexdigest()
        manifest={"capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","available_at":"2025-01-02T12:00:00+05:45","pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}
        package={"status":"CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION","capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","manifest_sha256":"manifest-hash","validation_report":{"verified_pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}}
        with self.assertRaisesRegex(ValueError,"column_map_must_cover_required_semantic_fields"):
            ingest_captured_evidence_csv(
                dataset_kind="official_market_calendar",package_report=package,
                manifest=manifest,payloads={"P1":raw},
                column_map={"is_open":"open","session_type":"kind","extra_field":"extra"},
                decision_cutoff="2025-01-03T00:00:00+05:45")

    def test_column_map_duplicate_or_blank_source_column_is_rejected(self):
        raw=b"date,open,kind\\n2025-01-02,true,regular\\n"
        digest=hashlib.sha256(raw).hexdigest()
        manifest={"capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","available_at":"2025-01-02T12:00:00+05:45","pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}
        package={"status":"CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION","capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1","manifest_sha256":"manifest-hash","validation_report":{"verified_pages":[{"page_number":1,"payload_id":"P1","raw_sha256":digest}]}}
        base={"session_date":"date","is_open":"open","session_type":"kind"}
        for candidate in (
            {"session_date":"date","is_open":"open","session_type":"open"},
            {"session_date":"date","is_open":" ","session_type":"kind"},
        ):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(ValueError,"column_map_must_cover_required_semantic_fields"):
                ingest_captured_evidence_csv(
                    dataset_kind="official_market_calendar",package_report=package,
                    manifest=manifest,payloads={"P1":raw},column_map=candidate,
                    decision_cutoff="2025-01-03T00:00:00+05:45")

    def test_unknown_dataset_schema_rejected(self):
        with self.assertRaises(ValueError):
            ingest_captured_evidence_csv(dataset_kind="unknown",package_report={},manifest={},payloads={},column_map={},decision_cutoff="2025-01-03T00:00:00+05:45")

if __name__=="__main__":unittest.main()
