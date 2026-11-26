"""Confluence layer for NEPSE sector price rotation and broker transaction mix.

This joins two descriptive evidence streams. It does not infer beneficial
ownership, operator intent, manipulation, or a trade signal. Broker source
lineage remains explicitly incomplete until the upstream broker contract
exports immutable source IDs and payload hashes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def _timestamp(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return result.astimezone(timezone.utc)


def _amount(value, field):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"invalid_{field}")
    return result


def _signed(value, field):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if not result.is_finite():
        raise ValueError(f"invalid_{field}")
    return result


def build_sector_intelligence_confluence(
    market_rotation: dict,
    broker_rotation: dict,
    *,
    decision_time: str,
    minimum_broker_count: int = 1,
) -> dict:
    """Join verified market rotation with descriptive broker-sector activity.

    Requires both upstream outputs to refer to the same NEPSE session date and
    to be available by decision_time. Broker flow is aggregated from reported
    amounts; no inference is made about broker identity, beneficial ownership,
    accumulation/distribution, or intent.
    """
    cutoff = _timestamp(decision_time, "decision_time")
    if isinstance(minimum_broker_count, bool) or not isinstance(minimum_broker_count, int) or minimum_broker_count < 1:
        raise ValueError("minimum_broker_count_must_be_positive")
    if not isinstance(market_rotation, dict) or not isinstance(broker_rotation, dict):
        raise ValueError("rotation_inputs_must_be_objects")

    market_as_of = market_rotation.get("as_of_session")
    broker_as_of = broker_rotation.get("as_of_date")
    if market_rotation.get("status") != "observed":
        return {
            "status": "insufficient_evidence", "reason": "market_rotation_not_observed",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }
    if broker_rotation.get("status") != "descriptive_only":
        return {
            "status": "insufficient_evidence", "reason": "broker_rotation_not_descriptive_only",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }
    if not isinstance(market_as_of, str) or market_as_of != broker_as_of:
        return {
            "status": "insufficient_evidence", "reason": "market_broker_as_of_session_mismatch",
            "market_as_of_session": market_as_of, "broker_as_of_date": broker_as_of,
            "sectors": {}, "signals_enabled": False,
        }

    try:
        broker_available = _timestamp(broker_rotation.get("as_of_timestamp"), "broker_as_of_timestamp")
    except ValueError:
        return {
            "status": "insufficient_evidence", "reason": "broker_timestamp_missing_or_invalid",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }
    if broker_available > cutoff:
        return {
            "status": "insufficient_evidence", "reason": "broker_data_not_available_by_decision_time",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }

    prior_sessions = broker_rotation.get("prior_complete_sessions")
    current_sessions = broker_rotation.get("current_complete_sessions")
    if not isinstance(prior_sessions, list) or not isinstance(current_sessions, list):
        return {
            "status": "insufficient_evidence", "reason": "broker_complete_session_coverage_missing",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }
    if not current_sessions or current_sessions[-1] != market_as_of:
        return {
            "status": "insufficient_evidence", "reason": "broker_window_does_not_end_on_market_session",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }
    for group in (prior_sessions, current_sessions):
        if any(not isinstance(day, str) for day in group) or group != sorted(set(group)):
            raise ValueError("broker_complete_sessions_must_be_unique_ascending_iso_dates")

    broker_rows = broker_rotation.get("brokers")
    if not isinstance(broker_rows, list) or len(broker_rows) < minimum_broker_count:
        return {
            "status": "insufficient_evidence", "reason": "broker_count_below_minimum",
            "broker_count": len(broker_rows) if isinstance(broker_rows, list) else 0,
            "sectors": {}, "signals_enabled": False,
        }

    market_sectors = market_rotation.get("sectors")
    if not isinstance(market_sectors, dict) or not market_sectors:
        return {
            "status": "insufficient_evidence", "reason": "market_sector_results_missing",
            "as_of_session": market_as_of, "sectors": {}, "signals_enabled": False,
        }

    flow = {}
    broker_seen = set()
    for broker in broker_rows:
        if not isinstance(broker, dict):
            raise ValueError("broker_row_must_be_an_object")
        broker_id = broker.get("broker_id")
        if not isinstance(broker_id, str) or not broker_id.strip() or broker_id in broker_seen:
            raise ValueError("broker_ids_must_be_nonempty_and_unique")
        broker_seen.add(broker_id)
        sectors = broker.get("sectors")
        if not isinstance(sectors, list):
            raise ValueError("broker_sector_rows_required")
        for item in sectors:
            if not isinstance(item, dict) or not isinstance(item.get("sector"), str):
                raise ValueError("invalid_broker_sector_row")
            sector = item["sector"]
            bucket = flow.setdefault(sector, {
                "prior_buy": Decimal(0), "prior_sell": Decimal(0),
                "current_buy": Decimal(0), "current_sell": Decimal(0),
                "broker_count": 0, "brokers": [],
            })
            pb = _amount(item.get("prior_buy_amount"), "prior_buy_amount")
            ps = _amount(item.get("prior_sell_amount"), "prior_sell_amount")
            cb = _amount(item.get("current_buy_amount"), "current_buy_amount")
            cs = _amount(item.get("current_sell_amount"), "current_sell_amount")
            bucket["prior_buy"] += pb
            bucket["prior_sell"] += ps
            bucket["current_buy"] += cb
            bucket["current_sell"] += cs
            bucket["broker_count"] += 1
            bucket["brokers"].append({
                "broker_id": broker_id,
                "prior_net_amount": str(pb - ps),
                "current_net_amount": str(cb - cs),
                "current_gross_amount": str(cb + cs),
            })

    total_prior_gross = sum((v["prior_buy"] + v["prior_sell"] for v in flow.values()), Decimal(0))
    total_current_gross = sum((v["current_buy"] + v["current_sell"] for v in flow.values()), Decimal(0))
    results = {}
    for sector, market in market_sectors.items():
        if not isinstance(market, dict):
            raise ValueError("invalid_market_sector_result")
        windows = market.get("windows", {})
        one_week = windows.get("1W", {})
        one_month = windows.get("1M", {})
        three_month = windows.get("3M", {})
        excess_1w = one_week.get("median_excess_return_pct")
        excess_1m = one_month.get("median_excess_return_pct")
        excess_3m = three_month.get("median_excess_return_pct")
        broker = flow.get(sector)
        if broker is None or broker["broker_count"] < minimum_broker_count:
            results[sector] = {
                "market_classification": market.get("classification", "insufficient_evidence"),
                "market_weighted_excess_return_pct": market.get("weighted_excess_return_pct"),
                "broker_status": "insufficient_evidence",
                "confluence": "market_only_broker_evidence_insufficient",
                "broker_count": 0, "broker_flow": None,
            }
            continue
        prior_buy, prior_sell = broker["prior_buy"], broker["prior_sell"]
        current_buy, current_sell = broker["current_buy"], broker["current_sell"]
        prior_gross = prior_buy + prior_sell
        current_gross = current_buy + current_sell
        prior_net = prior_buy - prior_sell
        current_net = current_buy - current_sell
        prior_share = prior_gross / total_prior_gross if total_prior_gross else None
        current_share = current_gross / total_current_gross if total_current_gross else None
        share_change = current_share - prior_share if prior_share is not None and current_share is not None else None

        if market.get("score_status") != "observed" or excess_1w is None or excess_1m is None or excess_3m is None:
            confluence = "market_evidence_insufficient"
        elif current_gross == 0:
            confluence = "broker_activity_absent"
        elif Decimal(str(excess_1m)) > 0 and current_net > 0 and share_change is not None and share_change > 0:
            confluence = "price_strength_and_broker_participation_broadening"
        elif Decimal(str(excess_1m)) > 0 and current_net > 0:
            confluence = "price_strength_with_net_broker_buying"
        elif Decimal(str(excess_1m)) > 0 and current_net < 0:
            confluence = "price_strength_with_net_broker_selling_divergence"
        elif Decimal(str(excess_1m)) < 0 and current_net > 0:
            confluence = "broker_net_buying_against_weak_price_trend"
        elif Decimal(str(excess_1m)) < 0 and current_net < 0:
            confluence = "price_weakness_and_net_broker_selling"
        else:
            confluence = "mixed_price_and_broker_flow"

        results[sector] = {
            "market_classification": market.get("classification", "unclassified"),
            "market_weighted_excess_return_pct": market.get("weighted_excess_return_pct"),
            "market_excess_return_pct": {"1W": excess_1w, "1M": excess_1m, "3M": excess_3m},
            "broker_status": "observed_descriptive",
            "confluence": confluence,
            "broker_count": broker["broker_count"],
            "broker_flow": {
                "prior_buy_amount": str(prior_buy), "prior_sell_amount": str(prior_sell),
                "prior_net_amount": str(prior_net), "prior_gross_amount": str(prior_gross),
                "current_buy_amount": str(current_buy), "current_sell_amount": str(current_sell),
                "current_net_amount": str(current_net), "current_gross_amount": str(current_gross),
                "prior_sector_activity_share": str(prior_share) if prior_share is not None else None,
                "current_sector_activity_share": str(current_share) if current_share is not None else None,
                "activity_share_change": str(share_change) if share_change is not None else None,
                "broker_contributors": sorted(broker["brokers"], key=lambda x: Decimal(x["current_gross_amount"]), reverse=True),
            },
        }

    provenance_complete = bool(broker_rotation.get("source_ids")) and bool(broker_rotation.get("source_payload_hashes"))
    return {
        "status": "observed_descriptive",
        "mode": "confluence_only_no_trade_signal",
        "as_of_session": market_as_of,
        "decision_time": cutoff.isoformat(),
        "broker_data_available_at": broker_available.isoformat(),
        "market_source_ids": market_rotation.get("source_ids", {}),
        "broker_provenance_complete": provenance_complete,
        "broker_provenance_status": "complete" if provenance_complete else "not_exposed_by_upstream_broker_contract",
        "broker_count": len(broker_seen),
        "prior_sessions": prior_sessions,
        "current_sessions": current_sessions,
        "sectors": results,
        "signals_enabled": False,
        "production_score": None,
        "probability": None,
        "action": "NOT_EVALUATED",
        "limitations": [
            "Broker amounts are transaction-side turnover summaries, not proof of beneficial ownership or intent.",
            "Upstream broker rotation currently does not expose immutable source IDs and payload hashes; broker provenance is therefore incomplete.",
            "A positive net amount is descriptive broker-side buying, not verified accumulation.",
            "Market/broker confluence is not a BUY/SELL signal or forecast.",
        ],
    }
