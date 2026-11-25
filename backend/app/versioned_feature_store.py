"""Versioned, point-in-time feature snapshots with security/action joins.

Corporate actions are attached as known-at-decision-time context only. This
module intentionally does not rewrite historical OHLCV or infer adjustment
factors without an independently verified adjustment policy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.feature_pipeline import build_feature_snapshot
from app.temporal_registry import security_as_of, corporate_actions_as_of


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"unsupported snapshot value: {type(value).__name__}")


def build_versioned_feature_snapshot(records: list[dict], decision_time: str,
                                     security_records: list, corporate_action_records: list,
                                     expected_symbols: list[str] | None = None) -> dict[str, Any]:
    """Build features and attach as-of security/action evidence per observed symbol."""
    cutoff = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    if cutoff.tzinfo is None:
        raise ValueError("decision_time must be timezone-aware")
    cutoff_date = cutoff.date()
    features = build_feature_snapshot(records, decision_time, expected_symbols)
    symbols = sorted(features["security_features"])
    joins = {}
    for symbol in symbols:
        matches = [r for r in security_records if r.symbol.upper() == symbol]
        if not matches:
            joins[symbol] = {"security_status": "not_found", "corporate_actions": []}
            continue
        # Resolve by the matched stable security ID; conflicts remain ambiguous.
        ids = sorted({r.security_id for r in matches})
        if len(ids) != 1:
            joins[symbol] = {"security_status": "ambiguous", "corporate_actions": []}
            continue
        resolved = security_as_of(matches, cutoff_date)
        if resolved["status"] != "resolved":
            joins[symbol] = {"security_status": resolved["status"], "corporate_actions": []}
            continue
        security = resolved["record"]
        action_result = corporate_actions_as_of(corporate_action_records, security.security_id, decision_time)
        joins[symbol] = {
            "security_status": "resolved",
            "security_id": security.security_id,
            "security_evidence_ids": resolved.get("evidence_ids", []),
            "corporate_actions": [asdict(action) for action in action_result["actions"]],
            "corporate_action_count": action_result["included_count"],
            "corporate_action_evidence_ids": sorted({a.evidence_id for a in action_result["actions"]}),
        }
    body = {"schema_version": 1, "decision_time": features["decision_time"],
            "features": features, "security_and_action_joins": joins,
            "ohlcv_adjustment_applied": False}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=_json_default)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {**body, "snapshot_sha256": digest}


def persist_versioned_snapshot(root: str | Path, snapshot: dict) -> dict:
    """Write content-addressed snapshot once; conflicting content is never replaced."""
    digest = snapshot.get("snapshot_sha256")
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=_json_default)
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if not digest or digest != actual:
        raise ValueError("snapshot hash mismatch")
    directory = Path(root) / "feature-snapshots" / digest
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "snapshot.json"
    encoded = (json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=_json_default) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise RuntimeError("content-addressed snapshot conflict")
        return {"path": str(path), "idempotent": True, "snapshot_sha256": digest}
    return {"path": str(path), "idempotent": False, "snapshot_sha256": digest}
