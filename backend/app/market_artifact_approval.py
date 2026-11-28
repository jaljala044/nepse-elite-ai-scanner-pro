"""Offline verification of reviewer-signed candidate approvals.

The public key must come from independently controlled deployment configuration.
No signing key is stored here and verification never publishes a registry.
"""
import base64
import binascii
from hashlib import sha256
import json
from pathlib import Path
from .trusted_artifact_store import _timestamp, _safe_payload_path


def verify_market_approval(root, approval_bytes, signature, *, public_key_pem,
                           expected_reviewer_id, decision_time):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    key = load_pem_public_key(public_key_pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("reviewer_key_must_be_ed25519")
    try:
        key.verify(base64.b64decode(signature, validate=True), approval_bytes)
    except (InvalidSignature, ValueError, TypeError, binascii.Error):
        raise ValueError("approval_signature_invalid") from None
    approval = json.loads(approval_bytes)
    if (not isinstance(approval, dict) or approval.get("schema_version") != 1
            or approval.get("reviewer_id") != expected_reviewer_id
            or not isinstance(expected_reviewer_id, str) or not expected_reviewer_id.strip()
            or approval.get("decision") != "approved_for_research"
            or approval.get("signals_enabled") is not False):
        raise ValueError("approval_scope_invalid")
    cutoff = _timestamp(decision_time, "decision_time")
    approved_at = _timestamp(approval.get("approved_at"), "approved_at")
    if approved_at > cutoff:
        raise ValueError("approval_after_cutoff")
    root = Path(root)
    manifest_path = _safe_payload_path(root, approval.get("manifest_path"))
    raw = manifest_path.read_bytes()
    digest = sha256(raw).hexdigest()
    if digest != approval.get("manifest_sha256") or manifest_path.name != digest + ".manifest.json":
        raise ValueError("approval_manifest_hash_mismatch")
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or manifest.get("status") != "review_required"
            or manifest.get("promotion_allowed") is not False
            or manifest.get("signals_enabled") is not False
            or approval.get("input_bundle_sha256") != manifest.get("input_bundle_sha256")
            or not isinstance(manifest.get("input_bundle_sha256"), str)
            or len(manifest["input_bundle_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in manifest["input_bundle_sha256"])
            or approved_at < _timestamp(manifest.get("decision_time"), "manifest_decision_time")):
        raise ValueError("manifest_scope_invalid")
    entries = manifest.get("artifacts")
    expected = {"daily_market_participation", "index_rotation", "sector_rotation"}
    if not isinstance(entries, dict) or set(entries) != expected:
        raise ValueError("manifest_modules_invalid")
    for name, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("status") != "review_required":
            raise ValueError("manifest_entry_invalid")
        path = _safe_payload_path(root, entry.get("payload_path"))
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        if (digest != entry.get("payload_sha256") or path.name != digest + ".json"
                or type(entry.get("byte_count")) is not int or len(raw) != entry["byte_count"]):
            raise ValueError("approved_payload_hash_mismatch")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("signals_enabled") is not False:
            raise ValueError("approved_payload_scope_invalid")
        session = payload.get("as_of") if name == "index_rotation" else payload.get("as_of_session")
        if session != manifest.get("as_of_session"):
            raise ValueError("approved_payload_session_mismatch")
    return {"status": "signature_verified", "reviewer_id": expected_reviewer_id,
            "manifest_sha256": approval["manifest_sha256"], "manifest": manifest,
            "registry_published": False, "signals_enabled": False}
