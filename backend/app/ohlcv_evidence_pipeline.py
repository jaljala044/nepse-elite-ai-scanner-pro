"""OHLCV ingestion gate joining parsed rows to dated universe/session evidence."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import PurePosixPath
from app.ohlcv_csv_adapter import OhlcvCsvMapping, parse_ohlcv_csv
from app.session_evidence import resolve_session_state
from .issue5_quarantine import EXPECTED_SHA256, Quarantine


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("availability timestamps must be ISO-8601 strings")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("availability timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def run_ohlcv_evidence_pipeline(payload: bytes, *, source_id: str,
                                mapping: OhlcvCsvMapping,
                                instrument_lifecycle: list[dict],
                                session_evidence: list,
                                decision_time: str,
                                availability_by_key: dict | None = None) -> dict:
    """Annotate each row; unknown membership/calendar/PIT state remains quarantined."""
    cutoff = _utc(decision_time)
    parsed = parse_ohlcv_csv(payload, source_id=source_id, mapping=mapping)
    by_symbol = {}
    for instrument in instrument_lifecycle:
        symbol = str(instrument.get("symbol", "")).strip().upper()
        if symbol:
            by_symbol.setdefault(symbol, []).append(instrument)

    output = []
    counts = {"eligible_for_review": 0, "quarantined": 0}
    for row in parsed["rows"]:
        symbol, session = row["symbol"], date.fromisoformat(row["session_date"])
        candidates = []
        for instrument in by_symbol.get(symbol, []):
            try:
                start = date.fromisoformat(instrument["valid_from"])
                end = date.fromisoformat(instrument["valid_to"]) if instrument.get("valid_to") else None
            except (KeyError, ValueError, TypeError):
                continue
            if start <= session and (end is None or session <= end):
                candidates.append(instrument)
        reasons = []
        if len(candidates) != 1:
            reasons.append("security_identity_missing_or_ambiguous")
        elif not str(candidates[0].get("security_id", "")).strip():
            reasons.append("security_master_id_missing")
        elif str(candidates[0].get("status", "")).casefold() not in {"active", "listed", "trading"}:
            reasons.append("security_not_active_on_session_date")
        session_state = resolve_session_state(session, session_evidence, decision_time)
        if not session_state["is_confirmed_trading_session"]:
            reasons.append("exchange_session_not_primary_evidence_verified")
        key = f"{symbol}|{session.isoformat()}"
        available_at = (availability_by_key or {}).get(key)
        if available_at is None:
            reasons.append("source_available_at_unknown")
        else:
            try:
                if _utc(available_at) > cutoff:
                    reasons.append("row_not_available_at_decision_time")
            except (TypeError, ValueError):
                reasons.append("invalid_source_available_at")
        if row["exception_flags"]:
            reasons.extend(row["exception_flags"])
        enriched = {
            **row,
            "security_id": candidates[0].get("security_id") if len(candidates) == 1 else None,
            "session_evidence": {
                "status": session_state["status"],
                "session_state": session_state["session_state"],
                "evidence_ids": session_state["evidence_ids"],
            },
            "source_available_at": available_at,
            "point_in_time_status": "verified_as_of_decision" if available_at is not None
                and not any(x in reasons for x in ("source_available_at_unknown",
                    "row_not_available_at_decision_time", "invalid_source_available_at")) else "unknown_or_late",
            "row_status": "eligible_for_review" if not reasons else "quarantined",
            "quarantine_reasons": sorted(set(reasons)),
        }
        output.append(enriched)
        counts[enriched["row_status"]] += 1
    rejected_rows = [item for item in parsed["exceptions"] if item.get("status") == "rejected"]
    if parsed["input_rows"] != len(output) + len(rejected_rows):
        raise AssertionError("OHLCV parser row conservation failed")
    return {
        "source_id": source_id, "source_payload_sha256": parsed["source_payload_sha256"],
        "input_rows": parsed["input_rows"], "parsed_rows": parsed["parsed_rows"],
        "rows": output, "rejected_rows": rejected_rows,
        "counts": {**counts, "parser_rejected": len(rejected_rows)},
        "row_conservation_passed": True,
        "promotion_allowed": False,
        "policy": "require_dated_security_primary_session_and_point_in_time_evidence_retain_parser_rejections",
    }


def run_archive_ohlcv_evidence_pipeline(payload: bytes, *, source_id: str,
                                        mapping: OhlcvCsvMapping,
                                        instrument_lifecycle: list[dict],
                                        session_evidence: list,
                                        decision_time: str,
                                        repository: str,
                                        commit_sha: str,
                                        source_file: str,
                                        source_file_sha256: str,
                                        archive_guard: Quarantine | None,
                                        availability_by_key: dict | None = None) -> dict:
    """Run the OHLCV evidence pipeline with the pinned Issue #5 archive overlay.

    This explicit entry point is for immutable GitHub archive CSVs. Missing guard,
    incomplete locators, a non-canonical archive path, or a raw-file hash mismatch
    quarantines every parsed row. A locator absent from the overlay is not cleared;
    it proceeds only through the existing identity/session/rights/PIT gates.
    """
    result = run_ohlcv_evidence_pipeline(
        payload, source_id=source_id, mapping=mapping,
        instrument_lifecycle=instrument_lifecycle, session_evidence=session_evidence,
        decision_time=decision_time, availability_by_key=availability_by_key,
    )

    path = PurePosixPath(source_file) if isinstance(source_file, str) else None
    locator_valid = (
        isinstance(repository, str)
        and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is not None
        and isinstance(commit_sha, str)
        and re.fullmatch(r"[0-9a-f]{40}", commit_sha) is not None
        and path is not None
        and not path.is_absolute()
        and "\\" not in source_file
        and ".." not in path.parts
        and source_file.startswith("03_stock_charts_ohlcv/")
        and source_file.lower().endswith(".csv")
        and isinstance(source_file_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", source_file_sha256) is not None
    )
    file_hash_matches = source_file_sha256 == result["source_payload_sha256"]
    guard_valid = isinstance(archive_guard, Quarantine)

    for row in result["rows"]:
        locator = {
            "repository": repository,
            "commit_sha": commit_sha,
            "source_file": source_file,
            "source_file_sha256": source_file_sha256,
            "target_csv_row": row["source_row_number"],
            "target_date": row["session_date"],
        }
        row.update(locator)
        reasons = list(row["quarantine_reasons"])
        if not locator_valid:
            reasons.append("archive_source_provenance_invalid")
        if not file_hash_matches:
            reasons.append("archive_source_file_hash_mismatch")
        if not guard_valid:
            reasons.append("archive_quarantine_guard_missing")
        if locator_valid and file_hash_matches and guard_valid:
            disposition = archive_guard.disposition(row)
            if disposition != "not_in_overlay_requires_other_gates":
                reasons.append("archive_quarantine:" + disposition)
            row["archive_quarantine_disposition"] = disposition
        else:
            row["archive_quarantine_disposition"] = "held_guard_or_provenance_unavailable"
        row["quarantine_reasons"] = sorted(set(reasons))
        row["row_status"] = "eligible_for_review" if not row["quarantine_reasons"] else "quarantined"

    counts = {"eligible_for_review": 0, "quarantined": 0}
    for row in result["rows"]:
        counts[row["row_status"]] += 1
    result["counts"] = {**counts, "parser_rejected": len(result["rejected_rows"])}
    result["archive_quarantine"] = {
        "guard_applied": guard_valid and locator_valid and file_hash_matches,
        "overlay_sha256": EXPECTED_SHA256 if guard_valid else None,
        "overlay_record_count": len(archive_guard.rows) if guard_valid else 0,
        "source_file_sha256_matches_payload": file_hash_matches,
        "promotion_allowed": False,
    }
    result["policy"] += "_plus_issue5_pinned_archive_quarantine"
    result["promotion_allowed"] = False
    return result
