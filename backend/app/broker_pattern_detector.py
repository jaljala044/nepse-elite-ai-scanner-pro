"""Point-in-time broker accumulation/distribution candidate detector.

Research-only descriptive output. Broker codes/entities are execution-channel
observations, not beneficial-owner identities or evidence of intent.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

_HASH = re.compile(r"^[0-9a-f]{64}$")
_PATTERNS = {
    "accumulation": "EARLY_ACCUMULATION_CANDIDATE",
    "distribution": "EARLY_DISTRIBUTION_CANDIDATE",
}


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _money(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a decimal") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return result


def _insufficient(symbol: str, decision_at: str, as_of_session: str | None,
                  methodology_version: str, missing: list[str],
                  evidence_ids: list[str] | None = None) -> dict:
    return {
        "symbol": symbol,
        "decision_at": decision_at,
        "as_of_session": as_of_session,
        "methodology_version": methodology_version,
        "status": "INSUFFICIENT_EVIDENCE",
        "pattern": None,
        "features": {},
        "coverage": {},
        "missing_features": sorted(set(missing)),
        "evidence_ids": sorted(set(evidence_ids or [])),
        "contradictions": [],
        "invalidation_conditions": [],
        "calibration_status": "UNCALIBRATED",
        "trading_action": "NONE",
        "production_eligible": False,
    }


def detect_broker_patterns(
    symbol: str,
    broker_rows: list[dict],
    price_rows: list[dict],
    market_context: list[dict],
    *,
    expected_sessions: list[str],
    complete_broker_sessions: list[str],
    decision_at: str,
    methodology_version: str = "p4.34.1",
    minimum_identity_coverage: float = 0.80,
    minimum_persistent_sessions: int = 3,
) -> dict:
    """Detect descriptive candidates from admitted, point-in-time evidence.

    Required price rows include session_date, available_at, close, high, low,
    volume, turnover, source_validation_status, source_id,
    source_payload_sha256, price_basis_status and corporate_action_status.
    Market context rows include session_date, available_at, validation status,
    market_return_pct, sector_return_pct, source_id and payload hash.
    Broker rows are one buy/sell party per contract and include trade_date,
    available_at, symbol, side, amount, quantity, identity_status,
    broker_entity_id, source_broker_code, contract_id, source_id,
    source_payload_sha256 and source_row_number.

    Session inventory is supplied independently; absent sessions are unknown,
    never interpreted as zero flow.
    """
    symbol = str(symbol).strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    cutoff = _timestamp(decision_at, "decision_at")
    if not isinstance(expected_sessions, list) or not expected_sessions:
        raise ValueError("expected_sessions must be a non-empty ordered list")
    sessions = [date.fromisoformat(str(item)).isoformat() for item in expected_sessions]
    if sessions != sorted(set(sessions)):
        raise ValueError("expected_sessions must be unique and ascending")
    if date.fromisoformat(sessions[-1]) > cutoff.date():
        raise ValueError("expected_sessions cannot contain a future session")
    if not isinstance(minimum_identity_coverage, (int, float)) or isinstance(minimum_identity_coverage, bool) or not 0 < minimum_identity_coverage <= 1:
        raise ValueError("minimum_identity_coverage must be in (0, 1]")
    if not isinstance(minimum_persistent_sessions, int) or isinstance(minimum_persistent_sessions, bool) or minimum_persistent_sessions < 2:
        raise ValueError("minimum_persistent_sessions must be at least 2")
    if len(sessions) < 5:
        return _insufficient(symbol, decision_at, sessions[-1], methodology_version,
                             ["five_session_window"])

    window = sessions[-5:]
    complete = set(str(x) for x in complete_broker_sessions)
    if not set(window) <= complete:
        return _insufficient(symbol, decision_at, window[-1], methodology_version,
                             ["complete_broker_session_inventory"])

    def asof_rows(rows: list[dict], field: str) -> list[dict]:
        if not isinstance(rows, list):
            raise ValueError(f"{field} must be a list")
        admitted = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{field} rows must be objects")
            available = _timestamp(row.get("available_at"), f"{field}.available_at")
            if available <= cutoff:
                admitted.append(row)
        return admitted

    prices_in = asof_rows(price_rows, "price")
    context_in = asof_rows(market_context, "market_context")
    brokers_in = asof_rows(broker_rows, "broker")
    prices = {}
    context = {}
    evidence_ids = set()

    for row in prices_in:
        if str(row.get("symbol", "")).strip().upper() != symbol:
            continue
        day = date.fromisoformat(str(row.get("session_date"))).isoformat()
        if day not in window:
            continue
        if row.get("source_validation_status") != "verified":
            continue
        if row.get("price_basis_status") not in {"verified_unadjusted_no_actions", "verified_adjusted"}:
            continue
        if row.get("corporate_action_status") not in {"clear", "adjusted_verified"}:
            continue
        digest = str(row.get("source_payload_sha256", "")).lower()
        source_id = row.get("source_id")
        if not _HASH.fullmatch(digest) or not isinstance(source_id, str) or not source_id.strip():
            continue
        values = {key: _money(row.get(key), f"price.{key}") for key in ("close", "high", "low", "volume", "turnover")}
        if values["close"] <= 0 or values["high"] < max(values["close"], values["low"]) or values["low"] <= 0:
            continue
        if day in prices:
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["duplicate_price_session"], sorted(evidence_ids))
        prices[day] = {**values, "source_id": source_id, "hash": digest}
        evidence_ids.add(source_id)

    for row in context_in:
        day = date.fromisoformat(str(row.get("session_date"))).isoformat()
        if day not in window:
            continue
        if row.get("validation_status") != "verified":
            continue
        source_id = row.get("source_id")
        digest = str(row.get("source_payload_sha256", "")).lower()
        if not isinstance(source_id, str) or not source_id.strip() or not _HASH.fullmatch(digest):
            continue
        if day in context:
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["duplicate_market_context_session"], sorted(evidence_ids))
        market_return = Decimal(str(row.get("market_return_pct")))
        sector_return = Decimal(str(row.get("sector_return_pct")))
        if not market_return.is_finite() or not sector_return.is_finite():
            continue
        context[day] = {"market_return_pct": market_return,
                        "sector_return_pct": sector_return, "source_id": source_id}
        evidence_ids.add(source_id)

    if set(prices) != set(window) or set(context) != set(window):
        missing = []
        if set(prices) != set(window):
            missing.append("verified_price_volume_window")
        if set(context) != set(window):
            missing.append("verified_market_sector_context")
        return _insufficient(symbol, decision_at, window[-1], methodology_version,
                             missing, sorted(evidence_ids))

    broker_by_day = defaultdict(lambda: defaultdict(lambda: {"buy": Decimal("0"), "sell": Decimal("0")}))
    gross_all = Decimal("0")
    gross_verified = Decimal("0")
    seen_party_rows = set()
    seen_contract_sides = set()
    broker_row_count = 0
    for row in brokers_in:
        if str(row.get("symbol", "")).strip().upper() != symbol:
            continue
        day = date.fromisoformat(str(row.get("trade_date"))).isoformat()
        if day not in window:
            continue
        required_text = ("contract_id", "source_id", "source_row_number")
        if any(row.get(key) in (None, "") for key in required_text):
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["broker_lineage"], sorted(evidence_ids))
        digest = str(row.get("source_payload_sha256", "")).lower()
        if not _HASH.fullmatch(digest):
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["broker_payload_hash"], sorted(evidence_ids))
        try:
            row_number = int(row["source_row_number"])
            amount = _money(row.get("amount"), "broker.amount")
            _money(row.get("quantity"), "broker.quantity")
        except (ValueError, TypeError):
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["valid_broker_values"], sorted(evidence_ids))
        if row_number < 1 or str(row_number) != str(row["source_row_number"]):
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["broker_source_row_number"], sorted(evidence_ids))
        side = row.get("side")
        if side not in {"buy", "sell"}:
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["broker_side"], sorted(evidence_ids))
        lineage = (row["source_id"], digest, row_number, side)
        contract_side = (day, str(row["contract_id"]), side)
        if lineage in seen_party_rows or contract_side in seen_contract_sides:
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["duplicate_or_conflicting_broker_party"], sorted(evidence_ids))
        seen_party_rows.add(lineage)
        seen_contract_sides.add(contract_side)
        status = row.get("identity_status")
        broker_id = row.get("broker_entity_id")
        gross_all += amount
        if status == "verified" and isinstance(broker_id, str) and broker_id.strip():
            gross_verified += amount
            broker_by_day[day][broker_id][side] += amount
        elif status in {"unmapped", "ambiguous", "rejected"} and broker_id is None:
            pass
        else:
            return _insufficient(symbol, decision_at, window[-1], methodology_version,
                                 ["broker_identity"], sorted(evidence_ids))
        evidence_ids.add(row["source_id"])
        broker_row_count += 1

    if not broker_row_count or gross_all <= 0:
        return _insufficient(symbol, decision_at, window[-1], methodology_version,
                             ["broker_party_observations"], sorted(evidence_ids))
    identity_coverage = gross_verified / gross_all
    if identity_coverage < Decimal(str(minimum_identity_coverage)):
        return _insufficient(symbol, decision_at, window[-1], methodology_version,
                             ["broker_identity_amount_coverage"], sorted(evidence_ids))

    daily = []
    for day in window:
        totals = broker_by_day[day]
        buyers = sum(1 for values in totals.values() if values["buy"] > values["sell"])
        sellers = sum(1 for values in totals.values() if values["sell"] > values["buy"])
        active = len(totals)
        breadth = (buyers - sellers) / active if active else 0.0
        daily.append({"session": day, "net_buyer_count": buyers,
                      "net_seller_count": sellers, "active_brokers": active,
                      "broker_breadth": breadth})
    positive_sessions = sum(item["broker_breadth"] > 0 for item in daily)
    negative_sessions = sum(item["broker_breadth"] < 0 for item in daily)
    prior_breadth = sum(item["broker_breadth"] for item in daily[:2]) / 2
    recent_breadth = sum(item["broker_breadth"] for item in daily[-3:]) / 3
    flow_acceleration = recent_breadth - prior_breadth

    closes = [prices[day]["close"] for day in window]
    highs = [prices[day]["high"] for day in window]
    lows = [prices[day]["low"] for day in window]
    volumes = [prices[day]["volume"] for day in window]
    turnovers = [prices[day]["turnover"] for day in window]
    price_return = (closes[-1] / closes[0] - 1) * Decimal("100")
    range_pct = (max(highs) / min(lows) - 1) * Decimal("100")
    volume_baseline = sum(volumes[:2]) / 2
    volume_recent = sum(volumes[-3:]) / 3
    turnover_baseline = sum(turnovers[:2]) / 2
    turnover_recent = sum(turnovers[-3:]) / 3
    volume_ratio = volume_recent / volume_baseline if volume_baseline > 0 else None
    turnover_ratio = turnover_recent / turnover_baseline if turnover_baseline > 0 else None
    market_return = sum((context[day]["market_return_pct"] for day in window), Decimal("0"))
    sector_return = sum((context[day]["sector_return_pct"] for day in window), Decimal("0"))
    relative_market = price_return - market_return
    relative_sector = price_return - sector_return

    contradictions = []
    if market_return < Decimal("-2") or sector_return < Decimal("-2"):
        contradictions.append("market_or_sector_context_deteriorating")
    if volume_ratio is None or volume_ratio < Decimal("0.8"):
        contradictions.append("volume_confirmation_weak")
    if turnover_ratio is None or turnover_ratio < Decimal("0.8"):
        contradictions.append("turnover_confirmation_weak")
    if range_pct > Decimal("12"):
        contradictions.append("wide_volatile_range")

    accumulation = (
        positive_sessions >= minimum_persistent_sessions
        and flow_acceleration > 0
        and price_return <= Decimal("3")
        and range_pct <= Decimal("12")
        and volume_ratio is not None and volume_ratio >= Decimal("0.8")
        and turnover_ratio is not None and turnover_ratio >= Decimal("0.8")
        and not contradictions
    )
    distribution = (
        negative_sessions >= minimum_persistent_sessions
        and flow_acceleration < 0
        and price_return < Decimal("-2")
        and range_pct <= Decimal("15")
        and volume_ratio is not None and volume_ratio >= Decimal("0.8")
        and turnover_ratio is not None and turnover_ratio >= Decimal("0.8")
        and not contradictions
    )

    pattern = _PATTERNS["accumulation"] if accumulation else _PATTERNS["distribution"] if distribution else None
    return {
        "symbol": symbol,
        "decision_at": decision_at,
        "as_of_session": window[-1],
        "methodology_version": methodology_version,
        "status": "CANDIDATE" if pattern else "NO_CANDIDATE",
        "pattern": pattern,
        "features": {
            "daily_broker_breadth": daily,
            "positive_flow_sessions": positive_sessions,
            "negative_flow_sessions": negative_sessions,
            "flow_acceleration_breadth": float(flow_acceleration),
            "price_return_5s_pct": float(price_return),
            "relative_market_return_5s_pct": float(relative_market),
            "relative_sector_return_5s_pct": float(relative_sector),
            "range_5s_pct": float(range_pct),
            "volume_recent_vs_prior_ratio": float(volume_ratio) if volume_ratio is not None else None,
            "turnover_recent_vs_prior_ratio": float(turnover_ratio) if turnover_ratio is not None else None,
        },
        "coverage": {
            "expected_sessions": window,
            "price_sessions": len(prices),
            "market_context_sessions": len(context),
            "complete_broker_sessions": len(set(window) & complete),
            "broker_party_observations": broker_row_count,
            "verified_amount": str(gross_verified),
            "gross_amount": str(gross_all),
            "identity_amount_coverage": float(identity_coverage),
            "minimum_identity_coverage": minimum_identity_coverage,
        },
        "missing_features": [],
        "evidence_ids": sorted(evidence_ids),
        "contradictions": contradictions,
        "invalidation_conditions": [
            "subsequent verified sessions reverse broker-flow persistence",
            "price closes below a separately validated demand structure",
            "market or sector context deteriorates materially",
            "source completeness, identity mapping, or corporate-action basis is revoked",
        ],
        "calibration_status": "UNCALIBRATED",
        "trading_action": "NONE",
        "production_eligible": False,
        "interpretation": "descriptive_execution_channel_pattern_not_beneficial_ownership",
    }
