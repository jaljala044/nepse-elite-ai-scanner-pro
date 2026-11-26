"""Eligibility checks over server-reviewed evidence, never upload assertions."""
from datetime import date, datetime
from pathlib import Path
import json
from types import MappingProxyType
from .scanner import quality_errors
from .point_in_time import eligible_as_of

APPROVED_SOURCES = {"sharehub", "chukul", "sharesansar", "nepsealpha", "nepse"}
OPEN = {"verified_open", "verified_exceptional_open"}

def assess(symbol, rows, decision_time, reviewed):
    errors = quality_errors(rows)
    if not rows:
        errors.append("no_rows")
    if errors:
        return errors
    for row in rows:
        day = str(row["date"])
        record = reviewed.get((symbol, day), {})
        if record.get("instrument_type") != "equity" or record.get("security_status") != "active":
            errors.append(day+":equity_eligibility_unverified")
        if record.get("session_status") not in OPEN:
            errors.append(day+":session_unverified")
        if record.get("source_id") not in APPROVED_SOURCES or not record.get("evidence_id"):
            errors.append(day+":source_unverified")
        if any(record.get(k) != row.get(k) for k in ("open","high","low","close","volume")):
            errors.append(day+":reviewed_values_mismatch")
        try:
            if not eligible_as_of(record, decision_time):
                errors.append(day+":availability_unverified_or_future")
        except (ValueError, TypeError, AttributeError):
            errors.append(day+":invalid_availability")
    return errors

def load_reviewed_rows(path):
    """Read a server-owned canonical manifest; never promote project-only decisions."""
    path = Path(path)
    if not path.exists():
        return MappingProxyType({})
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("records"), list):
        raise ValueError("invalid reviewed manifest")
    output = {}
    for entry in payload["records"]:
        if entry.get("canonical_promotion_allowed") is not True:
            continue
        symbol = entry["symbol"]
        day = date.fromisoformat(entry["date"]).isoformat()
        row = dict(entry, date=day)
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise ValueError("invalid canonical symbol")
        if quality_errors([row]) or not entry.get("security_id") or not entry.get("lifecycle_evidence_id") or not entry.get("session_evidence_id") or entry.get("price_basis_reviewed") is not True:
            raise ValueError("incomplete canonical evidence")
        if assess(symbol, [row], entry.get("available_at"), {(symbol, day): row}):
            raise ValueError("invalid canonical eligibility")
        key = (symbol, day)
        if key in output:
            raise ValueError("duplicate canonical key")
        output[key] = MappingProxyType(row)
    return MappingProxyType(output)

# Only a repository/deployment-owned manifest can authorize scanner rows.
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data/reference/scanner_canonical_reviewed_rows.json"
REVIEWED_ROWS = load_reviewed_rows(MANIFEST_PATH)
