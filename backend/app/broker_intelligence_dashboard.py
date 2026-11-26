"""Read-only composition contract for the NEPSE broker intelligence dashboard.

This layer combines upstream P4.36/P4.37/P4.38/P4.39 artifacts. It does not
recompute or upgrade their evidence status, infer missing broker activity, or
turn broker flow into ownership/intent/trade signals.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class BrokerDashboardError(ValueError):
    """Invalid or temporally inconsistent dashboard evidence."""


_REQUIRED_WINDOWS = ("daily", "weekly", "monthly", "yearly")


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise BrokerDashboardError(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BrokerDashboardError(f"{field}_must_be_timezone_aware")
    return parsed


def _coverage(value, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise BrokerDashboardError(f"invalid_{field}") from None
    if not parsed.is_finite() or parsed < 0 or parsed > 1:
        raise BrokerDashboardError(f"invalid_{field}")
    return parsed


def build_broker_intelligence_dashboard(
    *, as_of_date: str, as_of_timestamp: str,
    rolling_profiles: dict, source_manifest: dict,
    sector_rotation_by_window: dict | None = None,
    candidates: list[dict] | None = None,
    min_coverage: Decimal = Decimal("0.95"),
) -> dict:
    """Compose point-in-time broker dashboard payload from upstream artifacts.

    Required profile windows are daily/weekly/monthly/yearly. A missing window
    is UNKNOWN, not zero. Source manifest is propagated as an upstream assertion;
    this function does not independently re-verify source files or broker identity.
    """
    try:
        cutoff_date = date.fromisoformat(as_of_date)
    except (TypeError, ValueError):
        raise BrokerDashboardError("as_of_date_must_be_iso") from None
    cutoff_time = _timestamp(as_of_timestamp, "as_of_timestamp")
    threshold = _coverage(min_coverage, "min_coverage")
    if threshold <= 0:
        raise BrokerDashboardError("min_coverage_must_be_positive")
    if not isinstance(rolling_profiles, dict) or not isinstance(source_manifest, dict):
        raise BrokerDashboardError("rolling_profiles_and_source_manifest_required")
    if rolling_profiles.get("as_of_date") != cutoff_date.isoformat():
        raise BrokerDashboardError("rolling_profiles_as_of_date_mismatch")
    try:
        profile_available = _timestamp(rolling_profiles["as_of_timestamp"], "profile_as_of_timestamp")
    except KeyError:
        raise BrokerDashboardError("profile_as_of_timestamp_required") from None
    if profile_available > cutoff_time:
        raise BrokerDashboardError("rolling_profiles_available_after_cutoff")

    manifest_status = source_manifest.get("status")
    source_ids = source_manifest.get("source_ids")
    if manifest_status != "verified":
        manifest_reason = "source_manifest_not_verified"
    elif not isinstance(source_ids, list) or not source_ids or any(
        not isinstance(item, str) or not item.strip() for item in source_ids
    ):
        manifest_reason = "source_manifest_source_ids_missing"
    else:
        manifest_reason = None
    manifest_coverage = _coverage(source_manifest.get("coverage"), "manifest_coverage")
    try:
        manifest_available = _timestamp(source_manifest["available_at"], "manifest_available_at")
    except KeyError:
        raise BrokerDashboardError("manifest_available_at_required") from None
    if manifest_available > cutoff_time:
        manifest_reason = "source_manifest_not_available_as_of_cutoff"
    if manifest_coverage < threshold:
        manifest_reason = "source_manifest_coverage_below_threshold"

    raw_profiles = rolling_profiles.get("profiles")
    if not isinstance(raw_profiles, list):
        raise BrokerDashboardError("rolling_profiles_list_required")
    grouped: dict[tuple[str, str], dict] = {}
    excluded_profiles = 0
    for row in raw_profiles:
        if not isinstance(row, dict):
            excluded_profiles += 1
            continue
        broker = row.get("broker_id")
        security = row.get("security_id")
        window = row.get("window")
        if not all(isinstance(x, str) and x.strip() for x in (broker, security, window)):
            excluded_profiles += 1
            continue
        if window not in _REQUIRED_WINDOWS:
            continue
        key = (broker, security)
        item = grouped.setdefault(key, {
            "broker_id": broker, "security_id": security, "windows": {},
        })
        if window in item["windows"]:
            raise BrokerDashboardError("duplicate_broker_security_window_profile")
        coverage = _coverage(row.get("coverage_ratio"), "profile_coverage")
        enough = (
            manifest_reason is None
            and row.get("status") == "descriptive_only"
            and coverage >= threshold
            and row.get("directional_summary") != "insufficient_evidence"
        )
        # Preserve the upstream daily detail and values; do not synthesize absent rows.
        item["windows"][window] = {
            "status": "available" if enough else "insufficient_evidence",
            "coverage": str(coverage),
            "requested_sessions": row.get("requested_sessions"),
            "expected_sessions": row.get("expected_sessions"),
            "complete_source_sessions": row.get("complete_source_sessions"),
            "buy_amount": row.get("buy_amount") if enough else None,
            "sell_amount": row.get("sell_amount") if enough else None,
            "net_amount": row.get("net_amount") if enough else None,
            "gross_amount": row.get("gross_amount") if enough else None,
            "buy_quantity": row.get("buy_quantity") if enough else None,
            "sell_quantity": row.get("sell_quantity") if enough else None,
            "net_quantity": row.get("net_quantity") if enough else None,
            "positive_net_sessions": row.get("positive_net_sessions") if enough else None,
            "negative_net_sessions": row.get("negative_net_sessions") if enough else None,
            "zero_activity_sessions": row.get("zero_activity_sessions") if enough else None,
            "positive_net_session_ratio": row.get("positive_net_session_ratio") if enough else None,
            "negative_net_session_ratio": row.get("negative_net_session_ratio") if enough else None,
            "broker_participation_ratio": row.get("broker_participation_ratio") if enough else None,
            "daily": row.get("daily") if enough else None,
            "directional_summary": row.get("directional_summary") if enough else "UNKNOWN",
        }

    broker_rows = []
    complete_window_count = 0
    required_window_count = len(grouped) * len(_REQUIRED_WINDOWS)
    for key in sorted(grouped):
        item = grouped[key]
        for name in _REQUIRED_WINDOWS:
            if name not in item["windows"]:
                item["windows"][name] = {"status": "unavailable", "coverage": None,
                                         "directional_summary": "UNKNOWN"}
        complete_window_count += sum(
            1 for name in _REQUIRED_WINDOWS if item["windows"][name]["status"] == "available"
        )
        broker_rows.append(item)

    rotations = sector_rotation_by_window or {}
    if not isinstance(rotations, dict):
        raise BrokerDashboardError("sector_rotation_by_window_must_be_mapping")
    sector_views = {}
    for window in ("daily", "weekly", "monthly", "yearly"):
        artifact = rotations.get(window)
        if artifact is None:
            sector_views[window] = {"status": "unavailable", "brokers": [],
                                    "reason": "sector_rotation_artifact_not_supplied"}
            continue
        if not isinstance(artifact, dict):
            raise BrokerDashboardError("invalid_sector_rotation_artifact")
        artifact_date = artifact.get("as_of_date")
        artifact_time = artifact.get("as_of_timestamp")
        if artifact_date != cutoff_date.isoformat():
            raise BrokerDashboardError("sector_rotation_as_of_date_mismatch")
        if artifact_time is None or _timestamp(artifact_time, "sector_rotation_as_of_timestamp") > cutoff_time:
            raise BrokerDashboardError("sector_rotation_not_available_as_of_cutoff")
        sector_views[window] = {
            "status": artifact.get("status", "unknown"),
            "prior_window": artifact.get("prior_window"),
            "current_window": artifact.get("current_window"),
            "prior_coverage": artifact.get("prior_coverage"),
            "current_coverage": artifact.get("current_coverage"),
            "excluded_rows": artifact.get("excluded_rows"),
            "brokers": artifact.get("brokers", []) if artifact.get("status") == "descriptive_only" else [],
            "policy": artifact.get("policy", "UNKNOWN"),
        }

    candidate_rows = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        available_at = candidate.get("available_at")
        candidate_date = candidate.get("as_of_date")
        try:
            candidate_available = _timestamp(available_at, "candidate_available_at")
            candidate_day = date.fromisoformat(candidate_date)
        except (TypeError, ValueError):
            candidate_rows.append({"symbol": candidate.get("symbol"), "status": "withheld",
                                   "classification": "UNKNOWN", "action": "NO_TRADE",
                                   "reason": "candidate_timestamp_or_date_invalid"})
            continue
        if candidate_day > cutoff_date or candidate_available > cutoff_time:
            candidate_rows.append({"symbol": candidate.get("symbol"), "status": "withheld",
                                   "classification": "UNKNOWN", "action": "NO_TRADE",
                                   "reason": "candidate_not_available_as_of_cutoff"})
            continue
        candidate_rows.append({
            "symbol": candidate.get("symbol"),
            "status": candidate.get("status", "unknown"),
            "classification": candidate.get("classification", "UNKNOWN"),
            "action": candidate.get("action", "NO_TRADE"),
            "probability": None,
            "reason": candidate.get("reason"),
            "source_ids": candidate.get("source_ids", []),
        })

    if manifest_reason:
        quality = "LOW_CONFIDENCE"
        overall_status = "withheld"
    elif required_window_count == 0 or complete_window_count < required_window_count:
        quality = "LOW_CONFIDENCE"
        overall_status = "partial"
    else:
        quality = "MEDIUM_CONFIDENCE"
        overall_status = "descriptive_only"

    return {
        "schema_version": "p4.40.1",
        "dashboard": "broker_intelligence",
        "mode": "research_only",
        "status": overall_status,
        "data_quality": quality,
        "as_of_date": cutoff_date.isoformat(),
        "as_of_timestamp": cutoff_time.isoformat(),
        "source_manifest": {
            "status": manifest_status if not manifest_reason else "withheld",
            "source_ids": sorted(set(source_ids)) if isinstance(source_ids, list) else [],
            "coverage": str(manifest_coverage),
            "available_at": manifest_available.isoformat(),
            "reason": manifest_reason,
            "verification_boundary": "upstream_assertion_propagated_not_independently_reverified",
        },
        "coverage": {
            "required_profile_windows": list(_REQUIRED_WINDOWS),
            "broker_security_pairs": len(grouped),
            "required_window_profiles": required_window_count,
            "available_window_profiles": complete_window_count,
            "excluded_profile_rows": excluded_profiles,
            "rolling_profile_excluded_observation_rows": rolling_profiles.get("excluded_observation_rows"),
            "verified_exchange_sessions": rolling_profiles.get("verified_exchange_sessions"),
            "complete_source_sessions": rolling_profiles.get("complete_source_sessions"),
        },
        "brokers": broker_rows,
        "sector_rotation": sector_views,
        "market_candidates": candidate_rows,
        "interpretation": (
            "Broker-side transaction behaviour and sector mix are descriptive only. "
            "They do not establish beneficial ownership, intent, manipulation, accumulation, "
            "distribution, or a BUY/SELL recommendation."
        ),
        "missing_data_policy": "UNKNOWN_NOT_ZERO_NO_IMPUTATION",
        "limitations": [
            "Upstream source assertions are propagated, not independently re-verified here.",
            "No missing broker/security/session rows are synthesized.",
            "A zero-activity figure is retained only when supplied by an upstream complete-session profile.",
            "No probability, BUY/SELL, entry, stop, target or backtest claim is generated.",
        ],
    }
