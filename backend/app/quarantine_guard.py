"""Shared explicit quarantine-marker gate; not a substitute for evidence validation."""
from collections.abc import Mapping

def is_quarantined(row: Mapping) -> bool:
    """Reject explicit quarantine markers, including unresolved ledger dispositions."""
    for key in ("row_status", "status", "disposition", "quarantine_status"):
        value = str(row.get(key, "")).strip().lower()
        if value.startswith("quarantin"):
            return True
    return bool(row.get("quarantined") or row.get("quarantine_reasons"))


from datetime import date
import hashlib
import json
from pathlib import Path

def quarantine_keys(path, expected_sha256):
    """Load a pinned OHLCV exception ledger. Reject malformed or changed input."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("quarantine ledger hash mismatch")
    ledger = json.loads(raw)
    rows = ledger.get("exceptions")
    if ledger.get("schema_version") != "1.0" or not isinstance(rows, list):
        raise ValueError("invalid quarantine ledger schema")
    if ledger.get("counts", {}).get("total_exception_records") != len(rows):
        raise ValueError("quarantine ledger count mismatch")
    keys = set()
    ids = set()
    for row in rows:
        identity = row["exception_id"]
        if not identity or identity in ids:
            raise ValueError("invalid or duplicate exception ID")
        ids.add(identity)
        symbol = row["symbol"].strip().upper()
        day = date.fromisoformat(row["trade_date"]).isoformat()
        if not symbol or not row.get("disposition"):
            raise ValueError("invalid quarantine ledger record")
        # No automatic release: every listed exception remains blocked.
        keys.add((symbol, day))
    return frozenset(keys)

def reject_quarantined_history(rows, symbol, keys):
    """Reject entire history rather than bridging a missing candle."""
    symbol = symbol.strip().upper()
    for row in rows:
        day = row.get("session_date", row.get("trade_date", row.get("date")))
        if is_quarantined(row) or (symbol, date.fromisoformat(str(day)).isoformat()) in keys:
            raise ValueError("quarantined historical input")
