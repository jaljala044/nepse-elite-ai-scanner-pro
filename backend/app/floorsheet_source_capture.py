"""Policy-bound HTTPS capture of exact public floorsheet responses.

This transport layer never parses or promotes source data. A deployment must
supply a reviewed endpoint policy; no provider endpoint is assumed by default.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ssl
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPSHandler, HTTPRedirectHandler, Request, build_opener,
)

from app.raw_capture import build_capture_manifest
from app.evidence_store import persist_evidence_batch


class FloorsheetCaptureRejected(ValueError):
    """The requested endpoint or response violates capture policy."""


@dataclass(frozen=True)
class FloorsheetCapturePolicy:
    source_id: str
    allowed_host: str
    allowed_path_prefix: str
    max_response_bytes: int = 20_000_000
    allowed_content_types: tuple[str, ...] = (
        "application/json", "text/csv", "application/csv",
    )
    rights_status: str = "unknown"
    parser_version: str = "unassigned"

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id is required")
        host = self.allowed_host.lower().strip().rstrip(".")
        if not host or "/" in host or ":" in host:
            raise ValueError("allowed_host must be a bare hostname")
        object.__setattr__(self, "allowed_host", host)
        if (
            not isinstance(self.allowed_path_prefix, str)
            or not self.allowed_path_prefix.startswith("/")
            or ".." in self.allowed_path_prefix.split("/")
        ):
            raise ValueError("allowed_path_prefix must be a safe absolute path prefix")
        if isinstance(self.max_response_bytes, bool) or self.max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        if not self.allowed_content_types or any(
            not isinstance(item, str) or "/" not in item for item in self.allowed_content_types
        ):
            raise ValueError("allowed_content_types must be non-empty media types")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validate_endpoint(url: str, policy: FloorsheetCapturePolicy) -> None:
    if not isinstance(url, str) or not url.strip():
        raise FloorsheetCaptureRejected("endpoint_url_required")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise FloorsheetCaptureRejected("https_required")
    if parsed.username is not None or parsed.password is not None:
        raise FloorsheetCaptureRejected("url_credentials_forbidden")
    if parsed.fragment:
        raise FloorsheetCaptureRejected("url_fragment_forbidden")
    if parsed.query:
        raise FloorsheetCaptureRejected("query_string_forbidden")
    if (parsed.hostname or "").lower().rstrip(".") != policy.allowed_host:
        raise FloorsheetCaptureRejected("endpoint_host_not_allowlisted")
    if parsed.port not in (None, 443):
        raise FloorsheetCaptureRejected("nonstandard_https_port_forbidden")
    prefix = policy.allowed_path_prefix.rstrip("/")
    if not (parsed.path == prefix or parsed.path.startswith(prefix + "/")):
        raise FloorsheetCaptureRejected("endpoint_path_not_allowlisted")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def capture_public_floorsheet(
    url: str,
    *,
    policy: FloorsheetCapturePolicy,
    storage_root: str,
    fetch_id: str,
    database_path: str | None = None,
    timeout_seconds: float = 20.0,
    opener: Any | None = None,
    clock: Callable[[], datetime] = _now,
) -> dict:
    """Fetch and immutably capture a policy-approved public HTTPS response.

    Redirects are rejected. TLS certificate verification stays enabled.
    Request headers are deliberately not persisted. Query strings and URL
    credentials are rejected to prevent accidental secret capture.
    """
    if not isinstance(policy, FloorsheetCapturePolicy):
        raise TypeError("policy must be a FloorsheetCapturePolicy")
    if not isinstance(fetch_id, str) or not fetch_id.strip():
        raise FloorsheetCaptureRejected("fetch_id_required")
    if isinstance(timeout_seconds, bool) or not (0 < timeout_seconds <= 120):
        raise FloorsheetCaptureRejected("timeout_out_of_range")
    _validate_endpoint(url, policy)

    requested_at = clock()
    if requested_at.tzinfo is None or requested_at.utcoffset() is None:
        raise FloorsheetCaptureRejected("clock_must_return_timezone_aware_time")

    request = Request(
        url,
        headers={
            "Accept": ", ".join(policy.allowed_content_types),
            "User-Agent": "NEPSE-Research-Evidence-Capture/1.0",
        },
        method="GET",
    )
    if opener is None:
        opener = build_opener(
            _NoRedirect(),
            HTTPSHandler(context=ssl.create_default_context()),
        )

    try:
        response = opener.open(request, timeout=timeout_seconds)
        try:
            status = response.getcode()
            headers = response.headers
            declared_length = headers.get("Content-Length")
            if declared_length is not None:
                try:
                    parsed_length = int(declared_length)
                except (TypeError, ValueError):
                    raise FloorsheetCaptureRejected("invalid_content_length") from None
                if parsed_length < 0:
                    raise FloorsheetCaptureRejected("invalid_content_length")
                if parsed_length > policy.max_response_bytes:
                    raise FloorsheetCaptureRejected("response_exceeds_size_limit")
            content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in {x.lower() for x in policy.allowed_content_types}:
                raise FloorsheetCaptureRejected("content_type_not_allowlisted")
            payload = response.read(policy.max_response_bytes + 1)
        finally:
            response.close()
    except HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise FloorsheetCaptureRejected("redirect_rejected") from None
        raise FloorsheetCaptureRejected(f"http_status_not_accepted:{exc.code}") from None
    except URLError as exc:
        raise FloorsheetCaptureRejected("source_transport_failed") from None

    if status != 200:
        raise FloorsheetCaptureRejected(f"http_status_not_accepted:{status}")
    if len(payload) > policy.max_response_bytes:
        raise FloorsheetCaptureRejected("response_exceeds_size_limit")
    if not payload:
        raise FloorsheetCaptureRejected("empty_response_body")

    received_at = clock()
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise FloorsheetCaptureRejected("clock_must_return_timezone_aware_time")
    if received_at < requested_at:
        raise FloorsheetCaptureRejected("received_before_requested")

    manifest = build_capture_manifest(
        payload,
        source_id=policy.source_id,
        source_url=url,
        request_method="GET",
        request_metadata={"accept": ", ".join(policy.allowed_content_types)},
        requested_at=requested_at.isoformat(),
        received_at=received_at.isoformat(),
        http_status=status,
        content_type=content_type,
        fetch_id=fetch_id,
        parser_version=policy.parser_version,
        rights_status=policy.rights_status,
    )
    persisted = persist_evidence_batch(
        payload, manifest, [], storage_root=storage_root, database_path=database_path
    )
    return {
        "status": "captured",
        "source_id": policy.source_id,
        "fetch_id": fetch_id,
        "http_status": status,
        "content_type": content_type,
        "payload_bytes": len(payload),
        "payload_sha256": manifest["payload_sha256"],
        "requested_at_utc": manifest["requested_at_utc"],
        "received_at_utc": manifest["received_at_utc"],
        "rights_status": policy.rights_status,
        "parser_version": policy.parser_version,
        "capture": persisted,
        "canonical_eligible": False,
        "production_eligible": False,
    }
