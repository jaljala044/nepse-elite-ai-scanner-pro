"""P4.26 primary notice archive and corporate-action evidence gates.

Accepts operator-supplied immutable documents and ledger rows. It performs no
network requests, does not infer missing identity links, and never adjusts OHLCV.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

PRIMARY_HOSTS = {"nepalstock.com.np", "www.nepalstock.com", "cdsc.com.np", "www.cdsc.com.np"}
SECONDARY_TIERS = {"secondary_notice", "secondary_metadata", "secondary_first_trade"}
ACTION_TYPES = {"bonus", "rights", "split", "reverse_split", "cash_dividend", "stock_dividend", "merger", "demerger"}
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed


def _iso_day(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field}_missing_or_invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}_invalid") from exc


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _safe_file(root: Path, relative: str) -> Path:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("unsafe_archive_relative_path")
    resolved_root = root.resolve()
    resolved = (root / Path(*candidate.parts)).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("archive_path_escapes_root")
    return resolved


def validate_primary_notice_archive(
    *, entries: list[dict[str, Any]], archive_root: str | Path,
    decision_cutoff: str, required_event_ids: list[str],
) -> dict:
    """Verify archived PDF bytes and provenance for required primary lifecycle notices."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    root = Path(archive_root)
    errors: list[dict] = []
    verified: dict[str, dict] = {}
    for index, row in enumerate(entries):
        event_id = str(row.get("event_id", "")).strip()
        if not event_id:
            errors.append({"index": index, "reason": "event_id_missing"})
            continue
        if event_id in verified:
            errors.append({"event_id": event_id, "reason": "duplicate_document_entry"})
            continue
        try:
            source_url = str(row.get("source_url", "")).strip()
            parsed = urlparse(source_url)
            if parsed.scheme != "https" or parsed.hostname not in PRIMARY_HOSTS:
                raise ValueError("source_not_approved_primary_https_host")
            if row.get("http_status") != 200:
                raise ValueError("document_http_status_not_200")
            if str(row.get("content_type", "")).split(";")[0].strip().lower() != "application/pdf":
                raise ValueError("document_content_type_not_pdf")
            retrieved = _aware(row.get("retrieved_at"), "retrieved_at")
            available = _aware(row.get("available_at"), "available_at")
            if retrieved > cutoff or available > cutoff:
                raise ValueError("document_evidence_after_decision_cutoff")
            if available > retrieved:
                raise ValueError("document_available_after_retrieval")
            relative = str(row.get("archive_path", "")).strip()
            path = _safe_file(root, relative)
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if not raw.startswith(b"%PDF-"):
                raise ValueError("archived_bytes_not_pdf")
            if len(raw) < 100:
                raise ValueError("archived_pdf_too_small")
            if not _sha(row.get("sha256")) or digest != row["sha256"].lower():
                raise ValueError("archived_pdf_sha256_mismatch")
            if not str(row.get("publisher_id", "")).strip():
                raise ValueError("publisher_identity_missing")
            if not str(row.get("document_title", "")).strip():
                raise ValueError("document_title_missing")
            verified[event_id] = {
                "event_id": event_id, "source_url": source_url, "archive_path": relative,
                "sha256": digest, "bytes": len(raw), "publisher_id": row["publisher_id"],
                "document_title": row["document_title"], "retrieved_at": retrieved.isoformat(),
                "available_at": available.isoformat(),
            }
        except (ValueError, OSError) as exc:
            errors.append({"event_id": event_id, "reason": str(exc)})
    missing = sorted(set(required_event_ids) - set(verified))
    extra = sorted(set(verified) - set(required_event_ids))
    if missing:
        errors.append({"reason": "required_primary_notices_not_archived", "event_ids": missing})
    if extra:
        errors.append({"reason": "unrequested_document_entries", "event_ids": extra})
    return {
        "status": "PRIMARY_NOTICE_ARCHIVE_VERIFIED" if not errors and not missing else "PRIMARY_NOTICE_ARCHIVE_BLOCKED",
        "required_event_count": len(set(required_event_ids)), "verified_document_count": len(verified),
        "verified_documents": [verified[key] for key in sorted(verified)],
        "missing_event_ids": missing, "errors": errors,
        "archive_manifest_sha256": hashlib.sha256(
            repr([(key, verified[key]["sha256"]) for key in sorted(verified)]).encode()
        ).hexdigest(),
        "historical_identity_promotion_allowed": False,
    }


def validate_predecessor_identity_evidence(
    *, records: list[dict[str, Any]], required_symbols: list[str],
    archive_report: dict, decision_cutoff: str,
) -> dict:
    """Require primary, archived evidence for each predecessor-to-successor mapping."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    docs = {item["event_id"]: item for item in archive_report.get("verified_documents", [])}
    errors: list[dict] = []
    accepted = {}
    for index, row in enumerate(records):
        symbol = str(row.get("predecessor_symbol", "")).strip().upper()
        if not symbol:
            errors.append({"index": index, "reason": "predecessor_symbol_missing"})
            continue
        try:
            effective = _iso_day(row.get("effective_from"), "effective_from")
            available = _aware(row.get("available_at"), "available_at")
            if available > cutoff:
                raise ValueError("identity_evidence_after_decision_cutoff")
            event_id = str(row.get("event_id", "")).strip()
            doc = docs.get(event_id)
            if not doc:
                raise ValueError("linked_primary_document_not_verified")
            if row.get("evidence_tier") != "primary_nepse_or_cdsc":
                raise ValueError("predecessor_identity_not_primary_evidence")
            if str(row.get("publisher_id", "")).strip() != doc["publisher_id"]:
                raise ValueError("publisher_id_differs_from_archived_document")
            if not str(row.get("predecessor_security_id", "")).strip() or not str(row.get("successor_symbol", "")).strip() or not str(row.get("successor_security_id", "")).strip():
                raise ValueError("predecessor_or_successor_security_id_missing")
            if row.get("independent_review_status") != "approved" or not str(row.get("reviewer_id", "")).strip():
                raise ValueError("independent_identity_review_missing")
            if symbol in accepted:
                raise ValueError("duplicate_predecessor_identity_record")
            accepted[symbol] = {
                "predecessor_symbol": symbol, "predecessor_security_id": str(row["predecessor_security_id"]),
                "successor_symbol": str(row["successor_symbol"]).strip().upper(),
                "successor_security_id": str(row["successor_security_id"]),
                "effective_from": effective.isoformat(), "event_id": event_id,
                "evidence_sha256": doc["sha256"], "reviewer_id": row["reviewer_id"],
            }
        except (ValueError, KeyError) as exc:
            errors.append({"symbol": symbol, "reason": str(exc)})
    missing = sorted(set(x.upper() for x in required_symbols) - set(accepted))
    if missing:
        errors.append({"reason": "predecessor_identity_evidence_missing", "symbols": missing})
    return {
        "status": "PREDECESSOR_IDENTITY_REVIEWED" if not errors and not missing else "PREDECESSOR_IDENTITY_BLOCKED",
        "required_symbol_count": len(set(x.upper() for x in required_symbols)),
        "accepted_count": len(accepted), "accepted_records": [accepted[k] for k in sorted(accepted)],
        "missing_symbols": missing, "errors": errors,
        "historical_join_admission_allowed": False,
    }


def validate_corporate_action_ledger(
    *, records: list[dict[str, Any]], decision_cutoff: str,
) -> dict:
    """Validate source-level action assertions; conflicting assertions block the event."""
    cutoff = _aware(decision_cutoff, "decision_cutoff")
    groups: dict[str, list[dict]] = defaultdict(list)
    errors: list[dict] = []
    for index, row in enumerate(records):
        action_id = str(row.get("action_id", "")).strip()
        try:
            if not action_id:
                raise ValueError("action_id_missing")
            symbol = str(row.get("symbol", "")).strip().upper()
            security_id = str(row.get("security_id", "")).strip()
            action_type = str(row.get("action_type", "")).strip().lower()
            if not symbol or not security_id:
                raise ValueError("security_identity_missing")
            if action_type not in ACTION_TYPES:
                raise ValueError("action_type_invalid")
            announced = _aware(row.get("announced_at"), "announced_at")
            available = _aware(row.get("available_at"), "available_at")
            ex_date = _iso_day(row.get("ex_date"), "ex_date")
            if announced > cutoff or available > cutoff:
                raise ValueError("action_evidence_after_decision_cutoff")
            if available < announced:
                raise ValueError("action_available_before_announcement")
            publisher = str(row.get("publisher_id", "")).strip()
            source_id = str(row.get("source_id", "")).strip()
            source_tier = str(row.get("source_tier", "")).strip()
            digest = row.get("evidence_sha256")
            if not publisher or not source_id:
                raise ValueError("action_source_provenance_missing")
            if source_tier not in {"primary_nepse_or_cdsc", "independent_secondary"}:
                raise ValueError("action_source_tier_invalid")
            if not _sha(digest):
                raise ValueError("action_evidence_hash_invalid")
            if row.get("status") not in {"announced", "confirmed", "cancelled", "rejected"}:
                raise ValueError("action_status_invalid")
            factor = None
            if action_type in {"bonus", "rights", "split", "reverse_split", "stock_dividend"}:
                try:
                    factor = Decimal(str(row.get("adjustment_factor")))
                    if not factor.is_finite() or factor <= 0:
                        raise InvalidOperation
                except (InvalidOperation, TypeError, ValueError):
                    raise ValueError("action_adjustment_factor_invalid") from None
                if not str(row.get("factor_methodology_id", "")).strip():
                    raise ValueError("factor_methodology_id_missing")
            if row.get("independent_review_status") not in {"pending", "approved", "rejected"}:
                raise ValueError("independent_review_status_invalid")
            groups[action_id].append({
                "action_id": action_id, "symbol": symbol, "security_id": security_id,
                "action_type": action_type, "announced_at": announced.isoformat(),
                "available_at": available.isoformat(), "ex_date": ex_date.isoformat(),
                "publisher_id": publisher, "source_id": source_id, "source_tier": source_tier,
                "evidence_sha256": digest.lower(), "status": row["status"],
                "adjustment_factor": str(factor) if factor is not None else None,
                "factor_methodology_id": row.get("factor_methodology_id"),
                "independent_review_status": row["independent_review_status"],
                "reviewer_id": row.get("reviewer_id"),
            })
        except (ValueError, KeyError) as exc:
            errors.append({"index": index, "action_id": action_id, "reason": str(exc)})
    accepted = []
    for action_id, assertions in sorted(groups.items()):
        publishers = {x["publisher_id"] for x in assertions}
        primary = {x["publisher_id"] for x in assertions if x["source_tier"] == "primary_nepse_or_cdsc"}
        facts = {(x["symbol"], x["security_id"], x["action_type"], x["ex_date"], x["status"], x["adjustment_factor"], x["factor_methodology_id"]) for x in assertions}
        if len(publishers) < 2 or not primary:
            errors.append({"action_id": action_id, "reason": "requires_two_publishers_including_primary"})
        if len(facts) != 1:
            errors.append({"action_id": action_id, "reason": "publisher_action_assertions_conflict"})
        approved_review = any(x["independent_review_status"] == "approved" and x["reviewer_id"] for x in assertions)
        if not approved_review:
            errors.append({"action_id": action_id, "reason": "independent_review_not_approved"})
        if len(publishers) >= 2 and primary and len(facts) == 1 and approved_review:
            accepted.append({"action_id": action_id, **assertions[0], "publisher_count": len(publishers)})
    return {
        "status": "CORPORATE_ACTION_LEDGER_REVIEW_READY" if accepted and not errors else "CORPORATE_ACTION_LEDGER_BLOCKED",
        "accepted_event_count": len(accepted), "accepted_events": accepted, "errors": errors,
        "price_adjustment_admission_allowed": False,
        "reason": "review-ready evidence still requires temporal identity gate and separately approved adjustment policy",
    }
