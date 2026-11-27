"""Assemble a deterministic pilot OHLCV panel from validated capture ingestions."""
from __future__ import annotations

import re
import math
from datetime import date, datetime
from typing import Iterable, Mapping

from app.historical_pilot_ingest import calculate_pilot_row_sha256
from app.historical_pilot_panel import build_lifecycle_panel_readiness

_FIELDS = ("open", "high", "low", "close", "volume")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _positive_integer(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a positive integer") from exc
    if str(value).strip() not in (str(number), f"{number}.0") or number < 1:
        raise ValueError(f"{field} must be a positive integer")
    return number


def assemble_lifecycle_pilot_panel(
    *,
    cohort_symbols: Iterable[str],
    security_master: Iterable[Mapping[str, object]],
    expected_sessions: Iterable[Mapping[str, object]],
    ingestion_reports: Iterable[Mapping[str, object]],
    corporate_action_status: Mapping[str, object],
    decision_cutoff: str,
    minimum_independent_sources: int = 1,
) -> dict:
    """Assemble only rows whose capture and normalized-row provenance still matches.

    The historical argument name is retained for compatibility, but the threshold
    counts distinct publisher identifiers only. It does not prove independence.
    """
    symbols = list(cohort_symbols)
    if not symbols or len(symbols) != len(set(symbols)) or any(
        not isinstance(symbol, str) or not symbol or symbol != symbol.strip() or symbol != symbol.upper()
        for symbol in symbols
    ):
        raise ValueError("cohort_symbols must be nonempty, unique, trimmed uppercase strings")
    if isinstance(minimum_independent_sources, bool) or not isinstance(minimum_independent_sources, int) or minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources must be a positive integer")
    try:
        cutoff = _aware(decision_cutoff, "decision_cutoff")
    except ValueError as exc:
        raise ValueError("decision_cutoff must be timezone-aware") from exc

    master = list(security_master)
    sessions = list(expected_sessions)
    reports = list(ingestion_reports)
    errors, grouped, seen_row_locators = [], {}, set()

    for report_index, report in enumerate(reports):
        if not isinstance(report, Mapping):
            errors.append({"ingestion_index": report_index, "reason": "ingestion_report_not_mapping"})
            continue
        if report.get("status") != "INGESTED" or report.get("all_rows_accepted") is not True:
            errors.append({"ingestion_index": report_index, "reason": "ingestion_report_not_fully_validated"})
            continue
        context = {
            "source_id": report.get("source_id"),
            "publisher_id": report.get("publisher_id"),
            "capture_id": report.get("capture_id"),
            "capture_manifest_sha256": report.get("capture_manifest_sha256"),
        }
        if (any(not isinstance(value, str) or not value.strip() for value in context.values())
                or not isinstance(context["capture_manifest_sha256"], str)
                or not _SHA256.fullmatch(context["capture_manifest_sha256"])):
            errors.append({"ingestion_index": report_index, "reason": "ingestion_capture_context_invalid"})
            continue
        rows = report.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append({"ingestion_index": report_index, "reason": "ingestion_rows_missing"})
            continue

        for row_index, row in enumerate(rows):
            prefix = {"ingestion_index": report_index, "row_index": row_index}
            if not isinstance(row, Mapping):
                errors.append({**prefix, "reason": "ingested_row_not_mapping"})
                continue
            try:
                symbol = row.get("symbol")
                if not isinstance(symbol, str) or symbol not in symbols or symbol != symbol.strip() or symbol != symbol.upper():
                    raise ValueError("symbol_not_canonical_or_outside_pilot_cohort")
                day_text = row.get("session_date")
                if not isinstance(day_text, str):
                    raise ValueError("session_date_not_text")
                day = date.fromisoformat(day_text)
                if day.isoformat() != day_text:
                    raise ValueError("session_date_not_canonical")

                values = {}
                for field in ("open", "high", "low", "close"):
                    raw_value = row.get(field)
                    if isinstance(raw_value, bool):
                        raise ValueError(f"{field}_not_numeric")
                    value = float(raw_value)
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError(f"{field}_not_finite_positive")
                    values[field] = value
                raw_volume = row.get("volume")
                if isinstance(raw_volume, bool):
                    raise ValueError("volume_not_whole_positive_share_count")
                volume_number = float(raw_volume)
                if not math.isfinite(volume_number) or not volume_number.is_integer() or volume_number <= 0:
                    raise ValueError("volume_not_whole_positive_share_count")
                values["volume"] = int(volume_number)
                if (values["low"] > min(values["open"], values["close"])
                        or values["high"] < max(values["open"], values["close"])
                        or values["high"] < values["low"]):
                    raise ValueError("ohlc_geometry_invalid")

                available_at = _aware(row.get("available_at"), "row.available_at")
                if available_at > cutoff:
                    raise ValueError("row_available_after_decision_cutoff")

                provenance = {}
                for field in ("source_id", "publisher_id", "capture_id", "payload_id"):
                    value = row.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{field}_missing")
                    provenance[field] = value
                provenance["capture_manifest_sha256"] = row.get("capture_manifest_sha256")
                if not isinstance(provenance["capture_manifest_sha256"], str) or not _SHA256.fullmatch(provenance["capture_manifest_sha256"]):
                    raise ValueError("capture_manifest_sha256_invalid")
                for field in ("source_id", "publisher_id", "capture_id", "capture_manifest_sha256"):
                    if provenance[field] != context[field]:
                        raise ValueError(f"row_{field}_does_not_match_ingestion_report")

                raw_hash, row_hash = row.get("raw_sha256"), row.get("row_sha256")
                if not isinstance(raw_hash, str) or not _SHA256.fullmatch(raw_hash):
                    raise ValueError("raw_sha256_invalid")
                if not isinstance(row_hash, str) or not _SHA256.fullmatch(row_hash):
                    raise ValueError("row_sha256_invalid")
                page_number = _positive_integer(row.get("page_number"), "page_number")
                source_row_number = _positive_integer(row.get("source_row_number"), "source_row_number")
                normalized = {
                    "symbol": symbol, "session_date": day_text, **values, **provenance,
                    "page_number": page_number, "source_row_number": source_row_number,
                    "raw_sha256": raw_hash,
                }
                if calculate_pilot_row_sha256(normalized) != row_hash:
                    raise ValueError("normalized_row_fingerprint_mismatch")

                locator = (provenance["capture_id"], provenance["payload_id"], page_number, source_row_number)
                if locator in seen_row_locators:
                    raise ValueError("duplicate_raw_row_locator")
                seen_row_locators.add(locator)
                normalized["available_at"] = row["available_at"]
                normalized["raw_sha256"] = raw_hash
                normalized["row_sha256"] = row_hash
                grouped.setdefault((symbol, day), []).append(normalized)
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                errors.append({**prefix, "symbol": row.get("symbol"), "reason": str(exc)})

    identity_by_symbol = {
        str(item.get("symbol")): item
        for item in master if isinstance(item, Mapping) and str(item.get("symbol")) in symbols
    }
    assembled, conflicts, insufficient = [], [], []
    for key in sorted(grouped, key=lambda item: (item[0], item[1])):
        symbol, day = key
        rows = grouped[key]
        distinct_values = {tuple(row.get(field) for field in _FIELDS) for row in rows}
        if len(distinct_values) != 1:
            conflicts.append({
                "symbol": symbol, "session_date": day.isoformat(),
                "source_ids": sorted({str(row["source_id"]) for row in rows}),
                "reason": "cross_source_ohlcv_conflict",
            })
            continue
        source_ids = sorted({str(row["source_id"]) for row in rows})
        publisher_ids = sorted({str(row["publisher_id"]) for row in rows})
        if len(publisher_ids) < minimum_independent_sources:
            insufficient.append({
                "symbol": symbol, "session_date": day.isoformat(),
                "publisher_ids": publisher_ids,
                "required_distinct_publishers": minimum_independent_sources,
            })
            continue

        identity = identity_by_symbol.get(symbol)
        if not identity or not str(identity.get("security_id", "")).strip():
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "permanent_security_identity_missing"})
            continue
        try:
            start = date.fromisoformat(str(identity.get("effective_from", "")))
            end = date.fromisoformat(str(identity["effective_to"])) if identity.get("effective_to") else None
        except (ValueError, TypeError):
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "invalid_security_lifecycle"})
            continue
        if start.isoformat() != str(identity.get("effective_from")) or (end and end.isoformat() != str(identity.get("effective_to"))):
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "security_lifecycle_date_not_canonical"})
            continue
        if day < start or (end and day > end):
            errors.append({"symbol": symbol, "session_date": day.isoformat(), "reason": "bar_outside_security_lifecycle"})
            continue

        first = sorted(rows, key=lambda row: (
            str(row["source_id"]), str(row["capture_id"]),
            int(row["page_number"]), int(row["source_row_number"]),
        ))[0]
        latest_available = max(((_aware(row["available_at"], "row.available_at"), str(row["available_at"])) for row in rows))[1]
        source_records = [
            {
                "source_id": row["source_id"], "publisher_id": row["publisher_id"],
                "capture_id": row["capture_id"], "payload_id": row["payload_id"],
                "page_number": row["page_number"], "source_row_number": row["source_row_number"],
                "raw_sha256": row["raw_sha256"], "row_sha256": row["row_sha256"],
                "capture_manifest_sha256": row["capture_manifest_sha256"],
                "available_at": row["available_at"],
            }
            for row in sorted(rows, key=lambda row: (
                str(row["source_id"]), str(row["capture_id"]),
                int(row["page_number"]), int(row["source_row_number"]),
            ))
        ]
        assembled.append({
            "symbol": symbol, "security_id": str(identity["security_id"]),
            "session_date": day.isoformat(),
            **dict(zip(_FIELDS, next(iter(distinct_values)))),
            "available_at": latest_available,
            "raw_sha256": first["raw_sha256"],
            "source_ids": source_ids, "publisher_ids": publisher_ids,
            "capture_ids": sorted({str(row["capture_id"]) for row in rows}),
            "row_hashes": sorted({str(row["row_sha256"]) for row in rows}),
            "source_records": source_records,
        })

    readiness_bars = [
        {key: row[key] for key in (
            "symbol", "session_date", "open", "high", "low", "close",
            "volume", "available_at", "raw_sha256",
        )}
        for row in assembled
    ]
    readiness = build_lifecycle_panel_readiness(
        cohort_symbols=symbols, security_master=master, expected_sessions=sessions,
        bars=readiness_bars, corporate_action_status=corporate_action_status,
        decision_cutoff=decision_cutoff,
    )
    ready = (
        readiness.get("status") == "READY_FOR_BOUNDED_RESEARCH"
        and not errors and not conflicts and not insufficient
    )
    return {
        "status": "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH" if ready else "BLOCKED",
        "panel_rows": assembled, "panel_row_count": len(assembled),
        "conflicts": conflicts, "insufficient_source_coverage": insufficient,
        "ingestion_errors": errors, "readiness_report": readiness,
        "minimum_distinct_publishers": minimum_independent_sources,
        "publisher_ids_are_independence_proof": False,
        "backtest_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "production_enabled": False,
        "limitations": [
            "Publisher-ID counts measure distinct identifiers only; they do not prove independent upstream feeds.",
            "Each row fingerprint binds normalized OHLCV to the exact manifest and raw-payload locator.",
            "Agreement between sources does not prove publisher independence or source completeness.",
            "No rows are synthesized for missing sessions; conflicts and gaps remain visible.",
            "A ready panel is bounded research only and requires separate human admission.",
        ],
    }
