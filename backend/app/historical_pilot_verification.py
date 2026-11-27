"""Fail-closed official first-execution evidence gate for the 2025 pilot."""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Iterable, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
OFFICIAL_SOURCES = {"nepse_official_floorsheet", "cdsc_official_record"}

def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed

def validate_official_first_trade_evidence(cohort_rows: Iterable[Mapping[str, object]], evidence_rows: Iterable[Mapping[str, object]], *, decision_cutoff: str) -> dict:
    """Match official contract evidence to cohort symbols; preserve every gap."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    cohort, evidence = list(cohort_rows), list(evidence_rows)
    symbols = [str(row.get("symbol", "")) for row in cohort]
    if not symbols or len(symbols) != len(set(symbols)) or any(not s for s in symbols):
        raise ValueError("cohort must contain unique nonblank symbols")
    accepted = {symbol: [] for symbol in symbols}
    rejected = []
    for index, row in enumerate(evidence):
        symbol, reason = str(row.get("symbol", "")), None
        if symbol not in accepted: reason = "symbol_not_in_pilot_cohort"
        elif row.get("source_type") not in OFFICIAL_SOURCES: reason = "source_not_official"
        elif not str(row.get("contract_id", "")).strip(): reason = "missing_contract_id"
        elif not str(row.get("security_id", "")).strip(): reason = "missing_permanent_security_id"
        elif not isinstance(row.get("raw_sha256"), str) or not _SHA256.fullmatch(row["raw_sha256"]): reason = "invalid_raw_sha256"
        elif not str(row.get("source_record_id", "")).strip(): reason = "missing_source_record_id"
        else:
            try:
                trade_date = date.fromisoformat(str(row.get("trade_date", "")))
                available, captured = _aware(row.get("available_at"), "available_at"), _aware(row.get("captured_at"), "captured_at")
                quantity, price = int(row.get("quantity", 0)), float(row.get("price", 0))
            except (ValueError, TypeError, OverflowError): reason = "invalid_trade_or_capture_fields"
            else:
                if trade_date.isoformat() != str(row.get("trade_date")) or quantity <= 0 or price <= 0: reason = "invalid_trade_date_quantity_or_price"
                elif available > cutoff or captured > cutoff: reason = "evidence_available_after_decision_cutoff"
                elif row.get("finality") != "final": reason = "record_not_final"
                elif row.get("record_status") != "verified": reason = "record_not_verified"
        if reason:
            rejected.append({"row": index, "symbol": symbol or None, "reason": reason})
        else:
            accepted[symbol].append({"trade_date": trade_date.isoformat(), "contract_id": str(row["contract_id"]), "security_id": str(row["security_id"]), "source_record_id": str(row["source_record_id"]), "raw_sha256": row["raw_sha256"], "quantity": quantity, "price": price})
    verified, unresolved = [], []
    for row in cohort:
        symbol, matches = str(row["symbol"]), accepted[str(row["symbol"])]
        if not matches:
            unresolved.append({"symbol": symbol, "status": "unverified_no_official_contract_evidence"})
            continue
        first_date = min(item["trade_date"] for item in matches)
        first = [item for item in matches if item["trade_date"] == first_date]
        if first_date != str(row.get("reported_first_trade_date", "")):
            unresolved.append({"symbol": symbol, "status": "official_boundary_conflicts_with_reported_date", "reported_date": row.get("reported_first_trade_date"), "official_first_date": first_date})
            continue
        verified.append({"symbol": symbol, "first_trade_date": first_date, "official_contract_count": len(first), "security_ids": sorted({x["security_id"] for x in first}), "evidence_ids": sorted({x["source_record_id"] for x in first}), "raw_hashes": sorted({x["raw_sha256"] for x in first})})
    return {"status": "verified_subset" if verified else "blocked", "cohort_count": len(cohort), "verified_count": len(verified), "unresolved_count": len(unresolved), "verified": verified, "unresolved": unresolved, "rejected_evidence": rejected, "all_cohort_first_trades_verified": len(verified) == len(cohort), "canonical_promotion_allowed": False, "backtest_admission_allowed": False, "production_enabled": False, "limitations": ["Only supplied official final records are assessed; no live source retrieval occurs.", "A first matching contract does not prove full-day source completeness.", "Conflicting permanent IDs and missing official sessions require separate resolution."]}
