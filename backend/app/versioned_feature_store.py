"""Versioned, point-in-time feature snapshots with security/action joins.

Corporate actions are attached as known-at-decision-time context only. This
module intentionally does not rewrite historical OHLCV or infer adjustment
factors without an independently verified adjustment policy.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.feature_pipeline import build_feature_snapshot
from app.quarantine_guard import is_quarantined
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
            joins[symbol] = {"security_status": "not_found", "security_identity_verified": False, "corporate_actions": [], "corporate_action_adjustment_actions": []}
            continue
        # Resolve by the matched stable security ID; conflicts remain ambiguous.
        ids = sorted({r.security_id for r in matches})
        if len(ids) != 1:
            joins[symbol] = {"security_status": "ambiguous", "security_identity_verified": False, "corporate_actions": [], "corporate_action_adjustment_actions": []}
            continue
        resolved = security_as_of(matches, cutoff_date)
        if resolved["status"] != "resolved":
            joins[symbol] = {
                "security_status": resolved["status"],
                "security_identity_verified": False,
                "security_evidence_ids": resolved.get("evidence_ids", []),
                "corporate_actions": [],
                "corporate_action_adjustment_actions": [],
                "corporate_action_adjustment_eligible_count": 0,
                "corporate_action_excluded_unverified_count": 0,
                "corporate_action_point_in_time_eligible": False,
                "corporate_action_source_universe_completeness_verified": False,
            }
            continue
        security = resolved["record"]
        action_result = corporate_actions_as_of(corporate_action_records, security.security_id, decision_time)
        joins[symbol] = {
            "security_status": "resolved",
            "security_identity_verified": True,
            "security_id": security.security_id,
            "security_evidence_ids": resolved.get("evidence_ids", []),
            "corporate_actions": [asdict(action) for action in action_result["actions"]],
            "corporate_action_count": action_result["included_count"],
            "corporate_action_adjustment_actions": [
                asdict(action) for action in action_result["adjustment_actions"]
            ],
            "corporate_action_adjustment_eligible_count": action_result["adjustment_eligible_count"],
            "corporate_action_excluded_unverified_count": action_result["excluded_unverified_count"],
            "corporate_action_point_in_time_eligible": action_result["point_in_time_eligible"],
            "corporate_action_source_universe_completeness_verified": action_result["source_universe_completeness_verified"],
            "corporate_action_evidence_ids": sorted({a.evidence_id for a in action_result["actions"]}),
        }
    included_records = [
        row for row in records
        if not is_quarantined(row) and row.get("available_at") and datetime.fromisoformat(row["available_at"].replace("Z", "+00:00")) <= cutoff
    ]
    input_lineage = []
    for row in included_records:
        payload_hash = str(row.get("source_payload_sha256") or row.get("payload_sha256") or "").lower()
        input_lineage.append({
            "record_id": row.get("record_id"),
            "source_id": row.get("source_id"),
            "payload_sha256": payload_hash if re.fullmatch(r"[0-9a-f]{64}", payload_hash) else None,
            "source_row_number": row.get("source_row_number"),
            "available_at": row.get("available_at"),
        })
    lineage_complete = all(
        item["record_id"] and item["source_id"] and item["payload_sha256"]
        and isinstance(item["source_row_number"], int) and item["source_row_number"] > 0
        for item in input_lineage
    )
    body = {"schema_version": 1, "decision_time": features["decision_time"],
            "features": features, "security_and_action_joins": joins,
            "input_lineage": input_lineage,
            "input_lineage_status": "complete" if lineage_complete else "incomplete",
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
