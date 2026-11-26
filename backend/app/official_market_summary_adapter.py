"""Validate pinned NEPSE official market-summary captures without promotion.

A successful HTTPS capture proves origin and bytes, not exchange-session
completeness or finality. Records remain review-only until a separate,
server-controlled finality/session attestation is supplied.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

SOURCE_ID = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
ENDPOINT_PATH = "/api/nots/market-summary-history"
OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
METRICS = {
    "total_turnover": ("totalTurnover", "total_turnover"),
    "total_traded_shares": ("totalTradedShares", "total_traded_shares"),
    "total_transactions": ("totalTransactions", "total_transactions", "totalTransaction"),
    "traded_scrips": ("tradedScrips", "traded_scrips"),
}


class MarketSummaryCaptureError(ValueError):
    """Raised when a pinned official capture fails evidence validation."""


def _aware(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise MarketSummaryCaptureError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MarketSummaryCaptureError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MarketSummaryCaptureError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _path(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise MarketSummaryCaptureError("raw_payload_path_missing")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or "\\" in value:
        raise MarketSummaryCaptureError("raw_payload_path_unsafe")
    base = root.resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise MarketSummaryCaptureError("raw_payload_path_escapes_root")
    return resolved


def _metric(row: dict, aliases: tuple[str, ...], label: str) -> float:
    value = next((row[key] for key in aliases if key in row), None)
    if value is None or isinstance(value, bool):
        raise MarketSummaryCaptureError(f"{label}_missing_or_invalid")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise MarketSummaryCaptureError(f"{label}_missing_or_invalid") from None
    if not number.is_finite() or number <= 0:
        raise MarketSummaryCaptureError(f"{label}_must_be_finite_and_positive")
    return float(number)


def validate_official_market_summary_capture(
    root: str | Path,
    *,
    report_path: str,
    raw_payload_path: str,
    decision_time: str,
    max_age_days: int = 7,
) -> dict:
    """Verify raw bytes and normalize official observations as review-only rows.

    The result deliberately sets finality_status=unverified and
    evidence_gate_passed=False. It cannot be consumed as final turnover
    evidence until a separate session/finality attestation exists.
    """
    if isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError("max_age_days_must_be_nonnegative_integer")
    cutoff = _aware(decision_time, "decision_time")
    base = Path(root)
    report_file = _path(base, report_path)
    raw_file = _path(base, raw_payload_path)
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
        raw = raw_file.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketSummaryCaptureError("capture_report_or_raw_payload_unavailable") from exc
    if not isinstance(report, dict):
        raise MarketSummaryCaptureError("capture_report_must_be_object")
    if report.get("source_id") != SOURCE_ID:
        raise MarketSummaryCaptureError("unexpected_source_id")
    parsed_url = urlparse(str(report.get("source_url", "")))
    if (parsed_url.scheme != "https" or parsed_url.hostname not in OFFICIAL_HOSTS
            or parsed_url.port not in (None, 443) or parsed_url.path.rstrip("/") != ENDPOINT_PATH):
        raise MarketSummaryCaptureError("official_source_origin_or_endpoint_unverified")
    if report.get("http_status") != 200 or report.get("response_origin_verified") is not True:
        raise MarketSummaryCaptureError("official_response_status_or_origin_unverified")
    if report.get("response_preserved") is not True:
        raise MarketSummaryCaptureError("raw_response_not_preserved")
    digest = sha256(raw).hexdigest()
    expected = report.get("response_sha256")
    if not isinstance(expected, str) or digest != expected.lower():
        raise MarketSummaryCaptureError("raw_response_sha256_mismatch")
    if report.get("response_bytes") != len(raw):
        raise MarketSummaryCaptureError("raw_response_byte_count_mismatch")

    retrieved_at = _aware(report.get("retrieved_at_utc"), "retrieved_at_utc")
    if retrieved_at > cutoff:
        raise MarketSummaryCaptureError("capture_retrieved_after_decision_time")
    if cutoff - retrieved_at > timedelta(days=max_age_days):
        raise MarketSummaryCaptureError("capture_stale")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        raise MarketSummaryCaptureError("market_summary_payload_must_be_nonempty_list")

    rows = []
    seen = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise MarketSummaryCaptureError(f"row_{index}_not_object")
        raw_date = next((item[key] for key in ("businessDate", "business_date", "businessdate", "date") if key in item), None)
        if not isinstance(raw_date, str):
            raise MarketSummaryCaptureError(f"row_{index}_date_missing")
        try:
            session = datetime.fromisoformat(raw_date[:10]).date().isoformat()
        except ValueError:
            raise MarketSummaryCaptureError(f"row_{index}_date_invalid") from None
        if session in seen:
            raise MarketSummaryCaptureError(f"duplicate_market_summary_date_{session}")
        seen.add(session)
        normalized = {
            name: _metric(item, aliases, name) for name, aliases in METRICS.items()
        }
        rows.append({
            "record_type": "market_summary",
            "market_code": "NEPSE",
            "session_date": session,
            **normalized,
            "source_id": SOURCE_ID,
            "source_payload_sha256": digest,
            "available_at": retrieved_at.isoformat(),
            "source_validation_status": "verified",
            "finality_status": "unverified",
            "evidence_gate_passed": False,
            "evidence_class": "official_exchange_response_review_only",
        })

    return {
        "status": "review_only",
        "source_id": SOURCE_ID,
        "source_url": report["source_url"],
        "source_payload_sha256": digest,
        "retrieved_at": retrieved_at.isoformat(),
        "record_count": len(rows),
        "first_session": min(row["session_date"] for row in rows),
        "last_session": max(row["session_date"] for row in rows),
        "rows": rows,
        "promotion_allowed": False,
        "finality_status": "unverified",
        "evidence_gate_passed": False,
        "limitations": [
            "HTTP 200 and official HTTPS origin verify source and transport, not finality",
            "An observed market-summary date is not a complete exchange-session calendar",
            "No missing dates are interpreted as holidays or no-trade sessions",
            "Rows cannot enter the verified turnover calculator until separate finality and session evidence is approved",
        ],
    }
