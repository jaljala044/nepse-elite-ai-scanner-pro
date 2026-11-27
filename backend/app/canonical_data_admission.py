"""Immutable raw source capture and fail-closed canonical OHLCV admission.

This is a local evidence-ingestion contract. It does not fetch NEPSE endpoints,
authenticate a publisher, or convert a file hash into source authenticity.
Only trusted ingestion services should supply source attestations.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_COLUMNS = {
    "symbol", "security_id", "session_date", "open", "high", "low", "close",
    "volume", "turnover", "available_at",
}


def _aware(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(field + "_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(field + "_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def capture_raw_artifact(raw_bytes: bytes, *, source_id: str, source_uri: str,
                         publisher: str, captured_at: str, published_at: str | None,
                         rights_status: str, source_validation_status: str,
                         finality_status: str, output_root: str | Path) -> dict:
    """Persist bytes by SHA-256 without overwriting existing content."""
    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise ValueError("raw_bytes_must_be_nonempty_bytes")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id_required")
    if not isinstance(source_uri, str) or not source_uri.strip():
        raise ValueError("source_uri_required")
    if not isinstance(publisher, str) or not publisher.strip():
        raise ValueError("publisher_required")
    captured = _aware(captured_at, "captured_at")
    published = _aware(published_at, "published_at") if published_at else None
    if published and published > captured:
        raise ValueError("published_at_after_capture")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / (digest + ".raw")
    if raw_path.exists():
        if raw_path.is_symlink() or raw_path.read_bytes() != raw_bytes:
            raise RuntimeError("content_addressed_raw_artifact_conflict")
    else:
        with raw_path.open("xb") as stream:
            stream.write(raw_bytes)
    metadata = {
        "schema_version": 1,
        "source_id": source_id.strip(),
        "source_uri": source_uri.strip(),
        "publisher": publisher.strip(),
        "captured_at": captured.isoformat(),
        "published_at": published.isoformat() if published else None,
        "available_at": captured.isoformat(),
        "raw_byte_count": len(raw_bytes),
        "raw_sha256": digest,
        "raw_path": raw_path.name,
        "rights_status": rights_status,
        "source_validation_status": source_validation_status,
        "finality_status": finality_status,
        "capture_status": "captured",
        "authenticity_status": "not_established_by_hash",
    }
    metadata_path = root / (digest + ".manifest.json")
    encoded = (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode()
    if metadata_path.exists() and metadata_path.read_bytes() != encoded:
        raise RuntimeError("content_addressed_manifest_conflict")
    if not metadata_path.exists():
        with metadata_path.open("xb") as stream:
            stream.write(encoded)
    return metadata


def validate_and_admit_ohlcv_csv(*, raw_path: str | Path, manifest: Mapping[str, Any],
                                  expected_symbols: Mapping[str, str],
                                  verified_session_status: Mapping[str, str],
                                  decision_cutoff: str, adjustment_basis: str,
                                  minimum_coverage: Decimal = Decimal("0.98")) -> dict:
    """Validate point-in-time OHLCV rows; unresolved records are never promoted."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    reasons: list[str] = []
    if adjustment_basis not in {"raw", "split_adjusted", "total_return_adjusted"}:
        reasons.append("adjustment_basis_unsupported")
    if not isinstance(manifest, Mapping):
        manifest = {}
        reasons.append("manifest_missing")
    path = Path(raw_path)
    try:
        raw = path.read_bytes()
    except OSError:
        raw = b""
        reasons.append("raw_artifact_unavailable")
    actual_hash = hashlib.sha256(raw).hexdigest() if raw else None
    expected_hash = str(manifest.get("raw_sha256", "")).lower()
    if not _SHA256.fullmatch(expected_hash) or actual_hash != expected_hash:
        reasons.append("raw_sha256_mismatch")
    if manifest.get("raw_byte_count") != len(raw):
        reasons.append("raw_byte_count_mismatch")
    if manifest.get("rights_status") != "approved":
        reasons.append("source_rights_not_approved")
    if manifest.get("source_validation_status") != "verified":
        reasons.append("source_not_independently_validated")
    if manifest.get("finality_status") != "final":
        reasons.append("source_finality_not_verified")
    for field in ("source_id", "source_uri", "publisher"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            reasons.append(field + "_missing")
    available_at = None
    try:
        available_at = _aware(str(manifest.get("available_at")), "manifest_available_at")
        if available_at > cutoff:
            reasons.append("manifest_available_after_decision_cutoff")
    except ValueError:
        reasons.append("manifest_available_at_invalid")
    published_at = None
    if manifest.get("published_at"):
        try:
            published_at = _aware(str(manifest.get("published_at")), "manifest_published_at")
            if published_at > cutoff:
                reasons.append("manifest_published_after_decision_cutoff")
        except ValueError:
            reasons.append("manifest_published_at_invalid")

    expected = dict(expected_symbols) if isinstance(expected_symbols, Mapping) else {}
    sessions = dict(verified_session_status) if isinstance(verified_session_status, Mapping) else {}
    if not expected:
        reasons.append("expected_security_universe_missing")
    if not sessions:
        reasons.append("verified_session_calendar_missing")
    for day, state in sessions.items():
        try:
            date.fromisoformat(day)
        except (TypeError, ValueError):
            reasons.append("invalid_calendar_date:" + str(day))
        if state not in {"confirmed_trading_session", "confirmed_no_trade_session"}:
            reasons.append("calendar_session_not_verified:" + str(day))

    rows, seen, row_reasons = [], set(), []
    if raw:
        try:
            text = raw.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            columns = set(reader.fieldnames or [])
            missing = sorted(_REQUIRED_COLUMNS - columns)
            if missing:
                reasons.append("required_columns_missing:" + ",".join(missing))
            else:
                for line_number, row in enumerate(reader, start=2):
                    symbol = row.get("symbol", "")
                    security_id = row.get("security_id", "")
                    day = row.get("session_date", "")
                    key = (symbol, day)
                    issues = []
                    if symbol not in expected or expected.get(symbol) != security_id:
                        issues.append("security_identity_unverified")
                    try:
                        session_day = date.fromisoformat(day).isoformat()
                    except (TypeError, ValueError):
                        session_day = None
                        issues.append("session_date_invalid")
                    if session_day and sessions.get(session_day) != "confirmed_trading_session":
                        issues.append("not_a_verified_trading_session")
                    if key in seen:
                        issues.append("duplicate_symbol_session")
                    seen.add(key)
                    prices = {name: _decimal(row.get(name)) for name in ("open", "high", "low", "close")}
                    volume, turnover = _decimal(row.get("volume")), _decimal(row.get("turnover"))
                    if any(v is None or v <= 0 for v in prices.values()):
                        issues.append("ohlc_nonpositive_or_invalid")
                    elif prices["high"] < max(prices.values()) or prices["low"] > min(prices.values()):
                        issues.append("ohlc_relationship_invalid")
                    if volume is None or volume <= 0:
                        issues.append("volume_invalid")
                    if turnover is None or turnover < 0:
                        issues.append("turnover_invalid")
                    try:
                        row_available = _aware(row.get("available_at"), "row_available_at")
                        if row_available > cutoff:
                            issues.append("row_available_after_decision_cutoff")
                        if published_at and row_available < published_at:
                            issues.append("row_available_before_source_publication")
                    except ValueError:
                        issues.append("row_available_at_invalid")
                    rows.append({
                        "line_number": line_number, "symbol": symbol, "security_id": security_id,
                        "session_date": day,
                        "values": {
                            name: (str(prices[name]) if prices[name] is not None else None)
                            for name in ("open", "high", "low", "close")
                        } | {
                            "volume": str(volume) if volume is not None else None,
                            "turnover": str(turnover) if turnover is not None else None,
                        },
                        "status": "valid_candidate" if not issues else "quarantined",
                        "reasons": issues,
                    })
                    if issues:
                        row_reasons.extend(issues)
        except UnicodeDecodeError:
            reasons.append("raw_csv_not_utf8")
    expected_pairs = len(expected) * sum(
        1 for state in sessions.values() if state == "confirmed_trading_session"
    )
    valid_pairs = len({(r["symbol"], r["session_date"]) for r in rows if r["status"] == "valid_candidate"})
    coverage = (valid_pairs / expected_pairs) if expected_pairs else 0.0
    if expected_pairs and coverage < float(minimum_coverage):
        reasons.append("coverage_below_minimum")
    if row_reasons:
        reasons.append("one_or_more_rows_quarantined")
    if len(rows) != valid_pairs:
        reasons.append("record_count_or_duplicate_mismatch")
    reasons = list(dict.fromkeys(reasons))
    allowed = not reasons and bool(rows)
    return {
        "status": "admitted_for_research" if allowed else "blocked_or_quarantined",
        "admission_allowed": allowed,
        "production_promotion_allowed": False,
        "source_id": manifest.get("source_id"),
        "raw_sha256": actual_hash,
        "raw_byte_count": len(raw),
        "row_count": len(rows),
        "valid_row_count": valid_pairs,
        "quarantined_row_count": sum(r["status"] == "quarantined" for r in rows),
        "expected_security_session_pairs": expected_pairs,
        "coverage_ratio": coverage,
        "adjustment_basis": adjustment_basis,
        "rows": rows,
        "reasons": reasons,
        "policy": "immutable_raw_no_auto_repair_no_gap_fill_no_lookahead_no_production_promotion",
    }
