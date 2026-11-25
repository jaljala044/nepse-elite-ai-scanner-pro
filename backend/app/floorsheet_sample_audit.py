"""Conservative acceptance report for a real, explicitly mapped floorsheet CSV sample."""
from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal, InvalidOperation

from app.floorsheet_contract import FloorsheetContract

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def build_floorsheet_sample_acceptance_report(
    parsed: dict,
    reconciled: dict,
    *,
    mapping_reviewed: bool = False,
    verified_session_dates: list[str] | None = None,
) -> dict:
    """Summarize a sample without granting source rights or canonical promotion."""
    if not isinstance(parsed, dict) or not isinstance(reconciled, dict):
        raise ValueError("parsed and reconciled results must be objects")
    source_id = parsed.get("source_id")
    digest = parsed.get("source_payload_sha256")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a nonblank string")
    if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest.lower()):
        raise ValueError("source_payload_sha256 must be a 64-character hex digest")
    if not isinstance(mapping_reviewed, bool):
        raise ValueError("mapping_reviewed must be boolean")

    rows = parsed.get("rows")
    rejected = parsed.get("errors")
    audit_rows = reconciled.get("rows")
    if not isinstance(rows, list) or not isinstance(rejected, list) or not isinstance(audit_rows, list):
        raise ValueError("parsed rows/errors and reconciliation rows must be lists")
    if any(not isinstance(row, FloorsheetContract) for row in rows):
        raise ValueError("parsed rows must contain FloorsheetContract records")
    if len(rows) != len(audit_rows):
        raise ValueError("parsed and reconciled row counts must match")
    if parsed.get("parsed_rows") != len(rows):
        raise ValueError("parsed_rows count does not match row payload")
    input_rows = parsed.get("input_data_rows")
    if isinstance(input_rows, bool) or not isinstance(input_rows, int) or input_rows != len(rows) + len(rejected):
        raise ValueError("input_data_rows must equal parsed plus rejected rows")
    if reconciled.get("input_rows") != len(rows) or reconciled.get("output_rows") != len(audit_rows):
        raise ValueError("reconciliation control totals do not match parsed rows")

    supplied_sessions = verified_session_dates or []
    if not isinstance(supplied_sessions, list):
        raise ValueError("verified_session_dates must be a list")
    session_set = set()
    for value in supplied_sessions:
        if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
            raise ValueError("verified session dates must use YYYY-MM-DD")
        session_set.add(value)

    dates = sorted({row.trade_date for row in rows})
    symbols = sorted({row.symbol for row in rows})
    buyer_codes = sorted({row.buyer_broker_code for row in rows})
    seller_codes = sorted({row.seller_broker_code for row in rows})
    broker_codes = sorted(set(buyer_codes) | set(seller_codes))
    disposition_counts = Counter()
    amount_exception_count = 0
    total_quantity = Decimal("0")
    total_amount = Decimal("0")
    for audit in audit_rows:
        if not isinstance(audit, dict):
            raise ValueError("reconciliation rows must be objects")
        disposition = audit.get("duplicate_disposition")
        if disposition not in {"unique", "exact_duplicate", "conflicting_duplicate"}:
            raise ValueError("reconciliation row has an unknown duplicate disposition")
        disposition_counts[disposition] += 1
        if not isinstance(audit.get("amount_reconciliation_exception"), bool):
            raise ValueError("amount_reconciliation_exception must be boolean")
        amount_exception_count += int(audit["amount_reconciliation_exception"])
    for row in rows:
        total_quantity += row.quantity
        total_amount += row.amount

    rejected_ratio = (len(rejected) / input_rows) if input_rows else None
    clean = (
        not rejected
        and disposition_counts.get("exact_duplicate", 0) == 0
        and disposition_counts.get("conflicting_duplicate", 0) == 0
        and amount_exception_count == 0
        and mapping_reviewed
        and all(value in session_set for value in dates)
    )
    return {
        "source_id": source_id,
        "source_payload_sha256": digest.lower(),
        "input_data_rows": input_rows,
        "parsed_rows": len(rows),
        "rejected_rows": len(rejected),
        "rejected_row_ratio": rejected_ratio,
        "trade_date_count": len(dates),
        "first_trade_date": dates[0] if dates else None,
        "last_trade_date": dates[-1] if dates else None,
        "trade_dates": dates,
        "calendar_unverified_dates": [value for value in dates if value not in session_set],
        "unique_symbols": symbols,
        "unique_symbol_count": len(symbols),
        "unique_buyer_broker_codes": buyer_codes,
        "unique_seller_broker_codes": seller_codes,
        "unique_broker_code_count": len(broker_codes),
        "duplicate_disposition_counts": dict(disposition_counts),
        "amount_reconciliation_exception_count": amount_exception_count,
        "total_quantity": str(total_quantity),
        "total_amount": str(total_amount),
        "mapping_reviewed": mapping_reviewed,
        "sample_quality_gate": "passed_for_rights_review" if clean else "review_required",
        "source_rights_status": "not_assessed",
        "promotion_allowed": False,
        "training_eligible": False,
        "policy": "sample_audit_only_no_calendar_or_rights_inference",
    }
