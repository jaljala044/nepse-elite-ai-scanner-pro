"""Read-only quarantine audit of declared training input and outcome windows.

A clean audit is necessary but not sufficient for independent dataset approval.
"""
from datetime import date
import hashlib
import json
from .historical_quarantine import QUARANTINE

def audit_training_windows(rows):
    if not isinstance(rows, list) or not rows:
        return {"status": "blocked", "reasons": ["dataset_windows_missing"], "row_count": 0}
    reasons = []
    seen = set()
    for i, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise ValueError()
            identity = row["record_id"]
            symbol = row["symbol"]
            if not isinstance(identity, str) or not identity.strip() or not isinstance(symbol, str) or not symbol.strip():
                raise ValueError()
            symbol = symbol.strip().upper()
            start = date.fromisoformat(row["history_start"]).isoformat()
            decision = date.fromisoformat(row["observation_date"]).isoformat()
            end = date.fromisoformat(row["outcome_end"]).isoformat()
            if not start <= decision <= end:
                raise ValueError()
            if identity in seen:
                reasons.append(f"duplicate_record:{i}")
            seen.add(identity)
            for ticker, day in sorted(QUARANTINE):
                if ticker == symbol and start <= day <= end:
                    reasons.append(f"historical_quarantine:{i}:{symbol}:{day}")
        except (KeyError, ValueError, TypeError):
            reasons.append(f"invalid_window_lineage:{i}")
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    registry_digest = hashlib.sha256(json.dumps(sorted(QUARANTINE), separators=(",", ":")).encode()).hexdigest()
    return {"status": "blocked" if reasons else "declared_windows_clear",
            "reasons": reasons, "row_count": len(rows), "declared_windows_sha256": digest,
            "quarantine_registry_sha256": registry_digest,
            "independent_dataset_clearance": False, "model_training_allowed": False}
