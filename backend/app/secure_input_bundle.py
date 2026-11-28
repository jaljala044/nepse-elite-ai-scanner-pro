"""Verify protected, immutable market input bundles before research generation.

The caller supplies a reviewer/collector public key from deployment configuration.
This module never signs bundles, grants source rights, or promotes market data.
"""
from __future__ import annotations
import base64
import binascii
import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from .trusted_artifact_store import _timestamp

_REQUIRED = {
    "decision_time", "calendar", "universe", "daily_rows", "benchmark_rows",
    "index_rows", "expected_indices", "stock_rows",
    "expected_sector_members", "sector_membership",
}

def verify_protected_input_bundle(bundle_path, signature_path, *, public_key_pem,
                                  expected_session, decision_time):
    path, sig_path = Path(bundle_path), Path(signature_path)
    if path.is_symlink() or sig_path.is_symlink() or not path.is_file() or not sig_path.is_file():
        raise ValueError("protected_bundle_or_signature_missing")
    raw = path.read_bytes()
    signature_raw = sig_path.read_bytes().strip()
    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("protected_bundle_exceeds_size_limit")
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
        bundle = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("protected_bundle_json_invalid") from None
    if not isinstance(bundle, dict) or not _REQUIRED <= set(bundle):
        raise ValueError("protected_bundle_schema_incomplete")
    if not isinstance(bundle.get("calendar"), dict) or bundle["calendar"].get("sessions", [])[-1:] != [expected_session]:
        raise ValueError("protected_bundle_session_mismatch")
    try:
        if date.fromisoformat(expected_session).isoformat() != expected_session:
            raise ValueError
        cutoff = _timestamp(decision_time, "decision_time")
        available = _timestamp(bundle["decision_time"], "bundle_decision_time")
    except (ValueError, TypeError, KeyError):
        raise ValueError("protected_bundle_timestamp_invalid") from None
    if available > cutoff:
        raise ValueError("protected_bundle_after_decision_cutoff")
    if date.fromisoformat(expected_session) > cutoff.date():
        raise ValueError("protected_bundle_future_session")
    if not isinstance(bundle.get("daily_rows"), list) or not isinstance(bundle.get("benchmark_rows"), list) or not isinstance(bundle.get("index_rows"), list) or not isinstance(bundle.get("stock_rows"), list):
        raise ValueError("protected_bundle_rows_invalid")
    digest = sha256(raw).hexdigest()
    return {"bundle": bundle, "sha256": digest, "session_date": expected_session,
            "signature_verified": True, "source_authorization_attested": False,
            "promotion_allowed": False, "signals_enabled": False}
