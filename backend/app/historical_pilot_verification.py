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


def validate_official_first_trade_evidence(
    cohort_rows: Iterable[Mapping[str, object]],
    evidence_rows: Iterable[Mapping[str, object]],
    *,
    decision_cutoff: str,
    validated_capture_reports: Mapping[str, Mapping[str, object]] | None = None,
) -> dict:
    """Accept only first-trade rows bound to exact pages in validated capture reports."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    cohort, evidence = list(cohort_rows), list(evidence_rows)
    symbols = [str(row.get("symbol", "")) for row in cohort]
    if not symbols or len(symbols) != len(set(symbols)) or any(not s for s in symbols):
        raise ValueError("cohort must contain unique nonblank symbols")

    expected_ids: dict[str, str] = {}
    seen_ids: dict[str, str] = {}
    cohort_identity_errors = []
    for row in cohort:
        symbol = str(row["symbol"])
        security_id = row.get("security_id")
        if not isinstance(security_id, str) or not security_id.strip():
            cohort_identity_errors.append({"symbol": symbol, "reason": "cohort_expected_security_id_missing"})
            continue
        if security_id in seen_ids and seen_ids[security_id] != symbol:
            cohort_identity_errors.append({"symbol": symbol, "reason": "cohort_security_id_reused", "security_id": security_id})
            continue
        seen_ids[security_id] = symbol
        expected_ids[symbol] = security_id

    capture_reports = validated_capture_reports if isinstance(validated_capture_reports, Mapping) else {}
    validated_by_id: dict[str, list[Mapping[str, object]]] = {}
    for report in capture_reports.values():
        if not isinstance(report, Mapping) or report.get("status") != "CAPTURE_VALIDATED":
            continue
        capture_id = report.get("capture_id")
        if isinstance(capture_id, str) and capture_id.strip():
            validated_by_id.setdefault(capture_id, []).append(report)

    accepted = {symbol: [] for symbol in symbols}
    rejected = []
    for index, row in enumerate(evidence):
        symbol, reason = str(row.get("symbol", "")), None
        if symbol not in accepted:
            reason = "symbol_not_in_pilot_cohort"
        elif row.get("source_type") not in OFFICIAL_SOURCES:
            reason = "source_not_official"
        elif not str(row.get("contract_id", "")).strip():
            reason = "missing_contract_id"
        elif symbol not in expected_ids:
            reason = "cohort_expected_security_id_missing"
        elif str(row.get("security_id", "")).strip() != expected_ids.get(symbol):
            reason = "security_id_does_not_match_cohort_identity"
        elif not isinstance(row.get("raw_sha256"), str) or not _SHA256.fullmatch(row["raw_sha256"]):
            reason = "invalid_raw_sha256"
        elif not str(row.get("source_record_id", "")).strip():
            reason = "missing_source_record_locator"
        elif not str(row.get("capture_id", "")).strip():
            reason = "missing_capture_id"
        elif not str(row.get("source_id", "")).strip() or not str(row.get("publisher_id", "")).strip():
            reason = "missing_capture_source_or_publisher_identity"
        elif not str(row.get("payload_id", "")).strip():
            reason = "missing_payload_id"
        elif isinstance(row.get("page_number"), bool) or not isinstance(row.get("page_number"), int) or row["page_number"] < 1:
            reason = "invalid_page_number"
        else:
            reports = validated_by_id.get(str(row["capture_id"]), [])
            if len(reports) != 1:
                reason = "capture_id_not_uniquely_bound_to_validated_capture"
            else:
                report = reports[0]
                if row.get("source_id") != report.get("source_id") or row.get("publisher_id") != report.get("publisher_id"):
                    reason = "capture_source_or_publisher_mismatch"
                else:
                    pages = report.get("verified_pages", [])
                    matches = [
                        page for page in pages if isinstance(page, Mapping)
                        and page.get("page_number") == row.get("page_number")
                        and page.get("payload_id") == row.get("payload_id")
                        and page.get("raw_sha256") == row.get("raw_sha256")
                    ] if isinstance(pages, list) else []
                    if len(matches) != 1:
                        reason = "first_trade_evidence_not_bound_to_validated_page_hash"
                    else:
                        try:
                            trade_date = date.fromisoformat(str(row.get("trade_date", "")))
                            available = _aware(row.get("available_at"), "available_at")
                            captured = _aware(row.get("captured_at"), "captured_at")
                            quantity, price = int(row.get("quantity", 0)), float(row.get("price", 0))
                            window_start = _aware(report.get("window_start"), "capture_window_start")
                            window_end = _aware(report.get("window_end"), "capture_window_end")
                        except (ValueError, TypeError, OverflowError):
                            reason = "invalid_trade_or_capture_fields"
                        else:
                            if trade_date.isoformat() != str(row.get("trade_date")) or quantity <= 0 or price <= 0:
                                reason = "invalid_trade_date_quantity_or_price"
                            elif available > cutoff or captured > cutoff:
                                reason = "evidence_available_after_decision_cutoff"
                            elif not (window_start.date() <= trade_date <= window_end.date()):
                                reason = "trade_date_outside_validated_capture_window"
                            elif row.get("finality") != "final":
                                reason = "record_not_final"
                            elif row.get("record_status") != "verified":
                                reason = "record_not_verified"
                            elif row.get("capture_complete") is not True:
                                reason = "official_day_capture_not_certified_complete"
        if reason:
            rejected.append({"row": index, "symbol": symbol or None, "reason": reason})
        else:
            accepted[symbol].append({
                "trade_date": trade_date.isoformat(), "contract_id": str(row["contract_id"]),
                "security_id": str(row["security_id"]), "source_record_id": str(row["source_record_id"]),
                "raw_sha256": row["raw_sha256"], "capture_id": row["capture_id"],
                "payload_id": row["payload_id"], "page_number": row["page_number"],
                "quantity": quantity, "price": price,
            })

    verified, unresolved = [], []
    for row in cohort:
        symbol = str(row["symbol"])
        matches = accepted[symbol]
        if symbol not in expected_ids:
            unresolved.append({"symbol": symbol, "status": "cohort_expected_security_id_missing"})
            continue
        if not matches:
            unresolved.append({"symbol": symbol, "status": "unverified_no_capture_bound_official_contract_evidence"})
            continue
        first_date = min(item["trade_date"] for item in matches)
        first = [item for item in matches if item["trade_date"] == first_date]
        ids = {item["security_id"] for item in first}
        if ids != {expected_ids[symbol]}:
            unresolved.append({"symbol": symbol, "status": "conflicting_or_unexpected_permanent_security_ids", "security_ids": sorted(ids), "expected_security_id": expected_ids[symbol]})
            continue
        if first_date != str(row.get("reported_first_trade_date", "")):
            unresolved.append({"symbol": symbol, "status": "official_boundary_conflicts_with_reported_date", "reported_date": row.get("reported_first_trade_date"), "official_first_date": first_date})
            continue
        verified.append({
            "symbol": symbol, "first_trade_date": first_date, "security_id": expected_ids[symbol],
            "official_contract_count": len(first),
            "evidence_ids": sorted({x["source_record_id"] for x in first}),
            "raw_hashes": sorted({x["raw_sha256"] for x in first}),
            "capture_ids": sorted({x["capture_id"] for x in first}),
        })
    return {
        "status": "verified_subset" if verified else "blocked",
        "cohort_count": len(cohort), "verified_count": len(verified),
        "unresolved_count": len(unresolved), "verified": verified,
        "unresolved": unresolved, "cohort_identity_errors": cohort_identity_errors,
        "rejected_evidence": rejected,
        "all_cohort_first_trades_verified": len(verified) == len(cohort) and not cohort_identity_errors,
        "canonical_promotion_allowed": False, "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "Only supplied official final records bound to exact pages in validated captures are assessed.",
            "A first matching contract does not prove full-day source completeness.",
            "Permanent security identity must be supplied from a separately reviewed effective-dated security master.",
        ],
    }
