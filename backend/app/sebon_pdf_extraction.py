"""Conservative, page-referenced text extraction for archived SEBON PDFs.

This module extracts text and table-row candidates only. It does not certify
that a row is a complete company-sector mapping or infer security identity,
classification effective dates, or NEPSE membership.
"""
from __future__ import annotations

import hashlib
import io
import re
from typing import Any

from pypdf import PdfReader


_MAX_PDF_BYTES = 30 * 1024 * 1024
_MAX_PAGES = 500
_SECTOR_LABELS = (
    "Commercial Banks?", "Development Banks?", "Finance Companies?",
    "Microfinance", "Hydropower", "Life Insurance", "Non[- ]Life Insurance",
    "Manufacturing and Processing", "Hotels? and Tourism", "Trading",
    "Investment", "Others?",
)
_SECTOR_RE = re.compile(
    r"^(?P<company>.+?)(?:\s{2,}|\s*\|\s*)(?P<sector>"
    + "|".join(_SECTOR_LABELS)
    + r")\s*$",
    re.IGNORECASE,
)
_HEADER_RE = re.compile(r"name\s+of\s+company", re.IGNORECASE)
_SECTOR_HEADER_RE = re.compile(r"\bsector\b", re.IGNORECASE)


def extract_sebon_pdf_text(
    raw_pdf: bytes,
    *,
    expected_sha256: str | None = None,
    max_pages: int = _MAX_PAGES,
) -> dict[str, Any]:
    """Extract page text and conservative row candidates from exact PDF bytes."""
    if not isinstance(raw_pdf, bytes) or not raw_pdf:
        raise ValueError("raw_pdf_bytes_required")
    if len(raw_pdf) > _MAX_PDF_BYTES:
        raise ValueError("pdf_exceeds_size_limit")
    if not raw_pdf.startswith(b"%PDF-"):
        raise ValueError("payload_is_not_pdf")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= _MAX_PAGES:
        raise ValueError("max_pages_out_of_range")
    digest = hashlib.sha256(raw_pdf).hexdigest()
    if expected_sha256 is not None and expected_sha256 != digest:
        raise ValueError("expected_pdf_sha256_mismatch")

    try:
        reader = PdfReader(io.BytesIO(raw_pdf), strict=True)
        if reader.is_encrypted:
            raise ValueError("encrypted_pdf_not_supported")
        page_count = len(reader.pages)
        if page_count > max_pages:
            raise ValueError("pdf_page_limit_exceeded")
        pages = []
        candidates = []
        for page_number, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            lines = [re.sub(r"[\t\u00a0 ]+", " ", line).strip()
                     for line in extracted.splitlines()]
            lines = [line for line in lines if line]
            header_seen = False
            page_record = {
                "page_number": page_number,
                "text": extracted,
                "text_sha256": hashlib.sha256(extracted.encode("utf-8")).hexdigest(),
                "line_count": len(lines),
                "source_line_refs": [],
            }
            for line_number, line in enumerate(lines, start=1):
                ref = f"pdf-sha256:{digest}:page:{page_number}:line:{line_number}"
                page_record["source_line_refs"].append(ref)
                if _HEADER_RE.search(line) and _SECTOR_HEADER_RE.search(line):
                    header_seen = True
                if header_seen:
                    match = _SECTOR_RE.match(line)
                    if match:
                        company = match.group("company").strip(" .:-")
                        sector = re.sub(r"\s+", " ", match.group("sector")).strip()
                        if company and len(company) >= 3:
                            candidates.append({
                                "company_name_candidate": company,
                                "sector_label_candidate": sector,
                                "source_row_ref": ref,
                                "source_page": page_number,
                                "source_line_number": line_number,
                                "source_text": line,
                                "review_status": "candidate_review_required",
                                "identity_status": "unresolved",
                                "classification_effective_date": None,
                            })
            pages.append(page_record)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"pdf_text_extraction_failed:{type(exc).__name__}") from None

    return {
        "schema_version": 1,
        "parser": "pypdf-page-text-v1",
        "payload_sha256": digest,
        "payload_bytes": len(raw_pdf),
        "page_count": len(pages),
        "pages": pages,
        "row_candidates": candidates,
        "extraction_status": "text_extracted_review_required",
        "membership_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
    }
