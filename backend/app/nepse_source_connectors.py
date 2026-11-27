"""Governed HTTPS acquisition for explicitly approved public data endpoints.

The connector never discovers endpoints or credentials. Operators must register
and approve a canonical HTTPS host, dataset rights, and source metadata first.
A transport may be injected for tests; redirects and cross-host responses fail.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlparse
from app.nepse_source_registry import validate_source_registry, build_source_capture_run

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _time(value):
    if not isinstance(value, str): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _endpoint(uri):
    try:
        p = urlparse(uri)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return None
        if p.port not in (None, 443): return None
        return p.hostname.lower().rstrip(".")
    except (TypeError, ValueError):
        return None

def _http_get(uri, *, timeout_seconds, max_bytes):
    opener = build_opener(_NoRedirect)
    request = Request(uri, headers={"User-Agent":"NEPSE-Research-Data-Collector/1.0",
                                    "Accept":"text/csv,application/csv,text/plain,application/octet-stream"},
                      method="GET")
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(max_bytes + 1)
            return {"status": response.status, "final_url": response.geturl(),
                    "headers": dict(response.headers.items()), "body": body}
    except HTTPError as exc:
        return {"status": exc.code, "final_url": exc.geturl(),
                "headers": dict(exc.headers.items()) if exc.headers else {}, "body": b""}
    except URLError as exc:
        raise ValueError("source_transport_error:" + str(exc.reason)) from exc

def acquire_registered_capture(*, registry, source_id, dataset_kind, endpoint_uri,
    evidence_id, captured_at, decision_cutoff, rights_status,
    timeout_seconds=15, max_bytes=25_000_000, transport=None):
    """Fetch one registered CSV endpoint and validate its captured bytes.

    transport(uri, timeout_seconds=..., max_bytes=...) must return
    {status, final_url, headers, body}; it is injectable for deterministic tests.
    """
    checked = validate_source_registry(registry)
    if checked["errors"]: raise ValueError("source_registry_contains_invalid_records")
    sources = {x["source_id"]: x for x in checked["sources"]}
    source = sources.get(source_id)
    if source is None or source.get("status") != "approved":
        raise ValueError("source_not_approved")
    cutoff = _time(decision_cutoff); captured = _time(captured_at)
    if cutoff is None or captured is None or captured > cutoff:
        raise ValueError("capture_or_cutoff_timestamp_invalid")
    if timeout_seconds <= 0 or max_bytes < 1:
        raise ValueError("transport_limits_invalid")
    host = _endpoint(endpoint_uri)
    if host is None or host != source["canonical_host"]:
        raise ValueError("endpoint_host_not_registered")
    if dataset_kind not in source["dataset_kinds"]:
        raise ValueError("dataset_not_authorized_for_source")
    fetch = transport or _http_get
    response = fetch(endpoint_uri, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
    if not isinstance(response, dict): raise ValueError("transport_response_invalid")
    status = response.get("status")
    final_url = response.get("final_url")
    body = response.get("body")
    headers = response.get("headers", {})
    if status != 200: raise ValueError("source_http_status_not_200")
    if _endpoint(final_url) != host: raise ValueError("source_redirect_or_final_host_mismatch")
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise ValueError("source_response_body_empty")
    if len(body) > max_bytes: raise ValueError("source_response_exceeds_max_bytes")
    if isinstance(headers, dict):
        length = headers.get("Content-Length") or headers.get("content-length")
        if length is not None:
            try: declared = int(length)
            except (TypeError, ValueError): raise ValueError("content_length_invalid")
            if declared > max_bytes or declared != len(body):
                raise ValueError("content_length_mismatch_or_limit_exceeded")
    receipt_run = build_source_capture_run(registry=registry, captures=[{
        "source_id":source_id, "dataset_kind":dataset_kind, "source_uri":endpoint_uri,
        "raw_bytes":bytes(body), "evidence_id":evidence_id, "captured_at":captured_at,
        "rights_status":rights_status, "source_validation_status":"verified",
        "finality_status":"final"}], decision_cutoff=decision_cutoff)
    if receipt_run["capture_count"] != 1:
        raise ValueError("captured_dataset_failed_validation")
    receipt = receipt_run["receipts"][0]
    return {"schema_version":"nepse-source-acquisition-1.0.0",
        "http_status":status, "content_type":(headers.get("Content-Type") or headers.get("content-type")) if isinstance(headers,dict) else None,
        "receipt":receipt, "raw_bytes":bytes(body), "validation":receipt_run,
        "network_retrieval_performed":True, "production_enabled":False,
        "limitations":[
            "The endpoint, host approval, rights status and evidence identity are operator-supplied.",
            "HTTP 200 and HTTPS do not cryptographically authenticate the publisher or prove dataset completeness.",
            "Redirects, non-HTTPS endpoints, non-standard ports, host mismatches and oversized bodies are rejected.",
            "No login, API key, cookie, private endpoint or credential workflow is supported.",
            "A source-specific parser and independent reconciliation are still required before historical panel promotion."]}
