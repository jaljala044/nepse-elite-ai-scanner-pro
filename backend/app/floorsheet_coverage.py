"""Evidence-gated date × security floorsheet coverage classification.

This module never infers zero trading from an absent row alone. A zero-contract
result requires a confirmed open session, complete source capture, reconciled
independent controls, and verified active-instrument status.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _iso_day(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("date must be an ISO-8601 string")
    return date.fromisoformat(value).isoformat()


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value.lower()))


def build_floorsheet_coverage_manifest(
    sessions: list[dict[str, Any]],
    instruments: list[dict[str, Any]],
    daily_evidence: list[dict[str, Any]],
    contract_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build explicit TRADED / NO_TRADE / UNKNOWN cells without filling gaps.

    Session rows: date, status='confirmed_open', source_id, source_payload_sha256.
    Instrument rows: symbol, effective_from, optional effective_to,
      status='verified', source_id, source_payload_sha256.
    Daily evidence rows: date, capture_status='complete_verified',
      control_status='reconciled', source_id, source_payload_sha256,
      source_row_count (may be zero), unique_contract_count.
    Contract observations: date, symbol, contract_count (>0), row_validation_status='verified'.
    """
    if not isinstance(sessions, list) or not sessions:
        raise ValueError("sessions must be a non-empty list")
    if not isinstance(instruments, list) or not instruments:
        raise ValueError("instruments must be a non-empty list")
    if not isinstance(daily_evidence, list):
        raise ValueError("daily_evidence must be a list")
    if not isinstance(contract_observations, list):
        raise ValueError("contract_observations must be a list")

    session_by_date: dict[str, dict[str, Any]] = {}
    for row in sessions:
        day = _iso_day(row.get("date"))
        if day in session_by_date:
            raise ValueError(f"duplicate session date: {day}")
        session_by_date[day] = row

    instrument_by_symbol: dict[str, dict[str, Any]] = {}
    for row in instruments:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in instrument_by_symbol:
            raise ValueError(f"blank or duplicate instrument symbol: {symbol!r}")
        start = _iso_day(row.get("effective_from"))
        end = _iso_day(row["effective_to"]) if row.get("effective_to") else None
        if end and end < start:
            raise ValueError(f"invalid lifecycle range for {symbol}")
        instrument_by_symbol[symbol] = {**row, "symbol": symbol,
                                         "effective_from": start, "effective_to": end}

    daily_by_date: dict[str, dict[str, Any]] = {}
    for row in daily_evidence:
        day = _iso_day(row.get("date"))
        if day in daily_by_date:
            raise ValueError(f"duplicate daily evidence date: {day}")
        daily_by_date[day] = row

    counts: dict[tuple[str, str], int] = {}
    for row in contract_observations:
        day = _iso_day(row.get("date"))
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol not in instrument_by_symbol:
            raise ValueError(f"unknown instrument in contract observations: {symbol!r}")
        count = row.get("contract_count")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("contract_count must be a positive integer")
        if row.get("row_validation_status") != "verified":
            raise ValueError(f"unverified contract observation for {symbol} on {day}")
        key = (day, symbol)
        if key in counts:
            raise ValueError(f"duplicate date × symbol observation: {day} {symbol}")
        counts[key] = count

    cells = []
    for day in sorted(session_by_date):
        session = session_by_date[day]
        daily = daily_by_date.get(day)
        session_ok = (
            session.get("status") == "confirmed_open"
            and isinstance(session.get("source_id"), str) and bool(session["source_id"].strip())
            and _valid_digest(session.get("source_payload_sha256"))
        )
        daily_ok = bool(
            daily
            and daily.get("capture_status") == "complete_verified"
            and daily.get("control_status") == "reconciled"
            and isinstance(daily.get("source_id"), str) and bool(daily["source_id"].strip())
            and _valid_digest(daily.get("source_payload_sha256"))
            and isinstance(daily.get("source_row_count"), int)
            and daily.get("source_row_count", -1) >= 0
            and isinstance(daily.get("unique_contract_count"), int)
            and daily.get("unique_contract_count", -1) >= 0
            and daily.get("source_row_count") == daily.get("unique_contract_count")
        )
        for symbol, instrument in sorted(instrument_by_symbol.items()):
            active = (
                instrument.get("status") == "verified"
                and instrument.get("as_of_status") == "verified"
                and instrument["effective_from"] <= day
                and (instrument["effective_to"] is None or day <= instrument["effective_to"])
                and isinstance(instrument.get("source_id"), str) and bool(instrument["source_id"].strip())
                and _valid_digest(instrument.get("source_payload_sha256"))
            )
            count = counts.get((day, symbol))
            if count is not None:
                status = "TRADED" if session_ok and daily_ok and active else "UNKNOWN"
                reason = None if status == "TRADED" else "trade_observed_but_session_or_coverage_contract_unverified"
            elif session_ok and daily_ok and active:
                status, reason = "NO_TRADE", "complete_reconciled_session_capture_contains_no_contract_for_active_symbol"
            else:
                status, reason = "UNKNOWN", "session_daily_coverage_or_instrument_lifecycle_not_verified"
            cells.append({
                "date": day, "symbol": symbol, "status": status,
                "contract_count": count if status == "TRADED" else (0 if status == "NO_TRADE" else None),
                "reason": reason,
                "session_evidence_verified": session_ok,
                "daily_coverage_verified": daily_ok,
                "instrument_lifecycle_verified": active,
                "daily_source_id": daily.get("source_id") if daily else None,
                "daily_source_payload_sha256": daily.get("source_payload_sha256") if daily else None,
            })

    counts_by_status = {name: sum(cell["status"] == name for cell in cells)
                        for name in ("TRADED", "NO_TRADE", "UNKNOWN")}
    return {
        "schema_version": "1.0",
        "status": "review_only_not_canonical",
        "session_count": len(session_by_date),
        "instrument_count": len(instrument_by_symbol),
        "cell_count": len(cells),
        "status_counts": counts_by_status,
        "coverage_complete": bool(cells) and counts_by_status["UNKNOWN"] == 0,
        "canonical_promotion_allowed": False,
        "cells": cells,
        "policy": "absence_is_no_trade_only_after_verified_open_session_complete_capture_reconciled_controls_and_active_instrument_lifecycle",
    }
