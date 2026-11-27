"""Generate as-of feature snapshots and six-strategy research qualifications.

Each decision is rebuilt with its own point-in-time evidence manifest and,
when supplied, its own effective-dated sector membership snapshot.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.feature_pipeline import build_feature_snapshot
from app.scanner_strategy_integration import adapt_feature_snapshot_to_strategy_evidence
from app.scanner_strategy_lab import STRATEGIES, evaluate_strategy


HORIZONS = ("t_plus_2", "swing", "positional", "investment")


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _canonical_day(value, field):
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError(field + "_must_be_canonical_yyyy_mm_dd") from None
    if parsed.isoformat() != str(value):
        raise ValueError(field + "_must_be_canonical_yyyy_mm_dd")
    return parsed


def _withheld_symbol_series(expected_symbols, reason):
    result = {}
    for symbol in expected_symbols:
        result[symbol] = {}
        for strategy_id in STRATEGIES:
            result[symbol][strategy_id] = {
                "feature_evidence": {}, "missing_features": ["trusted_point_in_time_manifest"],
                "admitted_feature_count": 0, "required_feature_count": None,
                "qualification_by_horizon": {
                    horizon: {
                        "status": "withheld", "action": "NO_TRADE", "score": None,
                        "evidence_coverage_pct": "0", "history_passed": False,
                        "coverage_passed": False, "missing_features": ["trusted_point_in_time_manifest"],
                        "rejected_features": [reason], "accepted_evidence_clusters": {},
                    }
                    for horizon in HORIZONS
                },
            }
    return result


def _sector_snapshot_for_decision(*, session, cutoff, membership_by_session, expected_by_session):
    membership = membership_by_session.get(session) if isinstance(membership_by_session, dict) else None
    expected = expected_by_session.get(session) if isinstance(expected_by_session, dict) else None
    if not isinstance(membership, dict) or not isinstance(expected, dict) or not expected:
        return None, None, "point_in_time_sector_membership_missing"
    required = []
    expected_sector_by_symbol = {}
    for sector_code, members in expected.items():
        if not isinstance(sector_code, str) or not sector_code.strip() or not isinstance(members, list) or not members:
            return None, None, "point_in_time_sector_membership_invalid"
        normalized_members = [str(symbol).strip().upper() for symbol in members]
        required.extend(normalized_members)
        for member in normalized_members:
            expected_sector_by_symbol[member] = sector_code
    if not required or any(not symbol for symbol in required) or len(required) != len(set(required)):
        return None, None, "point_in_time_sector_membership_duplicate_or_blank"
    for symbol in required:
        record = membership.get(symbol)
        if not isinstance(record, dict):
            return None, None, "point_in_time_sector_membership_incomplete"
        available = _time(record.get("available_at"))
        try:
            effective_from = _canonical_day(record.get("effective_from"), "sector_effective_from")
            effective_to_raw = record.get("effective_to")
            effective_to = _canonical_day(effective_to_raw, "sector_effective_to") if effective_to_raw else None
        except ValueError:
            return None, None, "point_in_time_sector_membership_date_invalid"
        digest = str(record.get("source_payload_sha256", "")).lower()
        if (
            record.get("status") != "verified"
            or record.get("as_of_status") != "verified"
            or available is None or available > cutoff
            or effective_from > date.fromisoformat(session)
            or (effective_to is not None and date.fromisoformat(session) > effective_to)
            or not isinstance(record.get("source_id"), str) or not record["source_id"].strip()
            or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
            or record.get("sector_code") != expected_sector_by_symbol.get(symbol)
        ):
            return None, None, "point_in_time_sector_membership_unverified_or_lookahead"
    return membership, expected, None


def build_historical_feature_series(
    *, records, decision_points, expected_symbols, evidence_manifests,
    sector_membership=None, expected_sector_members=None,
    sector_membership_by_session=None, expected_sector_members_by_session=None,
):
    """Build chronological snapshots; static current sector mappings are never reused."""
    if not isinstance(records, list) or not records:
        raise ValueError("historical_records_required")
    if not isinstance(decision_points, list) or not decision_points:
        raise ValueError("decision_points_required")
    if not isinstance(expected_symbols, list) or not expected_symbols:
        raise ValueError("expected_symbols_required")
    if any(not isinstance(symbol, str) for symbol in expected_symbols):
        raise ValueError("expected_symbols_must_be_unique_nonblank")
    normalized_symbols = [symbol.strip().upper() for symbol in expected_symbols]
    if any(not symbol for symbol in normalized_symbols) or len(normalized_symbols) != len(set(normalized_symbols)):
        raise ValueError("expected_symbols_must_be_unique_nonblank")
    if not isinstance(evidence_manifests, dict):
        raise ValueError("evidence_manifests_required")

    parsed = []
    previous = None
    for point in decision_points:
        if not isinstance(point, dict):
            raise ValueError("decision_point_invalid")
        cutoff = _time(point.get("decision_time"))
        sessions = point.get("session_dates")
        if cutoff is None:
            raise ValueError("decision_time_must_be_timezone_aware")
        if not isinstance(sessions, list) or not sessions:
            raise ValueError("canonical_session_dates_required")
        if previous is not None and cutoff <= previous:
            raise ValueError("decision_points_must_be_strictly_chronological")
        parsed_sessions = [_canonical_day(day, "session_date") for day in sessions]
        if parsed_sessions != sorted(parsed_sessions) or len(parsed_sessions) != len(set(parsed_sessions)):
            raise ValueError("session_dates_must_be_unique_and_chronological")
        market_cutoff = cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date()
        if parsed_sessions[-1] > market_cutoff:
            raise ValueError("future_session_after_decision_cutoff")
        parsed.append((cutoff, [day.isoformat() for day in parsed_sessions]))
        previous = cutoff

    snapshots = []
    withheld = []
    for cutoff, sessions in parsed:
        key = cutoff.isoformat()
        session = sessions[-1]
        manifest = evidence_manifests.get(key)
        if not isinstance(manifest, dict) or not manifest:
            reason = "trusted_evidence_manifest_missing_or_empty"
            withheld.append({"decision_time": key, "reason": reason})
            snapshots.append({
                "decision_time": key, "as_of_session": session,
                "session_count": len(sessions),
                "feature_series": _withheld_symbol_series(normalized_symbols, reason),
                "status": "withheld_no_trusted_manifest",
                "sector_membership_status": "withheld",
                "production_enabled": False,
            })
            continue

        point_membership, point_expected, sector_reason = _sector_snapshot_for_decision(
            session=session, cutoff=cutoff,
            membership_by_session=sector_membership_by_session,
            expected_by_session=expected_sector_members_by_session,
        )
        snapshot = build_feature_snapshot(
            records, cutoff.isoformat(), normalized_symbols,
            sector_membership=point_membership,
            expected_sector_members=point_expected,
            session_dates=sessions,
        )
        adapted = adapt_feature_snapshot_to_strategy_evidence(
            feature_snapshot=snapshot, evidence_manifest=manifest,
            decision_time=cutoff.isoformat(),
        )
        session_count = len(sessions)
        symbols = {}
        for symbol, strategy_map in adapted["symbols"].items():
            symbols[symbol] = {}
            for strategy_id in STRATEGIES:
                item = strategy_map[strategy_id]
                symbols[symbol][strategy_id] = {
                    "feature_evidence": item["feature_evidence"],
                    "missing_features": item["missing_features"],
                    "admitted_feature_count": item["admitted_feature_count"],
                    "required_feature_count": item["required_feature_count"],
                    "qualification_by_horizon": {},
                }
                for horizon in HORIZONS:
                    result = evaluate_strategy(
                        strategy_id=strategy_id, symbol=symbol, horizon=horizon,
                        decision_time=cutoff.isoformat(), history_sessions=session_count,
                        feature_evidence=item["feature_evidence"],
                    )
                    symbols[symbol][strategy_id]["qualification_by_horizon"][horizon] = {
                        "status": result["status"], "action": result["action"],
                        "score": result["score"],
                        "evidence_coverage_pct": result["evidence_coverage_pct"],
                        "history_passed": result["history_passed"],
                        "coverage_passed": result["coverage_passed"],
                        "missing_features": result["missing_features"],
                        "rejected_features": result["rejected_features"],
                        "accepted_evidence_clusters": result["accepted_evidence_clusters"],
                    }
        snapshots.append({
            "decision_time": key, "as_of_session": session,
            "session_count": session_count, "input_contracts": snapshot.get("input_contracts", {}),
            "included_input_count": snapshot.get("included_input_count"),
            "excluded_input_count": snapshot.get("excluded_input_count"),
            "feature_series": symbols, "feature_adapter_policy": adapted["policy"],
            "status": "research_snapshot_built",
            "sector_membership_status": "verified_for_decision" if sector_reason is None else "withheld",
            "sector_membership_reason": sector_reason,
            "production_enabled": False,
        })

    return {
        "schema_version": "nepse-historical-feature-series-1.1.0",
        "status": "built_with_gaps" if withheld or any(s["sector_membership_status"] == "withheld" for s in snapshots) else "built",
        "snapshot_count": len(snapshots), "snapshots": snapshots,
        "withheld_decision_points": withheld, "strategy_count": len(STRATEGIES),
        "horizons": list(HORIZONS), "signals_generated": False,
        "trade_plans_generated": False, "performance_claimed": False,
        "production_enabled": False,
        "limitations": [
            "Feature snapshots are descriptive and inherit upstream source/session/price-basis gates.",
            "A nonempty trusted per-decision evidence manifest is required before any adapter or qualification runs.",
            "Static sector membership arguments are not reused historically; each decision needs an availability- and effective-date-valid membership snapshot.",
            "The current feature pipeline does not implement complete IDPAT hidden-level, accumulation/distribution, broker-persistence or fundamental scores.",
            "SMC remains experimental-only and is not promoted to weighted strategy evidence.",
            "Research qualification is not a trade signal; evidence-backed plans, execution and replay remain separate gates.",
        ],
    }
