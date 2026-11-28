"""Post-collection candidate generation. No network, signing or publication."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from .market_artifact_generation import generate_market_candidates
from .trusted_artifact_store import _timestamp


def run_daily_candidate_handoff(bundle_dir, candidate_dir, *, session_date,
                                decision_time, trusted_registry_path=None):
    session = date.fromisoformat(session_date)
    if session.isoformat() != session_date:
        raise ValueError("invalid_session_date")
    cutoff = _timestamp(decision_time, "decision_time")
    if session > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("future_session")
    source = Path(bundle_dir).resolve()
    output = Path(candidate_dir).resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("candidate_storage_must_be_separate")
    if trusted_registry_path is not None:
        registry = Path(trusted_registry_path).resolve()
        if output == registry or output in registry.parents:
            raise ValueError("candidate_storage_overlaps_registry")
    path = source / (session_date + ".json")
    if not path.is_file():
        return {"status":"missing_reviewed_bundle","session_date":session_date,
                "promotion_allowed":False,"signals_enabled":False}
    if path.is_symlink():
        raise ValueError("bundle_symlink_not_allowed")
    raw = path.read_bytes()
    bundle = json.loads(raw)
    if not isinstance(bundle,dict):
        raise ValueError("invalid_bundle")
    if bundle.get("calendar",{}).get("sessions",[])[-1:] != [session_date]:
        raise ValueError("bundle_session_mismatch")
    if _timestamp(bundle.get("decision_time"),"bundle_decision_time") > cutoff:
        raise ValueError("bundle_after_cutoff")
    result = generate_market_candidates(bundle,output)
    if result["as_of_session"] != session_date:
        raise ValueError("generated_session_mismatch")
    return {"status":"review_required","session_date":session_date,
            "source_file_sha256":sha256(raw).hexdigest(),
            "manifest_path":result["manifest_path"],
            "manifest_sha256":result["manifest_sha256"],
            "promotion_allowed":False,"signals_enabled":False}
