"""Verify protected, immutable market input bundles before research generation."""
from __future__ import annotations
import base64
import binascii
import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from .trusted_artifact_store import _timestamp

_REQUIRED = {
    "decision_time", "calendar", "universe", "daily_rows", "benchmark_rows",
    "index_rows", "expected_indices", "stock_rows",
    "expected_sector_members", "sector_membership",
}

def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("protected_bundle_duplicate_json_key")
        result[key] = value
    return result

def _reject_constant(value):
    raise ValueError("protected_bundle_non_finite_json_number")

def verify_protected_input_bundle(bundle_path, signature_path, *, public_key_pem,
                                  expected_session, decision_time):
    path, sig_path = Path(bundle_path), Path(signature_path)
    if path.is_symlink() or sig_path.is_symlink() or not path.is_file() or not sig_path.is_file():
        raise ValueError("protected_bundle_or_signature_missing")
    if path.stat().st_size > 100 * 1024 * 1024 or sig_path.stat().st_size > 4096:
        raise ValueError("protected_bundle_exceeds_size_limit")
    raw = path.read_bytes()
    signature_raw = sig_path.read_bytes().strip()
    try:
        key = load_pem_public_key(public_key_pem)
    except (ValueError, TypeError):
        raise ValueError("collector_public_key_invalid") from None
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("collector_key_must_be_ed25519")
    try:
        signature = base64.b64decode(signature_raw, validate=True)
        key.verify(signature, raw)
    except (InvalidSignature, ValueError, TypeError, binascii.Error):
        raise ValueError("protected_bundle_signature_invalid") from None
    try:
        bundle = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("protected_bundle_json_invalid") from None
    if not isinstance(bundle, dict) or not _REQUIRED <= set(bundle):
        raise ValueError("protected_bundle_schema_incomplete")
    if not isinstance(expected_session, str):
        raise ValueError("protected_bundle_timestamp_invalid")
    try:
        if date.fromisoformat(expected_session).isoformat() != expected_session:
            raise ValueError
        cutoff = _timestamp(decision_time, "decision_time")
        available = _timestamp(bundle["decision_time"], "bundle_decision_time")
    except (ValueError, TypeError, KeyError):
        raise ValueError("protected_bundle_timestamp_invalid") from None
    sessions = bundle.get("calendar", {}).get("sessions") if isinstance(bundle.get("calendar"), dict) else None
    if not isinstance(sessions, list) or not sessions or sessions[-1] != expected_session:
        raise ValueError("protected_bundle_session_mismatch")
    if available > cutoff:
        raise ValueError("protected_bundle_after_decision_cutoff")
    if date.fromisoformat(expected_session) > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("protected_bundle_future_session")
    for field in ("daily_rows", "benchmark_rows", "index_rows", "stock_rows", "expected_indices"):
        if not isinstance(bundle.get(field), list):
            raise ValueError("protected_bundle_rows_invalid")
    if not isinstance(bundle.get("universe"), dict) or not isinstance(bundle.get("expected_sector_members"), dict) or not isinstance(bundle.get("sector_membership"), dict):
        raise ValueError("protected_bundle_schema_incomplete")
    digest = sha256(raw).hexdigest()
    return {"bundle": bundle, "sha256": digest, "session_date": expected_session,
            "signature_verified": True, "source_authorization_attested": False,
            "promotion_allowed": False, "signals_enabled": False}
