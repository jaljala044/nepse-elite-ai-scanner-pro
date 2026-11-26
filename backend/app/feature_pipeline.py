"""Point-in-time gated bridge from raw observations to descriptive features."""
from __future__ import annotations

from app.point_in_time import build_as_of_snapshot
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary, broker_footprint_features
from app.trend_features import minervini_trend_template
from app.volume_vsa_features import volume_vsa_features
from app.wyckoff_features import wyckoff_event_features
from app.smc_features import smc_features
from app.sector_strength_features import sector_strength_features
from app.liquidity_features import liquidity_tradability_features
from app.relative_strength_features import relative_strength_universe
from app.scoring_engine import score_scan


def build_feature_snapshot(records: list[dict], decision_time: str,
                           expected_symbols: list[str] | None = None,
                           sector_membership: dict | None = None,
                           expected_sector_members: dict | None = None,
                           session_dates: list[str] | None = None) -> dict:
    """Filter every input by availability before deriving any feature."""
    snapshot = build_as_of_snapshot(records, decision_time)
    rows = snapshot["records"]
    prices = [r for r in rows if r.get("record_type") == "ohlcv"]
    broker_rows = [r for r in rows if r.get("record_type") == "broker"]
    by_symbol = {}
    for row in prices:
        by_symbol.setdefault(str(row.get("symbol", "")).upper(), []).append(row)
    security_features = {
        symbol: security_footprint(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    trend_features = {}
    for symbol, items in sorted(by_symbol.items()):
        if not symbol:
            continue
        required_ohlc = ("session_date", "close", "high", "low")
        missing_rows = [
            index for index, item in enumerate(items)
            if any(key not in item or item[key] is None for key in required_ohlc)
        ]
        if missing_rows:
            trend_features[symbol] = {
                "status": "insufficient_evidence",
                "reason": "required_ohlc_fields_missing",
                "missing_row_count": len(missing_rows),
                "history_sessions": len(items),
                "score": None,
                "checks": {},
            }
        else:
            trend_features[symbol] = minervini_trend_template(items)
    volume_features = {
        symbol: volume_vsa_features(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    wyckoff_features = {
        symbol: wyckoff_event_features(items)
        for symbol, items in sorted(by_symbol.items()) if symbol
    }
    smc_features_by_symbol = {}
    for symbol, items in sorted(by_symbol.items()):
        if not symbol:
            continue
        required_smc_ohlc = ("session_date", "open", "high", "low", "close")
        missing_smc_rows = [index for index, item in enumerate(items)
                            if any(key not in item or item[key] is None for key in required_smc_ohlc)]
        if missing_smc_rows:
            smc_features_by_symbol[symbol] = {
                "status": "insufficient_evidence",
                "reason": "required_ohlc_fields_missing",
                "missing_row_count": len(missing_smc_rows),
                "history_sessions": len(items),
                "timeframes": {}, "fvg": [], "liquidity_sweeps": [], "score": None,
            }
        else:
            smc_features_by_symbol[symbol] = smc_features(items)
    broker_footprint = broker_footprint_features(broker_rows)
    if sector_membership is not None and expected_sector_members is not None and session_dates is not None:
        sector_features = sector_strength_features(
            prices, sector_membership=sector_membership,
            expected_sector_members=expected_sector_members,
            session_dates=session_dates,
        )
    else:
        sector_features = {
            "status": "insufficient_evidence",
            "reason": "verified_sector_membership_and_calendar_not_supplied",
            "sectors": {},
        }
    if expected_symbols is not None and session_dates is not None:
        liquidity_snapshot = liquidity_tradability_features(
            prices, expected_symbols=expected_symbols, session_dates=session_dates,
        )
    else:
        liquidity_snapshot = {
            "status": "insufficient_evidence",
            "reason": "expected_universe_and_canonical_calendar_not_supplied",
            "symbols": {},
        }
    index_candidates = [row for row in rows
                         if row.get("record_type") == "index_ohlcv"
                         and str(row.get("index_code", "")).upper() == "NEPSE"]
    benchmark_rows = []
    withheld_index_rows = 0
    for row in index_candidates:
        digest = str(row.get("source_payload_sha256", "")).lower()
        provenance_ok = (
            isinstance(row.get("source_id"), str) and bool(row["source_id"].strip())
            and len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)
        )
        if (row.get("source_validation_status") == "verified"
                and row.get("finality_status") == "final" and provenance_ok):
            benchmark_rows.append({"session_date": row.get("session_date"),
                                   "close": row.get("close")})
        else:
            withheld_index_rows += 1
    rs_securities = {}
    rs_excluded = {}
    for symbol, items in sorted(by_symbol.items()):
        if not symbol:
            continue
        if any(item.get("session_date") is None or item.get("close") is None for item in items):
            rs_excluded[symbol] = "missing_stock_session_or_close"
        else:
            rs_securities[symbol] = [{"session_date": item["session_date"],
                                      "close": item["close"]} for item in items]
    if benchmark_rows and rs_securities:
        relative_strength = relative_strength_universe(rs_securities, benchmark_rows)
        relative_strength["withheld_unverified_or_provisional_index_rows"] = withheld_index_rows
        relative_strength["benchmark_contract"] = "index_ohlcv:NEPSE:verified:final:source_id+sha256"
    else:
        relative_strength = {
            "status": "insufficient_evidence",
            "reason": "no_verified_final_nepse_index_rows" if not benchmark_rows else "no_eligible_stock_close_series",
            "benchmark_candidate_rows": len(index_candidates),
            "verified_final_benchmark_rows": len(benchmark_rows),
            "withheld_unverified_or_provisional_index_rows": withheld_index_rows,
            "eligible_symbols": 0, "excluded_symbols": rs_excluded, "results": {},
        }
    component_candidates = {}
    for symbol in sorted(by_symbol):
        if not symbol:
            continue
        component_candidates[symbol] = {
            "wyckoff": wyckoff_features[symbol].get("score") if wyckoff_features[symbol].get("status") == "observed" else None,
            "trend": trend_features[symbol].get("score") if trend_features[symbol].get("status") == "observed" else None,
            "relative_strength": (relative_strength.get("results", {}).get(symbol, {}).get("score")
                                  if relative_strength.get("status") == "observed" else None),
            "broker": (broker_footprint.get("security_features", {}).get(symbol, {}).get("1D", {}).get("score")
                       if broker_footprint.get("security_features", {}).get(symbol, {}).get("1D", {}).get("status") == "observed" else None),
            "volume": volume_features[symbol].get("score") if volume_features[symbol].get("status") == "observed" else None,
            "liquidity": (
                liquidity_snapshot.get("symbols", {}).get(symbol, {}).get("score")
                if liquidity_snapshot.get("status") == "observed"
                and liquidity_snapshot.get("symbols", {}).get(symbol, {}).get("score_status") == "observed"
                else None
            ),
            "sector": (
                sector_features.get("sectors", {}).get(
                    sector_membership.get(symbol, {}).get("sector_code"), {}
                ).get("score")
                if isinstance(sector_membership, dict)
                and sector_membership.get(symbol, {}).get("status") == "verified"
                and sector_features.get("status") == "observed" else None
            ),
            "smc": smc_features_by_symbol[symbol].get("score") if smc_features_by_symbol[symbol].get("status") == "observed" else None,
        }
    aggregate_scores = {}
    for symbol, components in component_candidates.items():
        aggregate_scores[symbol] = score_scan(
            components,
            stage1_quality="UNKNOWN",
            structure_confirmed=False,
            liquidity_ok=False,
            market_tradeable=False,
            reward_risk=None,
            hard_blocks=[
                "stage1_hard_gates_not_connected",
                "horizon_trade_plan_not_available",
            ],
        )
        aggregate_scores[symbol]["decision_status"] = "research_only_fail_closed_stage2_preview"

    latest_by_symbol = []
    for symbol, items in by_symbol.items():
        latest = sorted(items, key=lambda r: (r.get("session_date", ""), r.get("available_at", "")))[-1]
        latest_by_symbol.append(latest)
    return {
        "decision_time": snapshot["decision_time"],
        "included_input_count": snapshot["included_count"],
        "excluded_input_count": snapshot["excluded_count"],
        "max_input_available_at": snapshot["max_input_available_at"],
        "point_in_time_eligible": snapshot["point_in_time_eligible"],
        "market_breadth": market_breadth(latest_by_symbol, expected_symbols),
        "security_features": security_features,
        "trend_features": trend_features,
        "volume_features": volume_features,
        "wyckoff_features": wyckoff_features,
        "smc_features": smc_features_by_symbol,
        "component_candidates": component_candidates,
        "aggregate_scores": aggregate_scores,
        "broker_participation": broker_participation_summary(broker_rows),
        "broker_footprint": broker_footprint,
        "sector_strength": sector_features,
        "liquidity_tradability": liquidity_snapshot,
        "relative_strength": relative_strength,
        "interpretation": "descriptive_only_not_a_trading_signal",
    }
