"""Validate operator-reviewed source contracts before enabling any capture.

This module does not authenticate publishers, retrieve credentials or perform
network access. It emits only a safe capture specification and a minimal
approved-registry record for the existing raw-payload validator.
"""
from __future__ import annotations
from datetime import datetime
from urllib.parse import parse_qsl, urlparse
from typing import Mapping

_DATASET_KINDS = {
    "official_eod_ohlcv", "official_market_calendar", "official_security_master",
    "official_corporate_actions", "official_floorsheet", "cdsc_first_trade",
    "official_sector_indices", "official_broker_trade_summary",
}
_AUTH_MODES = {"public", "api_key", "bearer_token", "oauth2", "session_cookie"}
_SECRET_KEYS = {"token", "access_token", "refresh_token", "api_key", "password", "client_secret", "secret", "cookie", "authorization"}


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _secret_material_present(value: object, key: str = "") -> bool:
    if key.lower() in _SECRET_KEYS and value not in (None, "", False):
        return True
    if isinstance(value, Mapping):
        return any(_secret_material_present(v, str(k)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_secret_material_present(v, key) for v in value)
    return False


def validate_historical_source_contract(*, contract: Mapping[str, object], decision_cutoff: str) -> dict:
    """Return a safe, reviewed capture specification or a fail-closed report."""
    errors = []
    try:
        cutoff = _aware(decision_cutoff, "decision_cutoff")
    except ValueError:
        return {"status":"CONTRACT_BLOCKED","errors":[{"reason":"decision_cutoff_invalid"}],"capture_allowed":False,"registry_record":None,"capture_spec":None}
    if not isinstance(contract, Mapping):
        return {"status":"CONTRACT_BLOCKED","errors":[{"reason":"contract_not_mapping"}],"capture_allowed":False,"registry_record":None,"capture_spec":None}
    if _secret_material_present(contract):
        errors.append({"reason":"secret_material_must_not_be_embedded_in_contract"})
    source_id = str(contract.get("source_id","")).strip()
    publisher_id = str(contract.get("publisher_id","")).strip()
    dataset_kind = str(contract.get("dataset_kind","")).strip()
    endpoint = str(contract.get("endpoint_url","")).strip()
    parsed = urlparse(endpoint)
    hosts = contract.get("allowed_hosts")
    allowed_hosts = set(hosts) if isinstance(hosts,list) else set()
    if not source_id: errors.append({"reason":"source_id_missing"})
    if not publisher_id: errors.append({"reason":"publisher_id_missing"})
    if dataset_kind not in _DATASET_KINDS: errors.append({"reason":"dataset_kind_unsupported"})
    query_secret_keys = {key.lower() for key, _value in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_secret_keys.intersection(_SECRET_KEYS):
        errors.append({"reason":"endpoint_query_must_not_contain_credentials"})
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.hostname not in allowed_hosts:
        errors.append({"reason":"endpoint_must_be_https_and_exactly_allowlisted_without_userinfo_or_fragment"})
    if not isinstance(hosts,list) or not hosts or any(not isinstance(x,str) or not x.strip() for x in hosts):
        errors.append({"reason":"allowed_hosts_invalid"})
    content_types = contract.get("allowed_content_types")
    supported = {"text/csv","application/json","application/octet-stream"}
    if not isinstance(content_types,list) or not content_types or any(x not in supported for x in content_types):
        errors.append({"reason":"allowed_content_types_invalid"})
    try:
        start = _aware(contract.get("window_start"),"window_start")
        end = _aware(contract.get("window_end"),"window_end")
        reviewed_at = _aware(contract.get("reviewed_at"),"reviewed_at")
        if end < start: errors.append({"reason":"capture_window_inverted"})
        if reviewed_at > cutoff: errors.append({"reason":"contract_review_after_decision_cutoff"})
    except ValueError:
        start = end = reviewed_at = None
        errors.append({"reason":"contract_timestamps_invalid"})
    if contract.get("review_status") != "approved" or contract.get("approved_by_human") is not True:
        errors.append({"reason":"explicit_human_source_approval_missing"})
    if not str(contract.get("reviewer_id","")).strip(): errors.append({"reason":"reviewer_id_missing"})
    if not str(contract.get("authority_evidence_ref","")).strip(): errors.append({"reason":"publisher_authority_evidence_reference_missing"})
    if contract.get("licence_reviewed") is not True: errors.append({"reason":"licence_terms_not_reviewed"})
    if contract.get("access_policy_reviewed") is not True: errors.append({"reason":"access_policy_not_reviewed"})
    auth_mode = contract.get("authentication_mode")
    if auth_mode not in _AUTH_MODES: errors.append({"reason":"authentication_mode_invalid"})
    if auth_mode != "public" and not str(contract.get("credential_reference","")).strip():
        errors.append({"reason":"external_credential_reference_missing"})
    page_parameter = str(contract.get("page_parameter","")).strip()
    terminal_signal = contract.get("terminal_signal")
    max_pages = contract.get("max_pages")
    rate_limit = contract.get("minimum_request_interval_seconds")
    if not page_parameter: errors.append({"reason":"documented_page_parameter_missing"})
    if terminal_signal != "has_more_false": errors.append({"reason":"explicit_terminal_pagination_contract_missing"})
    if isinstance(max_pages,bool) or not isinstance(max_pages,int) or not 1 <= max_pages <= 1000:
        errors.append({"reason":"max_pages_out_of_range"})
    if isinstance(rate_limit,bool) or not isinstance(rate_limit,(int,float)) or rate_limit < 0.1:
        errors.append({"reason":"minimum_request_interval_invalid"})
    if not str(contract.get("capture_id","")).strip(): errors.append({"reason":"capture_id_missing"})
    ok = not errors
    registry = {"source_id":source_id,"publisher_id":publisher_id,"review_status":"approved","allowed_hosts":sorted(allowed_hosts)} if ok else None
    spec = None
    if ok:
        spec = {
            "review_status":"approved","source_id":source_id,"publisher_id":publisher_id,
            "dataset_kind":dataset_kind,"endpoint_url":endpoint,"allowed_hosts":sorted(allowed_hosts),
            "allowed_content_types":list(content_types),"window_start":start.isoformat(),
            "window_end":end.isoformat(),"capture_id":str(contract["capture_id"]),
            "page_parameter":page_parameter,"first_page":1,"max_pages":max_pages,
            "terminal_signal":terminal_signal,"minimum_request_interval_seconds":float(rate_limit),
            "authentication_mode":auth_mode,"credential_reference":contract.get("credential_reference"),
            "authority_evidence_ref":str(contract["authority_evidence_ref"]),
        }
    return {
        "status":"SOURCE_CONTRACT_APPROVED_FOR_CAPTURE" if ok else "CONTRACT_BLOCKED",
        "source_id":source_id or None,"publisher_id":publisher_id or None,"dataset_kind":dataset_kind or None,
        "errors":errors,"capture_allowed":ok,"registry_record":registry,"capture_spec":spec,
        "publisher_authenticity_independently_proven":False,"exchange_completeness_proven":False,
        "credentials_embedded":False,"network_access_performed":False,"production_enabled":False,
        "limitations":[
            "Human review and authority evidence references are workflow assertions, not cryptographic publisher authentication.",
            "The caller must retrieve credentials from a secret manager using credential_reference; secret values must never enter this contract.",
            "The injected transport must enforce TLS, authentication, rate limits, licensing and timeout policy.",
            "Capture approval does not prove endpoint completeness or authorize backtests.",
        ],
    }
