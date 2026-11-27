"""Shared explicit quarantine-marker gate; not a substitute for evidence validation."""
from collections.abc import Mapping

def is_quarantined(row: Mapping) -> bool:
    """Reject explicit quarantine markers, including unresolved ledger dispositions."""
    for key in ("row_status", "status", "disposition", "quarantine_status"):
        value = str(row.get(key, "")).strip().lower()
        if value.startswith("quarantin"):
            return True
    return bool(row.get("quarantined") or row.get("quarantine_reasons"))
