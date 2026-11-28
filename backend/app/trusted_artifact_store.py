"""Server-side, allowlisted artifact loader for Part 2 intelligence snapshots.

The registry is deployment-controlled configuration, never request data. A
registry entry pins an immutable payload path and SHA-256 digest. This module
does not fetch external websites or treat uploaded CSVs as trusted sources.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from .market_intelligence_snapshot import REQUIRED_MODULES


class TrustedArtifactError(ValueError):
    """Raised when a deployment-pinned artifact cannot be safely admitted."""


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _safe_payload_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise TrustedArtifactError("payload_path_missing")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or "\\" in relative:
        raise TrustedArtifactError("payload_path_unsafe")
    root_resolved = root.resolve()
    path = (root_resolved / relative).resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise TrustedArtifactError("payload_path_escapes_store")
    return path


def _validate_daily_participation(data, expected_symbols):
    """Validate descriptive payload structure; source truth remains upstream."""
    from decimal import Decimal, InvalidOperation
    def numeric(value):
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise TrustedArtifactError("daily_participation_invalid_number")
        try:
            n = Decimal(str(value))
        except InvalidOperation:
            raise TrustedArtifactError("daily_participation_invalid_number") from None
        if not n.is_finite():
            raise TrustedArtifactError("daily_participation_invalid_number")
        return n
    if (not isinstance(expected_symbols, list) or not expected_symbols
            or any(not isinstance(s, str) or not s or s != s.strip().upper() for s in expected_symbols)
            or len(set(expected_symbols)) != len(expected_symbols)):
        raise TrustedArtifactError("daily_participation_universe_invalid")
    counts = data.get("counts")
    keys = {"advance", "decline", "unchanged"}
    if (not isinstance(counts, dict) or set(counts) != keys
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != len(expected_symbols)
            or data.get("missing_symbols") != []):
        raise TrustedArtifactError("daily_participation_counts_invalid")
    a, d = counts["advance"], counts["decline"]
    sentiment = "positive" if a > d else "negative" if a < d else "balanced"
    if (data.get("sentiment") != sentiment
            or abs(numeric(data.get("pressure")) - Decimal(a-d)/len(expected_symbols)) > Decimal("0.000000000001")):
        raise TrustedArtifactError("daily_participation_pressure_invalid")
    def ranking(rows, descending, sign, maximum, integral=False):
        if not isinstance(rows, list) or len(rows) > min(maximum, 100):
            raise TrustedArtifactError("daily_participation_ranking_invalid")
        seen, order = set(), []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"symbol", "value"}:
                raise TrustedArtifactError("daily_participation_ranking_invalid")
            symbol = row["symbol"]
            if not isinstance(symbol, str) or symbol not in expected_symbols or symbol in seen:
                raise TrustedArtifactError("daily_participation_ranking_symbol_invalid")
            seen.add(symbol)
            v = numeric(row["value"])
            if v * sign <= 0 or (integral and v != v.to_integral_value()):
                raise TrustedArtifactError("daily_participation_ranking_value_invalid")
            order.append((-v if descending else v, symbol))
        if order != sorted(order):
            raise TrustedArtifactError("daily_participation_ranking_order_invalid")
        return seen
    ranks = data.get("rankings")
    if not isinstance(ranks, dict) or set(ranks) != {"gainers", "losers", "volume", "turnover"}:
        raise TrustedArtifactError("daily_participation_rankings_invalid")
    gain = ranking(ranks["gainers"], True, 1, a)
    loss = ranking(ranks["losers"], False, -1, d)
    if gain & loss:
        raise TrustedArtifactError("daily_participation_conflicting_direction")
    ranking(ranks["volume"], True, 1, len(expected_symbols), True)
    ranking(ranks["turnover"], True, 1, len(expected_symbols))
    relative = data.get("benchmark_relative")
    if relative is not None:
        if not isinstance(relative, dict) or relative.get("benchmark") != "NEPSE":
            raise TrustedArtifactError("daily_participation_benchmark_invalid")
        numeric(relative.get("benchmark_return_pct"))
        leaders = ranking(relative.get("leaders"), True, 1, len(expected_symbols))
        laggards = ranking(relative.get("laggards"), False, -1, len(expected_symbols))
        if leaders & laggards:
            raise TrustedArtifactError("daily_participation_conflicting_benchmark_direction")


def _validate_rotation(data, expected_indices):
    from math import isfinite
    indices = data["indices"]
    if (not isinstance(expected_indices, list) or not expected_indices
            or any(not isinstance(k, str) or not k.strip() for k in expected_indices)
            or len(set(expected_indices)) != len(expected_indices)
            or set(indices) != set(expected_indices)):
        raise TrustedArtifactError("rotation_universe_mismatch")
    common_dates = None
    for item in indices.values():
        trail = item.get("rotation_trail") if isinstance(item, dict) else None
        if not isinstance(trail, list) or len(trail) != 6:
            raise TrustedArtifactError("rotation_trail_invalid")
        dates = []
        for point in trail:
            if not isinstance(point, dict):
                raise TrustedArtifactError("rotation_point_invalid")
            day = point.get("date")
            if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
                raise TrustedArtifactError("rotation_date_invalid")
            x, y = point.get("relative_return_pct"), point.get("momentum_change_pp")
            if any(type(v) not in (int, float) or not isfinite(v) for v in (x, y)):
                raise TrustedArtifactError("rotation_coordinate_invalid")
            quadrant = "leading" if x >= 0 and y >= 0 else "weakening" if x >= 0 else "improving" if y >= 0 else "lagging"
            if point.get("quadrant") != quadrant:
                raise TrustedArtifactError("rotation_quadrant_invalid")
            dates.append(day)
        if dates != sorted(set(dates)) or dates[-1] != data["as_of"]:
            raise TrustedArtifactError("rotation_dates_misaligned")
        if common_dates is not None and dates != common_dates:
            raise TrustedArtifactError("rotation_dates_misaligned")
        common_dates = dates


def _validate_sector_constituents(data, expected_members, as_of):
    from math import isfinite
    from statistics import median
    sectors = data.get("sectors")
    if (data.get("status") != "observed" or data.get("as_of_session") != as_of
            or data.get("signals_enabled") is not False
            or not isinstance(sectors, dict) or not isinstance(expected_members, dict)
            or not expected_members or set(sectors) != set(expected_members)):
        raise TrustedArtifactError("sector_payload_invalid")
    all_members = set()
    for sector, item in sectors.items():
        members = expected_members[sector]
        if (not isinstance(members, list) or not members
                or any(not isinstance(s, str) or not s or s != s.strip().upper() for s in members)
                or len(set(members)) != len(members) or all_members.intersection(members)):
            raise TrustedArtifactError("sector_universe_invalid")
        all_members.update(members)
        windows = item.get("windows") if isinstance(item, dict) else None
        if not isinstance(windows, dict) or set(windows) != {"1W", "1M", "3M", "6M"}:
            raise TrustedArtifactError("sector_windows_invalid")
        for window in windows.values():
            if not isinstance(window, dict) or window.get("end_session") != as_of:
                raise TrustedArtifactError("sector_window_invalid")
            rows = window.get("constituents")
            if window.get("status") == "insufficient_evidence":
                if rows is not None:
                    raise TrustedArtifactError("sector_unverified_constituents")
                continue
            if window.get("status") != "observed" or not isinstance(rows, list) or not rows:
                raise TrustedArtifactError("sector_constituents_invalid")
            seen, order, returns, excess = set(), [], [], []
            benchmark = window.get("nepse_return_pct")
            if type(benchmark) not in (int, float) or not isfinite(benchmark):
                raise TrustedArtifactError("sector_benchmark_invalid")
            for row in rows:
                if not isinstance(row, dict):
                    raise TrustedArtifactError("sector_constituents_invalid")
                symbol, r, e = row.get("symbol"), row.get("return_pct"), row.get("excess_return_pct")
                if not isinstance(symbol, str) or symbol not in members or symbol in seen:
                    raise TrustedArtifactError("sector_constituent_identity_invalid")
                if any(type(v) not in (int, float) or not isfinite(v) for v in (r, e)):
                    raise TrustedArtifactError("sector_constituent_return_invalid")
                if abs(r-benchmark-e) > 0.00016:
                    raise TrustedArtifactError("sector_constituent_excess_invalid")
                seen.add(symbol)
                returns.append(r)
                excess.append(e)
                order.append((-e, symbol))
            if order != sorted(order):
                raise TrustedArtifactError("sector_constituent_order_invalid")
            if (window.get("observed_members") != len(seen) or window.get("expected_members") != len(members)
                    or window.get("missing_members") != sorted(set(members)-seen)):
                raise TrustedArtifactError("sector_constituent_coverage_invalid")
            for key, value, tolerance in (("coverage_pct",100*len(seen)/len(members),0.00501),
                    ("median_return_pct",median(returns),0.00011),("median_excess_return_pct",median(excess),0.00011)):
                actual = window.get(key)
                if type(actual) not in (int,float) or not isfinite(actual) or abs(actual-value)>tolerance:
                    raise TrustedArtifactError("sector_constituent_aggregate_invalid")


class TrustedArtifactStore:
    """Load only artifacts pinned by server-owned registry configuration.

    registry schema:
      {module: {source_id, payload_path, payload_sha256, evidence_ids,
                as_of_date, available_at, status, coverage_ratio,
                finality_status, source_validation_status}}

    The registry must come from deployment configuration with write access
    restricted to the ingestion/approval service. Hashes supplied by API
    clients are never consulted.
    """

    def __init__(self, root: str | Path, registry: Mapping[str, Any], *,
                 max_age_days: int = 7) -> None:
        self.root = Path(root)
        self.registry = registry
        if isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 0:
            raise ValueError("max_age_days_must_be_nonnegative_integer")
        self.max_age_days = max_age_days

    def load(self, *, decision_date: str, decision_time: str,
             required_modules: tuple[str, ...] = REQUIRED_MODULES) -> dict[str, dict]:
        try:
            cutoff_date = date.fromisoformat(decision_date)
        except (TypeError, ValueError):
            raise TrustedArtifactError("decision_date_must_be_iso_date") from None
        cutoff = _timestamp(decision_time, "decision_time")
        if cutoff.astimezone(ZoneInfo('Asia/Kathmandu')).date() < cutoff_date:
            raise TrustedArtifactError("decision_time_precedes_decision_date")
        if not isinstance(self.registry, Mapping):
            raise TrustedArtifactError("server_registry_invalid")

        output: dict[str, dict] = {}
        for module in required_modules:
            entry = self.registry.get(module)
            if not isinstance(entry, Mapping):
                continue
            try:
                source_id = entry.get("source_id")
                if not isinstance(source_id, str) or not source_id.strip():
                    raise TrustedArtifactError("source_id_missing")
                evidence_ids = entry.get("evidence_ids")
                if (not isinstance(evidence_ids, list) or not evidence_ids
                        or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
                        or len(evidence_ids) != len(set(evidence_ids))):
                    raise TrustedArtifactError("evidence_ids_missing_or_duplicate")

                as_of = date.fromisoformat(str(entry.get("as_of_date")))
                if as_of > cutoff_date:
                    raise TrustedArtifactError("artifact_as_of_after_decision_date")
                if cutoff_date - as_of > timedelta(days=self.max_age_days):
                    raise TrustedArtifactError("artifact_stale")

                available_at = _timestamp(entry.get("available_at"), "available_at")
                if available_at > cutoff:
                    raise TrustedArtifactError("artifact_available_after_decision_time")
                payload_path = _safe_payload_path(self.root, entry.get("payload_path"))
                raw = payload_path.read_bytes()
                expected_hash = entry.get("payload_sha256")
                actual_hash = sha256(raw).hexdigest()
                if (not isinstance(expected_hash, str) or len(expected_hash) != 64
                        or actual_hash != expected_hash.lower()):
                    raise TrustedArtifactError("payload_sha256_mismatch")

                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise TrustedArtifactError("payload_must_be_json_object")
                if entry.get("source_validation_status") != "verified":
                    raise TrustedArtifactError("source_not_verified")
                if entry.get("finality_status") != "final":
                    raise TrustedArtifactError("source_finality_not_verified")
                coverage = entry.get("coverage_ratio")
                if (isinstance(coverage, bool) or not isinstance(coverage, (int, float))
                        or not 0 < coverage <= 1):
                    raise TrustedArtifactError("coverage_ratio_invalid")
                status = entry.get("status")
                if status not in {"observed", "research_only", "descriptive_only"}:
                    raise TrustedArtifactError("artifact_status_not_admissible")

                calendar_id = entry.get("session_calendar_id")
                if not isinstance(calendar_id, str) or not calendar_id.strip():
                    raise TrustedArtifactError("session_calendar_id_missing")
                context = {"session_calendar_id": calendar_id}
                price_modules = {
                    "market_health", "index_intelligence", "sector_rotation",
                    "relative_strength", "wyckoff", "market_structure", "daily_market_participation",
                }
                if module in price_modules:
                    action_status = entry.get("corporate_action_status")
                    if action_status not in {"verified", "confirmed_none"}:
                        raise TrustedArtifactError("corporate_action_status_unverified")
                    context["corporate_action_status"] = action_status
                if module == "daily_market_participation":
                    if (coverage != 1 or data.get("status") != "research_only"
                            or data.get("coverage") != 1
                            or data.get("as_of_session") != as_of.isoformat()
                            or data.get("signals_enabled") is not False
                            or not isinstance(data.get("rankings"), dict)):
                        raise TrustedArtifactError("daily_participation_not_complete")
                    if entry.get("equity_universe_status") != "verified":
                        raise TrustedArtifactError("equity_universe_unverified")
                    _validate_daily_participation(data, entry.get("expected_symbols"))
                if module == "index_rotation":
                    if (coverage != 1 or data.get("status") != "research_only"
                            or data.get("as_of") != as_of.isoformat()
                            or data.get("coverage_ratio") != 1
                            or data.get("missing_indices") != []
                            or data.get("benchmark") != "NEPSE"
                            or data.get("signals_enabled") is not False
                            or data.get("trade_actions_enabled") is not False
                            or not isinstance(data.get("indices"), dict)
                            or "NEPSE" not in data["indices"]):
                        raise TrustedArtifactError("index_rotation_not_complete")
                    _validate_rotation(data, entry.get("expected_indices"))
                if module in {"sector_rotation", "broker_sector_rotation"}:
                    membership_status = entry.get("sector_membership_status")
                    membership_version = entry.get("sector_membership_version")
                    if membership_status != "verified" or not isinstance(membership_version, str) or not membership_version.strip():
                        raise TrustedArtifactError("sector_membership_version_unverified")
                    context["sector_membership_status"] = membership_status
                    context["sector_membership_version"] = membership_version
                    if module == "sector_rotation":
                        _validate_sector_constituents(data, entry.get("expected_sector_members"), as_of.isoformat())
                if module in {"broker_profiles", "broker_sector_rotation"}:
                    broker_status = entry.get("broker_code_mapping_status")
                    broker_coverage = entry.get("broker_identity_coverage_ratio")
                    if broker_status != "verified":
                        raise TrustedArtifactError("broker_code_mapping_unverified")
                    if (isinstance(broker_coverage, bool)
                            or not isinstance(broker_coverage, (int, float))
                            or not 0 < broker_coverage <= 1):
                        raise TrustedArtifactError("broker_identity_coverage_invalid")
                    context["broker_code_mapping_status"] = broker_status
                    context["broker_identity_coverage_ratio"] = float(broker_coverage)

                output[module] = {
                    "status": status,
                    "as_of_date": as_of.isoformat(),
                    "available_at": available_at.isoformat(),
                    "session_calendar_id": calendar_id,
                    "quality_context": context,
                    "source_ids": [source_id],
                    "evidence_ids": list(evidence_ids),
                    "coverage_ratio": float(coverage),
                    "source_validation_status": "verified",
                    "finality_status": "final",
                    "evidence_gate_passed": True,
                    "data": data,
                }
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                # Preserve explicit failure reasons without admitting partial data.
                reason = str(exc) or "artifact_unavailable"
                output[module] = {"status": "unavailable", "rejection_reason": reason}
        return output


def build_trusted_market_snapshot(store: TrustedArtifactStore, *,
                                  decision_date: str, decision_time: str) -> dict:
    """Load pinned server-side artifacts and pass only admitted envelopes onward."""
    from .market_intelligence_snapshot import build_market_intelligence_snapshot

    modules = REQUIRED_MODULES + ("daily_market_participation", "index_rotation")
    artifacts = store.load(decision_date=decision_date, decision_time=decision_time, required_modules=modules)
    return build_market_intelligence_snapshot(
        artifacts, decision_date=decision_date, decision_time=decision_time, required_modules=modules
    )
