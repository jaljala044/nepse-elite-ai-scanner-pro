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
from app.scoring_engine import score_feature_bundle
from app.relative_strength_features import relative_strength_universe
from app.idpat_price_volume_engine import idpat_price_volume_features


def build_feature_snapshot(records: list[dict], decision_time: str,
                           expected_symbols: list[str] | None = None,
                           sector_membership: dict | None = None,
                           expected_sector_members: dict | None = None,
                           session_dates: list[str] | None = None) -> dict:
    """Filter every input by availability before deriving any feature."""
    snapshot = build_as_of_snapshot(records, decision_time)
    rows = snapshot["records"]
    raw_prices = [r for r in rows if r.get("record_type") == "ohlcv"]
    raw_broker_rows = [r for r in rows if r.get("record_type") == "broker"]

    # Scoring requires canonical-session alignment and source/price-basis evidence.
    from datetime import date
    valid_calendar = False
    canonical_sessions = set()
    if isinstance(session_dates, list) and session_dates:
        try:
            normalized_calendar = [date.fromisoformat(str(item)).isoformat() for item in session_dates]
            valid_calendar = normalized_calendar == sorted(normalized_calendar) and len(normalized_calendar) == len(set(normalized_calendar))
            canonical_sessions = set(normalized_calendar) if valid_calendar else set()
        except (TypeError, ValueError):
            valid_calendar = False

    def valid_digest(value):
        digest = str(value or "").lower()
        return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)

    price_contract_failures = []
    price_contract_by_symbol = {}
    prices = []
    for index, row in enumerate(raw_prices):
        day = str(row.get("session_date", ""))
        admitted = (
            valid_calendar and day in canonical_sessions
            and row.get("source_validation_status") == "verified"
            and isinstance(row.get("source_id"), str) and bool(row["source_id"].strip())
            and valid_digest(row.get("source_payload_sha256"))
            and row.get("price_basis_status") in {"verified_unadjusted_no_actions", "verified_adjusted"}
            and row.get("corporate_action_status") in {"clear", "adjusted_verified"}
        )
        symbol = str(row.get("symbol", "")).strip().upper()
        contract = price_contract_by_symbol.setdefault(symbol, {"input_rows": 0, "admitted_rows": 0, "exclusions": []})
        contract["input_rows"] += 1
        if admitted:
            prices.append(row)
            contract["admitted_rows"] += 1
        else:
            failure = {"row_index": index, "symbol": row.get("symbol"),
                "session_date": row.get("session_date"), "reason": "session_provenance_or_price_basis_unverified"}
            price_contract_failures.append(failure)
            contract["exclusions"].append(failure)

    broker_contract_failures = []
    broker_contract_by_symbol = {}
    broker_rows = []
    for index, row in enumerate(raw_broker_rows):
        day = str(row.get("trade_date", ""))
        admitted = (
            valid_calendar and day in canonical_sessions
            and row.get("session_calendar_status") == "confirmed_open"
            and row.get("floorsheet_coverage_status") == "verified_complete"
            and row.get("source_validation_status") == "verified"
            and isinstance(row.get("source_id"), str) and bool(row["source_id"].strip())
            and valid_digest(row.get("source_payload_sha256"))
        )
        symbol = str(row.get("symbol", "")).strip().upper()
        contract = broker_contract_by_symbol.setdefault(symbol, {"input_rows": 0, "admitted_rows": 0, "exclusions": []})
        contract["input_rows"] += 1
        if admitted:
            broker_rows.append(row)
            contract["admitted_rows"] += 1
        else:
            failure = {"row_index": index, "symbol": row.get("symbol"),
                "trade_date": row.get("trade_date"), "reason": "session_or_complete_floorsheet_provenance_unverified"}
            broker_contract_failures.append(failure)
            contract["exclusions"].append(failure)

    # Sector mappings must be effective-dated at the exact as-of session.
    sector_membership_contract_ok = False
    sector_membership_contract_reason = "verified_effective_dated_sector_membership_missing"
    if valid_calendar and isinstance(sector_membership, dict) and isinstance(expected_sector_members, dict) and expected_sector_members:
        as_of_session = normalized_calendar[-1]
        required_members = [str(symbol).strip().upper()
                            for members in expected_sector_members.values() for symbol in members]
        sector_membership_contract_ok = bool(required_members)
        for member in required_members:
            record = sector_membership.get(member)
            if not isinstance(record, dict):
                sector_membership_contract_ok = False
                break
            try:
                effective_from = date.fromisoformat(str(record.get("effective_from"))).isoformat()
                effective_to_raw = record.get("effective_to")
                effective_to = date.fromisoformat(str(effective_to_raw)).isoformat() if effective_to_raw else None
            except (TypeError, ValueError):
                sector_membership_contract_ok = False
                break
            if not (
                record.get("status") == "verified"
                and record.get("as_of_status") == "verified"
                and effective_from <= as_of_session
                and (effective_to is None or as_of_session <= effective_to)
                and isinstance(record.get("source_id"), str) and bool(record["source_id"].strip())
                and valid_digest(record.get("source_payload_sha256"))
            ):
                sector_membership_contract_ok = False
                break
        if sector_membership_contract_ok:
            sector_membership_contract_reason = None

    for contract in price_contract_by_symbol.values():
        contract["score_eligible"] = contract["input_rows"] > 0 and contract["admitted_rows"] == contract["input_rows"]
    for contract in broker_contract_by_symbol.values():
        contract["score_eligible"] = contract["input_rows"] > 0 and contract["admitted_rows"] == contract["input_rows"]

    # Keep raw point-in-time prices for descriptive diagnostics; the contract
    # gate below independently controls whether each symbol's component score is admitted.
    prices = raw_prices

    input_contracts = {
        "canonical_session_calendar": "verified" if valid_calendar else "unavailable_or_invalid",
        "ohlcv": {"input_rows": len(raw_prices), "admitted_rows": len(raw_prices) - len(price_contract_failures),
                  "excluded_rows": len(price_contract_failures), "score_eligible": bool(raw_prices) and not price_contract_failures,
                  "exclusions": price_contract_failures, "symbols": price_contract_by_symbol},
        "broker_floorsheet": {"input_rows": len(raw_broker_rows), "admitted_rows": len(broker_rows),
                  "excluded_rows": len(broker_contract_failures), "score_eligible": bool(raw_broker_rows) and len(broker_rows) == len(raw_broker_rows),
                  "exclusions": broker_contract_failures, "symbols": broker_contract_by_symbol},
        "sector_membership": {"score_eligible": sector_membership_contract_ok,
                              "reason": sector_membership_contract_reason},
    }
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
    idpat_features_by_symbol = {\n        symbol: idpat_price_volume_features(items)\n        for symbol, items in sorted(by_symbol.items()) if symbol\n    }\n    broker_footprint = broker_footprint_features(broker_rows)
    if expected_symbols:
        expected_rs_symbols = [str(symbol).strip().upper() for symbol in expected_symbols]
        benchmark_rows = [
            row for row in rows
            if row.get("record_type") == "index_ohlcv"
            and str(row.get("index_code", "")).upper() == "NEPSE"
        ]
        relative_strength = relative_strength_universe(
            {symbol: by_symbol.get(symbol, []) for symbol in expected_rs_symbols},
            benchmark_rows,
            expected_symbols=expected_rs_symbols,
        )
    else:
        relative_strength = {
            "status": "insufficient_evidence",
            "reason": "expected_equity_universe_not_supplied",
            "eligible_symbols": 0,
            "expected_symbols": 0,
            "results": {},
        }
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
    component_candidates = {}
    component_feature_bundles = {}
    for symbol in sorted(by_symbol):
        if not symbol:
            continue
        rs_item = relative_strength.get("results", {}).get(symbol, {})
        broker_item = broker_footprint.get("security_features", {}).get(symbol, {}).get("1W", {})
        liquidity_item = liquidity_snapshot.get("symbols", {}).get(symbol, {})
        sector_code = (
            sector_membership.get(symbol, {}).get("sector_code")
            if isinstance(sector_membership, dict)
            and isinstance(sector_membership.get(symbol), dict)
            and sector_membership.get(symbol, {}).get("status") == "verified"
            else None
        )
        sector_item = sector_features.get("sectors", {}).get(sector_code, {}) if sector_code else {}

        # Preserve complete upstream evidence objects. The scoring adapter
        # accepts only status='observed' plus a numeric score; unavailable,
        # partial and experimental outputs remain missing.
        price_score_gate = input_contracts["ohlcv"]["symbols"].get(symbol, {}).get("score_eligible", False)
        broker_score_gate = input_contracts["broker_floorsheet"]["symbols"].get(symbol, {}).get("score_eligible", False)
        feature_bundle = {
            "wyckoff": ({**wyckoff_features[symbol], "status": "input_contract_unverified", "score": None}
                        if not price_score_gate else wyckoff_features[symbol]),
            "trend": ({**trend_features[symbol], "status": "input_contract_unverified", "score": None}
                      if not price_score_gate else trend_features[symbol]),
            "relative_strength": {
                "status": (rs_item.get("score_status", "insufficient_evidence")
                           if price_score_gate else "input_contract_unverified"),
                "score": rs_item.get("score") if price_score_gate else None,
                "as_of_session": rs_item.get("as_of_session"),
                "rank": rs_item.get("rank"),
            },
            "broker": ({**broker_item, "status": "floorsheet_coverage_unverified", "score": None}
                       if not broker_score_gate else broker_item),
            "volume": ({**volume_features[symbol], "status": "input_contract_unverified", "score": None}
                       if not price_score_gate else volume_features[symbol]),
            "liquidity": ({**liquidity_item, "status": "input_contract_unverified", "score": None}
                          if not price_score_gate else liquidity_item),
            "sector": {
                "status": (sector_item.get("score_status", "insufficient_evidence")
                           if input_contracts["ohlcv"]["score_eligible"] and sector_membership_contract_ok else "membership_validity_unverified"),
                "score": sector_item.get("score") if input_contracts["ohlcv"]["score_eligible"] and sector_membership_contract_ok else None,
                "sector_code": sector_code,
                "score_coverage_pct": sector_item.get("score_coverage_pct"),
            },
            "smc": {
                **smc_features_by_symbol[symbol],
                "status": "experimental_only",
                "score": None,
                "score_note": "uncalibrated directional heuristic is retained as descriptive evidence but excluded from weighted production scoring",
            },
        }
        component_feature_bundles[symbol] = feature_bundle
        component_candidates[symbol] = {
            name: (
                feature.get("score")
                if isinstance(feature, dict) and feature.get("status") == "observed"
                else None
            )
            for name, feature in feature_bundle.items()
        }

    aggregate_scores = {}
    for symbol, feature_bundle in component_feature_bundles.items():
        aggregate_scores[symbol] = score_feature_bundle(
            feature_bundle,
            stage1_quality="UNKNOWN",
            structure_confirmed=False,
            liquidity_ok=False,
            market_tradeable=False,
            reward_risk=None,
            hard_blocks=[
                "stage1_hard_gates_not_connected",
                "horizon_trade_plan_not_available",
                "market_regime_gate_not_connected",
            ],
        )
        aggregate_scores[symbol]["decision_status"] = "research_only_fail_closed_stage2_preview"

    latest_by_symbol = []
    for symbol, items in by_symbol.items():
        latest = sorted(items, key=lambda r: (r.get("session_date", ""), r.get("available_at", "")))[-1]
        latest_by_symbol.append(latest)
    return {
        "decision_time": snapshot["decision_time"],
        "input_contracts": input_contracts,
        "included_input_count": snapshot["included_count"],
        "excluded_input_count": snapshot["excluded_count"],
        "max_input_available_at": snapshot["max_input_available_at"],
        "point_in_time_eligible": snapshot["point_in_time_eligible"],
        "market_breadth": market_breadth(latest_by_symbol, expected_symbols),
        "security_features": security_features,
        "trend_features": trend_features,
        "volume_features": volume_features,
        "wyckoff_features": wyckoff_features,\n        "idpat_features": idpat_features_by_symbol,
        "smc_features": smc_features_by_symbol,
        "component_candidates": component_candidates,
        "component_feature_bundles": component_feature_bundles,
        "aggregate_scores": aggregate_scores,
        "relative_strength": relative_strength,
        "broker_participation": broker_participation_summary(raw_broker_rows),
        "broker_footprint": broker_footprint,
        "sector_strength": sector_features,
        "liquidity_tradability": liquidity_snapshot,
        "interpretation": "descriptive_only_not_a_trading_signal",
    }
