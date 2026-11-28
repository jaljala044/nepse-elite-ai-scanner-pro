"""Deployment-only publishing; approval must bind the exact registry and manifest.

Run under a single authorized deployment writer. Private reviewer keys are
never needed here. A verified signature attests approval, not source truth.
"""
import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path
from .market_artifact_approval import verify_market_approval
from .trusted_artifact_store import TrustedArtifactStore, _timestamp


def publish_approved_registry(root, registry_path, registry_bytes, approval_bytes, signature,
                              *, public_key_pem, expected_reviewer_id, decision_time):
    from zoneinfo import ZoneInfo
    result = verify_market_approval(root, approval_bytes, signature,
        public_key_pem=public_key_pem, expected_reviewer_id=expected_reviewer_id,
        decision_time=decision_time)
    approval = json.loads(approval_bytes)
    if approval.get("registry_sha256") != sha256(registry_bytes).hexdigest():
        raise ValueError("approval_registry_hash_mismatch")
    registry = json.loads(registry_bytes)
    manifest = result["manifest"]
    entries = manifest["artifacts"]
    if not isinstance(registry, dict) or set(registry) != set(entries):
        raise ValueError("registry_module_scope_invalid")
    for module, entry in registry.items():
        candidate = entries[module]
        if not isinstance(entry, dict) or any(entry.get(k) != candidate[k]
                for k in ("payload_path", "payload_sha256")):
            raise ValueError("registry_candidate_binding_invalid")
        if entry.get("as_of_date") != manifest["as_of_session"]:
            raise ValueError("registry_session_mismatch")
        if _timestamp(entry.get("available_at"),"available_at") < _timestamp(approval["approved_at"],"approved_at"):
            raise ValueError("registry_availability_precedes_approval")
    cutoff = _timestamp(decision_time,"decision_time")
    day = cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date().isoformat()
    admitted = TrustedArtifactStore(root,registry).load(decision_date=day,
        decision_time=decision_time,required_modules=tuple(sorted(entries)))
    if set(admitted) != set(entries) or any(v.get("evidence_gate_passed") is not True for v in admitted.values()):
        raise ValueError("registry_artifact_admission_failed")
    if len({v["session_calendar_id"] for v in admitted.values()}) != 1:
        raise ValueError("registry_calendar_mismatch")
    destination = Path(registry_path)
    if destination.exists():
        previous = json.loads(destination.read_bytes())
        if not isinstance(previous,dict) or set(previous)!=set(entries):
            raise ValueError("existing_registry_scope_requires_manual_reconciliation")
        if any(e.get("as_of_date","") > manifest["as_of_session"] for e in previous.values()):
            raise ValueError("registry_rollback_rejected")
        if destination.read_bytes() == registry_bytes:
            return {"status":"already_published","registry_sha256":sha256(registry_bytes).hexdigest(),
                    "signals_enabled":False}
    # Atomic on a single filesystem. Deployment must serialize authorized writers.
    fd, tmp = tempfile.mkstemp(prefix=".registry-",dir=destination.parent)
    try:
        with os.fdopen(fd,"wb") as handle:
            handle.write(registry_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp,destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {"status":"published_research_registry","registry_sha256":sha256(registry_bytes).hexdigest(),
            "signals_enabled":False}
