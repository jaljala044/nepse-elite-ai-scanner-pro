"""Eligibility checks over server-reviewed evidence, never upload assertions."""
from datetime import date, datetime
from pathlib import Path
import json
import re
from types import MappingProxyType

from .scanner import quality_errors
from .point_in_time import eligible_as_of

APPROVED_SOURCES = {"sharehub", "chukul", "sharesansar", "nepsealpha", "nepse"}
OPEN = {"verified_open", "verified_exceptional_open"}
APPROVED_PRICE_BASES = {"verified_unadjusted_no_actions", "verified_adjusted"}
APPROVED_CORPORATE_ACTION_STATES = {"clear", "adjusted_verified"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def assess(symbol, rows, decision_time, reviewed):
    """Fail closed unless every OHLCV row has complete, matching evidence.

    This is the runtime gate, so it deliberately repeats identity, lifecycle,
    session, source, corporate-action and price-basis requirements rather than
    relying on a manifest loader having been the only caller.
    """
    errors = quality_errors(rows)
    if not rows:
        errors.append("no_rows")
    if errors:
        return errors
    for row in rows:
        day = str(row["date"])
        record = reviewed.get((symbol, day), {})
        prefix = day + ":"
        if (record.get("symbol") != symbol
                or str(record.get("date")) != day
                or not _nonblank(record.get("security_id"))):
            errors.append(prefix + "security_identity_unverified")
        if (record.get("instrument_type") != "equity"
                or record.get("security_status") != "active"
                or not _nonblank(record.get("lifecycle_evidence_id"))):
            errors.append(prefix + "equity_lifecycle_unverified")
        if (record.get("session_status") not in OPEN
                or not _nonblank(record.get("session_evidence_id"))):
            errors.append(prefix + "session_unverified")
        if (record.get("source_id") not in APPROVED_SOURCES
                or not _nonblank(record.get("evidence_id"))
                or not SHA256_RE.fullmatch(str(record.get("source_payload_sha256", "")).lower())):
            errors.append(prefix + "source_provenance_unverified")
        if (record.get("price_basis_reviewed") is not True
                or record.get("price_basis_status") not in APPROVED_PRICE_BASES):
            errors.append(prefix + "price_basis_unverified")
        if (record.get("corporate_action_status") not in APPROVED_CORPORATE_ACTION_STATES
                or not _nonblank(record.get("corporate_action_evidence_id"))):
            errors.append(prefix + "corporate_action_clearance_unverified")
        if any(record.get(k) != row.get(k) for k in ("open", "high", "low", "close", "volume")):
            errors.append(prefix + "reviewed_values_mismatch")
        try:
            if not eligible_as_of(record, decision_time):
                errors.append(prefix + "availability_unverified_or_future")
        except (ValueError, TypeError, AttributeError):
            errors.append(prefix + "invalid_availability")
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
        symbol = entry.get("symbol")
        day = date.fromisoformat(entry["date"]).isoformat()
        row = dict(entry, date=day)
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise ValueError("invalid canonical symbol")
        if quality_errors([row]):
            raise ValueError("invalid canonical OHLCV")
        key = (symbol, day)
        if key in output:
            raise ValueError("duplicate canonical key")
        errors = assess(symbol, [row], entry.get("available_at"), {key: row})
        if errors:
            raise ValueError("incomplete canonical evidence: " + ",".join(errors))
        output[key] = MappingProxyType(row)
    return MappingProxyType(output)


# Only a repository/deployment-owned manifest can authorize scanner rows.
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data/reference/scanner_canonical_reviewed_rows.json"
REVIEWED_ROWS = load_reviewed_rows(MANIFEST_PATH)
