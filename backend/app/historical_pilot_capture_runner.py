"""Orchestrate operator-authorized paginated source capture through an injected transport."""
from __future__ import annotations
import hashlib
from datetime import datetime
from typing import Callable, Mapping
from urllib.parse import urlparse, urlencode


def _aware(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def capture_registered_source_pages(*, source_spec: Mapping[str, object], fetch_page: Callable[[str], Mapping[str, object]], captured_at: str, decision_cutoff: str, max_pages: int = 100) -> dict:
    """Capture sequential pages from an approved HTTPS endpoint; require explicit terminal pagination."""
    captured, cutoff = _aware(captured_at, "captured_at"), _aware(decision_cutoff, "decision_cutoff")
    if captured > cutoff:
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"capture_after_decision_cutoff"}],"payloads":{},"manifest":None}
    if not isinstance(max_pages,int) or max_pages < 1 or max_pages > 1000:
        raise ValueError("max_pages must be between 1 and 1000")
    if source_spec.get("review_status") != "approved":
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"source_not_approved"}],"payloads":{},"manifest":None}
    source_id, publisher_id = str(source_spec.get("source_id","")).strip(), str(source_spec.get("publisher_id","")).strip()
    endpoint = str(source_spec.get("endpoint_url","")).strip()
    parsed = urlparse(endpoint); allowed = set(source_spec.get("allowed_hosts",[]))
    if not source_id or not publisher_id or parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in allowed:
        return {"status":"CAPTURE_BLOCKED","errors":[{"reason":"endpoint_or_publisher_not_allowlisted"}],"payloads":{},"manifest":None}
    content_types = set(source_spec.get("allowed_content_types",[]))
    if not content_types: raise ValueError("allowed_content_types must be explicitly registered")
    page_parameter, first_page = str(source_spec.get("page_parameter","page")), source_spec.get("first_page",1)
    if not isinstance(first_page,int) or first_page < 1: raise ValueError("first_page must be a positive integer")
    payloads, pages, errors, available_values = {}, [], [], []
    terminal = False
    for offset in range(max_pages):
        page_number = first_page + offset
        url = endpoint + ("&" if parsed.query else "?") + urlencode({page_parameter:page_number})
        try: response = fetch_page(url)
        except Exception as exc:
            errors.append({"page_number":page_number,"reason":"transport_error","detail":type(exc).__name__}); break
        if not isinstance(response,Mapping):
            errors.append({"page_number":page_number,"reason":"invalid_transport_response"}); break
        final_url, body = str(response.get("final_url",url)), response.get("body")
        final = urlparse(final_url); content_type = str(response.get("content_type","")).split(";")[0].strip().lower()
        if final.scheme != "https" or final.hostname not in allowed or final.hostname != parsed.hostname:
            errors.append({"page_number":page_number,"reason":"redirect_outside_registered_host"}); break
        if response.get("status_code") != 200 or not isinstance(body,bytes) or content_type not in content_types:
            errors.append({"page_number":page_number,"reason":"http_body_or_content_type_invalid"}); break
        try: available = _aware(response.get("available_at"),"available_at")
        except ValueError:
            errors.append({"page_number":page_number,"reason":"publisher_available_at_missing_or_invalid"}); break
        if available > cutoff:
            errors.append({"page_number":page_number,"reason":"page_not_available_by_decision_cutoff"}); break
        payload_id = f"{source_id}:{page_number}"
        payloads[payload_id] = body
        pages.append({"page_number":page_number,"payload_id":payload_id,"raw_sha256":hashlib.sha256(body).hexdigest(),"http_status":200,"content_type":content_type,"final_page":response.get("has_more") is False})
        available_values.append(available)
        if response.get("has_more") is False:
            terminal = True; break
        if response.get("has_more") is not True:
            errors.append({"page_number":page_number,"reason":"pagination_state_not_explicit"}); break
    if not terminal and not errors: errors.append({"reason":"maximum_pages_reached_without_terminal_page"})
    manifest = None
    if pages:
        manifest = {"source_id":source_id,"publisher_id":publisher_id,"request_url":endpoint,"captured_at":captured.isoformat(),"available_at":max(available_values).isoformat(),"window_start":str(source_spec.get("window_start","")),"window_end":str(source_spec.get("window_end","")),"capture_id":str(source_spec.get("capture_id","")),"expected_page_count":len(pages),"pages":pages,"capture_complete":terminal and not errors,"response_content_type":pages[0]["content_type"]}
    return {"status":"CAPTURED_PENDING_MANIFEST_VALIDATION" if manifest and terminal and not errors else "CAPTURE_INCOMPLETE","manifest":manifest,"payloads":payloads,"errors":errors,"raw_payload_count":len(payloads),"all_pages_hashed":len(pages)==len(payloads),"capture_complete":terminal and not errors,"publisher_authenticity_proven":False,"exchange_completeness_proven":False,"backtest_admission_allowed":False,"production_enabled":False,"limitations":["Injected transport must enforce TLS validation, publisher authentication, licensing, rate limits and safe timeouts.","Manifest must still pass the approved capture validator; publisher authenticity is not cryptographically proven.","Terminal pagination is publisher-declared completeness, not independent proof of exchange-wide completeness.","Raw bytes are returned to the caller; durable immutable storage and access controls remain the caller's responsibility."]}
