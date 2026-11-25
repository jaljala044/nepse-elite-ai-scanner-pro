import hashlib
import json
import unittest
from app.source_adapter_profile import (
    SourceAdapterProfile, header_fingerprint, verify_adapter_profile,
)


class SourceAdapterProfileTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"Date,Symbol,Close\n2026-11-24,NABIL,105\n"
        self.payload_hash = hashlib.sha256(self.payload).hexdigest()
        self.header_hash = header_fingerprint(self.payload)

    def profile(self, **changes):
        values = dict(
            source_id="publisher-a", publisher_name="Publisher A", schema_version="1",
            mapping={"session_date": "Date", "symbol": "Symbol", "close": "Close"},
            sample_payload_sha256=self.payload_hash, sample_header_sha256=self.header_hash,
            reviewer="data-reviewer", reviewed_at="2026-11-25T10:00:00Z",
            evidence_id="REVIEW-1",
        )
        values.update(changes)
        return SourceAdapterProfile(**values)

    def test_exact_reviewed_sample_verifies_profile(self):
        result = verify_adapter_profile(self.profile(), self.payload)
        self.assertTrue(result["mapping_verified_for_exact_sample"])

    def test_different_payload_does_not_verify_exact_sample(self):
        result = verify_adapter_profile(self.profile(), self.payload + b"\n")
        self.assertFalse(result["payload_hash_match"])
        self.assertFalse(result["mapping_verified_for_exact_sample"])

    def test_header_change_does_not_verify(self):
        result = verify_adapter_profile(self.profile(), b"Date,Symbol,Close,Extra\n")
        self.assertFalse(result["header_hash_match"])

    def test_naive_review_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.profile(reviewed_at="2026-11-25T10:00:00")

    def test_missing_review_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError, "evidence are required"):
            self.profile(evidence_id="")

    def test_invalid_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.profile(sample_payload_sha256="not-a-hash")



    def test_mapping_must_reference_headers_in_reviewed_sample(self):
        bad = self.profile(mapping={"session_date": "Date", "symbol": "Ticker"})
        result = verify_adapter_profile(bad, self.payload)
        self.assertFalse(result["mapping_headers_present"])
        self.assertFalse(result["mapping_verified_for_exact_sample"])

    def test_duplicate_source_header_mapping_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct source header"):
            self.profile(mapping={"symbol": "Date", "session_date": "Date"})


if __name__ == "__main__":
    unittest.main()
