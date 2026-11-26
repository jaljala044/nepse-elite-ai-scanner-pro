import unittest

from app.sebon_partial_evidence import build_sebon_partial_evidence


class SebonPartialEvidenceTests(unittest.TestCase):
    def build(self, **overrides):
        args = {
            "raw_payload": b"%PDF-1.7 example",
            "source_url": "https://www.sebon.gov.np/uploads/example.pdf",
            "captured_at": "2026-11-27T10:00:00+05:45",
            "http_status": 200,
            "content_type": "application/pdf",
            "tls_verified": True,
            "hostname_verified": True,
            "archive_ref": "evidence/sebon/example.pdf",
            "document_date": "2026-11-26",
            "observations": [{
                "company_name": "Example Hydropower Ltd.",
                "sector_label": "Hydropower",
                "registration_date": "2026-11-20",
            }],
        }
        args.update(overrides)
        return build_sebon_partial_evidence(**args)

    def test_builds_partial_record_and_keeps_effective_date_unknown(self):
        result = self.build()
        row = result["observations"][0]
        self.assertEqual(row["registration_date"], "2026-11-20")
        self.assertIsNone(row["classification_effective_date"])
        self.assertEqual(row["classification_effective_date_status"], "unknown")
        self.assertIsNone(row["security_id"])
        self.assertEqual(result["evidence_status"], "partial_review_only")
        self.assertFalse(result["membership_admission_allowed"])
        self.assertFalse(result["production_sector_signals_allowed"])
        self.assertEqual(result["capture"]["payload_bytes"], len(b"%PDF-1.7 example"))
        self.assertEqual(len(result["capture"]["payload_sha256"]), 64)

    def test_preserves_explicit_classification_date_separately(self):
        result = self.build(observations=[{
            "company_name": "Example Ltd.",
            "sector_label": "Finance",
            "registration_date": "2026-11-20",
            "classification_effective_date": "2026-10-01",
        }])
        row = result["observations"][0]
        self.assertEqual(row["registration_date"], "2026-11-20")
        self.assertEqual(row["classification_effective_date"], "2026-10-01")
        self.assertEqual(row["classification_effective_date_status"], "source_explicit")

    def test_rejects_non_sebon_host(self):
        with self.assertRaisesRegex(ValueError, "official_sebon"):
            self.build(source_url="https://example.com/uploads/example.pdf")

    def test_rejects_unverified_tls(self):
        with self.assertRaisesRegex(ValueError, "tls_and_hostname"):
            self.build(tls_verified=False)

    def test_rejects_non_200_response(self):
        with self.assertRaisesRegex(ValueError, "http_status_must_be_200"):
            self.build(http_status=404)

    def test_rejects_missing_raw_archive_reference(self):
        with self.assertRaisesRegex(ValueError, "archive_ref_required"):
            self.build(archive_ref=" ")

    def test_rejects_registration_date_as_non_iso(self):
        with self.assertRaisesRegex(ValueError, "registration_date_must_be_iso_date"):
            self.build(observations=[{
                "company_name": "Example Ltd.",
                "sector_label": "Finance",
                "registration_date": "20/11/2026",
            }])

    def test_rejects_blank_company_or_sector(self):
        for observation in (
            {"company_name": " ", "sector_label": "Finance"},
            {"company_name": "Example Ltd.", "sector_label": " "},
        ):
            with self.subTest(observation=observation):
                with self.assertRaises(ValueError):
                    self.build(observations=[observation])


if __name__ == "__main__":
    unittest.main()
