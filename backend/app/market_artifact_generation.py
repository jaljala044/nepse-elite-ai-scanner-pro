"""Generate candidates from supplied reviewed inputs, never approve evidence."""
from hashlib import sha256
import json
from pathlib import Path

from .daily_market_participation import daily_market_participation
from .index_intelligence import build_verified_rotation_dashboard
from .verified_sector_rotation import build_verified_sector_rotation


def _write_immutable(root, raw, suffix):
    digest = sha256(raw).hexdigest()
    path = root / (digest + suffix)
    try:
        with path.open("xb") as out:
            out.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError("existing_artifact_hash_conflict")
    return path.name, digest


def generate_market_candidates(bundle, output_dir):
    """Calculate three candidate artifacts, retaining hashes and no admission flag.

    Input is an already normalized bundle. A caller's verification flags are
    not independent source evidence. Nothing here writes a deployment registry.
    """
    if not isinstance(bundle, dict):
        raise ValueError("invalid_input_bundle")
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    cutoff = bundle["decision_time"]
    calendar = bundle["calendar"]
    universe = bundle["universe"]
    sessions = calendar["sessions"]
    symbols = universe["symbols"]
    # Daily calculator checks calendar and universe provenance and availability.
    daily = daily_market_participation(bundle["daily_rows"], expected_symbols=symbols,
        universe=universe, calendar=calendar, decision_time=cutoff,
        benchmark_rows=bundle["benchmark_rows"])
    if daily["status"] != "research_only":
        raise ValueError("daily_evidence_incomplete")
    rotation = build_verified_rotation_dashboard(bundle["index_rows"],
        verified_session_dates=sessions, expected_indices=bundle["expected_indices"],
        decision_time=cutoff)
    sector = build_verified_sector_rotation(bundle["stock_rows"], bundle["benchmark_rows"],
        expected_sector_members=bundle["expected_sector_members"],
        sector_membership=bundle["sector_membership"], verified_session_dates=sessions,
        decision_time=cutoff)
    if rotation["status"] != "research_only" or sector["status"] != "observed":
        raise ValueError("rotation_or_sector_evidence_incomplete")
    if len({daily["as_of_session"], rotation["as_of"], sector["as_of_session"]}) != 1:
        raise ValueError("candidate_session_mismatch")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    entries = {}
    for name, data in (("daily_market_participation", daily), ("index_rotation", rotation),
                       ("sector_rotation", sector)):
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        filename, digest = _write_immutable(root, raw, ".json")
        entries[name] = {"payload_path": filename, "payload_sha256": digest,
                         "byte_count": len(raw), "status": "review_required"}
    manifest = {"schema_version": 1, "status": "review_required",
                "input_bundle_sha256": sha256(canonical).hexdigest(),
                "decision_time": cutoff, "as_of_session": daily["as_of_session"],
                "artifacts": entries, "promotion_allowed": False,
                "signals_enabled": False}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    name, digest = _write_immutable(root, raw, ".manifest.json")
    return {"manifest_path": name, "manifest_sha256": digest, **manifest}
