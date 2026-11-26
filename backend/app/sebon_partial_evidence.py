"""Fail-closed ingestion for partial SEBON company-sector observations.

These observations are regulatory-document evidence, not a complete NEPSE
membership register. Report/registration dates are never substituted for
classification effective dates; security identity remains unresolved.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse


_ALLOWED_HOSTS = {"sebon.gov.np", "www.sebon.gov.np"}


def _aware_utc(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _optional_date(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field}_must_be_iso_date")
    return value


def build_sebon_partial_evidence(
    *,
    raw_payload: bytes,
    source_url: str,
    captured_at: str,
    http_status: int,
    content_type: str,
    tls_verified: bool,
    hostname_verified: bool,
    archive_ref: str,
    document_date: str,
    observations: list[dict],
) -> dict:
    """Build a review-only manifest from an archived official SEBON PDF.

    The caller must archive the exact raw bytes at archive_ref before calling.
    This function validates supplied capture assertions; it does not itself
    perform HTTP/TLS acquisition or authenticate the archive.
    """
    if not isinstance(raw_payload, bytes) or not raw_payload:
        raise ValueError("raw_pdf_payload_required")
    parsed_url = urlparse(source_url) if isinstance(source_url, str) else None
    if (parsed_url is None or parsed_url.scheme != "https"
            or parsed_url.hostname not in _ALLOWED_HOSTS
            or not parsed_url.path.lower().endswith(".pdf")
            or parsed_url.username or parsed_url.password):
        raise ValueError("source_url_must_be_official_sebon_https_pdf")
    if isinstance(http_status, bool) or http_status != 200:
        raise ValueError("source_http_status_must_be_200")
    if not isinstance(content_type, str) or "pdf" not in content_type.lower():
        raise ValueError("source_content_type_must_be_pdf")
    if tls_verified is not True or hostname_verified is not True:
        raise ValueError("source_tls_and_hostname_verification_required")
    if not isinstance(archive_ref, str) or not archive_ref.strip():
        raise ValueError("raw_payload_archive_ref_required")
    captured = _aware_utc(captured_at, "captured_at")
    doc_date = _optional_date(document_date, "document_date")
    if doc_date is None:
        raise ValueError("document_date_required")
    if not isinstance(observations, list) or not observations:
        raise ValueError("sebon_observations_required")

    normalized = []
    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            raise ValueError(f"observation_{index}_must_be_object")
        company = row.get("company_name")
        sector = row.get("sector_label")
        if not isinstance(company, str) or not company.strip():
            raise ValueError(f"observation_{index}_company_name_required")
        if not isinstance(sector, str) or not sector.strip():
            raise ValueError(f"observation_{index}_sector_label_required")
        registration_date = _optional_date(
            row.get("registration_date"), f"observation_{index}_registration_date")
        effective_date = _optional_date(
            row.get("classification_effective_date"),
            f"observation_{index}_classification_effective_date")
        normalized.append({
            "company_name": company.strip(),
            "sector_label": sector.strip(),
            "document_date": doc_date,
            "registration_date": registration_date,
            "classification_effective_date": effective_date,
            "classification_effective_date_status": (
                "source_explicit" if effective_date else "unknown"),
            "security_id": None,
            "symbol": None,
            "identity_status": "unresolved",
            "source_row_ref": row.get("source_row_ref"),
        })

    payload_hash = sha256(raw_payload).hexdigest()
    return {
        "schema_version": 1,
        "source": {
            "publisher": "Securities Board of Nepal (SEBON)",
            "source_url": source_url,
            "source_type": "official_regulatory_pdf",
        },
        "capture": {
            "captured_at": captured,
            "http_status": http_status,
            "content_type": content_type,
            "tls_verified": True,
            "hostname_verified": True,
            "payload_bytes": len(raw_payload),
            "payload_sha256": payload_hash,
            "archive_ref": archive_ref,
        },
        "document_date": doc_date,
        "observations": normalized,
        "evidence_status": "partial_review_only",
        "coverage_status": "incomplete_universe",
        "membership_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
    }
