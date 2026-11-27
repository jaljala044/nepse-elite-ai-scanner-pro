"""Verified-transport, immutable capture for official SEBON PDF evidence.

TLS and hostname checks are performed by httpx's default verified transport.
Redirects are disabled; only the two official SEBON hosts are accepted.
The exact response bytes are persisted content-addressably before returning.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .raw_capture import build_capture_manifest, persist_capture


_ALLOWED_HOSTS = {"sebon.gov.np", "www.sebon.gov.np"}
_MAX_BYTES = 30 * 1024 * 1024
_USER_AGENT = "NEPSE-ELITE-AI-SCANNER/0.2 (read-only regulatory evidence capture)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_url(url: str) -> None:
    parsed = urlparse(url) if isinstance(url, str) else None
    if (parsed is None or parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_HOSTS
            or not parsed.path.lower().endswith(".pdf")
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("url_must_be_official_sebon_https_pdf")


def _certificate_sha256(response: httpx.Response) -> str:
    """Extract peer certificate fingerprint from the verified TLS connection."""
    try:
        stream = response.extensions["network_stream"]
        ssl_object = stream.get_extra_info("ssl_object")
        certificate = ssl_object.getpeercert(binary_form=True)
    except (KeyError, AttributeError, TypeError):
        certificate = None
    if not certificate:
        raise ValueError("verified_tls_peer_certificate_unavailable")
    return hashlib.sha256(certificate).hexdigest()


def capture_sebon_pdf(
    url: str,
    *,
    storage_root: str | Path,
    timeout_seconds: float = 25.0,
    max_bytes: int = _MAX_BYTES,
) -> dict:
    """GET and immutably archive one official SEBON PDF with transport evidence.

    The transport is created internally with certificate verification enabled;
    callers cannot inject a client that might disable TLS verification.
    """
    _validate_url(url)
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= _MAX_BYTES:
        raise ValueError("max_bytes_out_of_range")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds_must_be_positive")

    active_client = httpx.Client(
        timeout=httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 10.0)),
        verify=True,
        follow_redirects=False,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/pdf"},
    )
    requested_at = _now()
    try:
        response = active_client.get(url)
        received_at = _now()
        if response.status_code != 200:
            raise ValueError(f"source_http_status_not_200:{response.status_code}")
        final_url = str(response.url)
        _validate_url(final_url)
        if final_url != url:
            raise ValueError("redirect_or_url_rewrite_not_permitted")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("response_content_type_not_pdf")
        payload = response.content
        if not payload or not payload.startswith(b"%PDF-"):
            raise ValueError("response_body_not_pdf")
        if len(payload) > max_bytes:
            raise ValueError("response_exceeds_size_limit")
        cert_hash = _certificate_sha256(response)
        fetch_id = "sebon-" + uuid.uuid4().hex
        source_id = "sebon-official-pdf"
        manifest = build_capture_manifest(
            payload,
            source_id=source_id,
            source_url=url,
            request_method="GET",
            request_metadata={
                "accept": "application/pdf",
                "redirects_allowed": False,
                "tls_verification": "httpx_default_verify_true",
                "hostname_verification": "httpx_verified_tls",
                "peer_certificate_sha256": cert_hash,
            },
            requested_at=requested_at,
            received_at=received_at,
            http_status=response.status_code,
            content_type=content_type,
            fetch_id=fetch_id,
            parser_version="sebon-pdf-capture-v1",
            rights_status="review_required",
        )
        stored = persist_capture(storage_root, payload, manifest)
        return {
            "capture_manifest": manifest,
            "storage": stored,
            "transport": {
                "tls_verified": True,
                "hostname_verified": True,
                "peer_certificate_sha256": cert_hash,
                "redirects_followed": 0,
            },
            "evidence_status": "captured_review_required",
            "membership_admission_allowed": False,
            "production_sector_signals_allowed": False,
        }
    finally:
        active_client.close()
