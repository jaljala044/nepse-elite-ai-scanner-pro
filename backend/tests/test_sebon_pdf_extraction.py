import hashlib
import unittest

from app.sebon_pdf_extraction import extract_sebon_pdf_text


def make_text_pdf(lines):
    """Build a tiny one-page PDF containing selectable text, without fixtures."""
    commands = ["BT", "/F1 10 Tf", "50 750 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("0 -16 Td")
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


class SebonPdfExtractionTests(unittest.TestCase):
    def setUp(self):
        self.pdf = make_text_pdf([
            "Name of Company Sector",
            "Himalayan Example Hydropower Ltd.  Hydropower",
            "Other Example Ltd.  Finance",
        ])

    def test_extracts_page_text_and_source_referenced_candidates(self):
        result = extract_sebon_pdf_text(self.pdf)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(len(result["pages"]), 1)
        self.assertEqual(len(result["row_candidates"]), 2)
        first = result["row_candidates"][0]
        self.assertEqual(first["company_name_candidate"], "Himalayan Example Hydropower Ltd")
        self.assertEqual(first["sector_label_candidate"], "Hydropower")
        self.assertIn("page:1:line:2", first["source_row_ref"])
        self.assertEqual(first["review_status"], "candidate_review_required")
        self.assertIsNone(first["classification_effective_date"])
        self.assertFalse(result["membership_admission_allowed"])

    def test_preserves_exact_payload_hash(self):
        result = extract_sebon_pdf_text(self.pdf)
        self.assertEqual(result["payload_sha256"], hashlib.sha256(self.pdf).hexdigest())

    def test_rejects_expected_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError, "sha256_mismatch"):
            extract_sebon_pdf_text(self.pdf, expected_sha256="0" * 64)

    def test_rejects_non_pdf_payload(self):
        with self.assertRaisesRegex(ValueError, "not_pdf"):
            extract_sebon_pdf_text(b"not a PDF")

    def test_rejects_invalid_page_limit(self):
        with self.assertRaisesRegex(ValueError, "max_pages_out_of_range"):
            extract_sebon_pdf_text(self.pdf, max_pages=0)

    def test_rejects_malformed_pdf(self):
        with self.assertRaisesRegex(ValueError, "extraction_failed"):
            extract_sebon_pdf_text(b"%PDF-1.4\nnot really a PDF")

    def test_header_is_required_before_row_candidates(self):
        pdf = make_text_pdf([
            "Some introductory text",
            "Himalayan Example Hydropower Ltd.  Hydropower",
            "Name of Company Sector",
        ])
        result = extract_sebon_pdf_text(pdf)
        self.assertEqual(result["row_candidates"], [])


if __name__ == "__main__":
    unittest.main()
