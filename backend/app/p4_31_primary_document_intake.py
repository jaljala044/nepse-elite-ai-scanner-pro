"""Step 96: intake verifier for operator-supplied primary listing/lifecycle documents."""
from __future__ import annotations
import hashlib
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

APPROVED_PRIMARY_HOSTS={"nepalstock.com","www.nepalstock.com","cdsc.com.np","www.cdsc.com.np"}

def _aware(value: str, field: str) -> datetime:
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (ValueError,AttributeError) as exc:
        raise ValueError(f"{field}_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field}_timezone_required")
    return dt

def validate_primary_document(*, raw_bytes: bytes, source_url: str, publisher_id: str,
                              retrieved_at: str, available_at: str, decision_cutoff: str,
                              archive_path: str, expected_sha256: str | None = None,
                              content_type: str = "application/pdf",
                              http_status: int = 200, event_id: str) -> dict[str, Any]:
    """Verify supplied bytes and provenance metadata; does not fetch or authenticate the publisher."""
    digest=hashlib.sha256(raw_bytes).hexdigest()
    errors=[]
    try:
        from urllib.parse import urlparse
        parsed=urlparse(source_url)
        host=(parsed.hostname or "").lower()
        if parsed.scheme!="https" or host not in APPROVED_PRIMARY_HOSTS:
            raise ValueError("source_url_not_approved_primary_https")
        if http_status!=200:
            raise ValueError("http_status_not_200")
        if content_type.split(";")[0].strip().lower()!="application/pdf":
            raise ValueError("content_type_not_pdf")
        if not raw_bytes.startswith(b"%PDF-"):
            raise ValueError("pdf_signature_missing")
        path=PurePosixPath(archive_path)
        if path.is_absolute() or ".." in path.parts or not archive_path.strip():
            raise ValueError("unsafe_archive_path")
        retrieved=_aware(retrieved_at,"retrieved_at")
        available=_aware(available_at,"available_at")
        cutoff=_aware(decision_cutoff,"decision_cutoff")
        if retrieved>cutoff or available>cutoff:
            raise ValueError("document_after_decision_cutoff")
        if available>retrieved:
            raise ValueError("available_at_after_retrieval")
        if not publisher_id.strip() or not event_id.strip():
            raise ValueError("publisher_or_event_id_missing")
        if expected_sha256 and expected_sha256.lower()!=digest:
            raise ValueError("sha256_mismatch")
        return {"status":"PRIMARY_DOCUMENT_BYTES_VERIFIED","event_id":event_id,
                "publisher_id":publisher_id,"source_url":source_url,"host":host,
                "http_status":http_status,"content_type":content_type,
                "retrieved_at":retrieved.isoformat(),"available_at":available.isoformat(),
                "archive_path":archive_path,"sha256":digest,"byte_count":len(raw_bytes),
                "publisher_authenticity_verified":False,"event_admission_allowed":False}
    except ValueError as exc:
        errors.append(str(exc))
        return {"status":"BLOCKED","event_id":event_id or None,"sha256":digest,
                "byte_count":len(raw_bytes),"errors":errors,"event_admission_allowed":False}
