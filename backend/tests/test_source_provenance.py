import unittest
from app.source_provenance import SourceProvenance, build_batch_provenance


class SourceProvenanceTests(unittest.TestCase):
    def source(self, **kwargs):
        values = dict(source_id="publisher-a", publisher_name="Example Publisher",
                      source_url="https://example.invalid/data", provenance_class="publisher",
                      rights_state="unknown", rights_evidence_id=None, attribution_required=None,
                      redistribution_allowed=None, terms_reviewed_at=None)
        values.update(kwargs)
        return SourceProvenance(**values)

    def test_unknown_rights_never_clear_training_or_redistribution(self):
        result = build_batch_provenance(self.source(), payload=b"abc",
                                        captured_at="2026-11-25T10:00:00+05:45",
                                        acquired_by="operator", acquisition_method="manual_export")
        self.assertFalse(result["training_eligibility"]["rights_clearance"])
        self.assertFalse(result["training_eligibility"]["redistribution_allowed"])
        self.assertTrue(result["training_eligibility"]["requires_human_rights_review"])

    def test_permission_requires_explicit_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires rights evidence"):
            self.source(rights_state="redistribution_permitted")

    def test_inconsistent_permission_flag_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit permitted"):
            self.source(redistribution_allowed=True)

    def test_payload_hash_and_capture_metadata(self):
        result = build_batch_provenance(self.source(rights_state="research_only"),
                                        payload=b"abc", captured_at="2026-11-25T04:15:00Z",
                                        acquired_by="operator", acquisition_method="download")
        self.assertEqual(result["capture"]["payload_sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(result["capture"]["payload_bytes"], 3)

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            build_batch_provenance(self.source(), payload=b"x", captured_at="2026-11-25T04:15:00",
                                   acquired_by="operator", acquisition_method="download")


if __name__ == "__main__":
    unittest.main()
