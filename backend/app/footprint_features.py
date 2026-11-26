"""Transparent, coverage-aware footprint feature primitives.

These functions calculate descriptive statistics only. They do not infer intent
or issue buy/sell signals. Inputs must already be point-in-time filtered.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date
import math


def market_breadth(rows: list[dict], expected_symbols: list[str] | None = None) -> dict:
    latest = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol and row.get("close") is not None and row.get("previous_close") is not None:
            latest[symbol] = row
    unexpected_symbols = []
    normalized_expected = None
    if expected_symbols is not None:
        normalized_expected = [str(symbol).strip().upper() for symbol in expected_symbols]
        if any(not symbol for symbol in normalized_expected):
            raise ValueError("expected_symbols cannot contain blank values")
        if len(normalized_expected) != len(set(normalized_expected)):
            raise ValueError("expected_symbols must be unique")
        expected_set = set(normalized_expected)
        unexpected_symbols = sorted(set(latest) - expected_set)
        observed_rows = {symbol: row for symbol, row in latest.items() if symbol in expected_set}
    else:
        observed_rows = latest
    advancing = declining = unchanged = 0
    for symbol, row in observed_rows.items():
        try:
            close, previous = float(row["close"]), float(row["previous_close"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{symbol}: close and previous_close must be numeric") from exc
        if not math.isfinite(close) or not math.isfinite(previous) or close <= 0 or previous <= 0:
            raise ValueError(f"{symbol}: close and previous_close must be finite and positive")
        if close > previous:
            advancing += 1
        elif close < previous:
            declining += 1
        else:
            unchanged += 1
    if normalized_expected is not None:
        eligible = len(normalized_expected)
    else:
        eligible = len(latest)
    observed = len(observed_rows)
    return {
        "advancing": advancing, "declining": declining, "unchanged": unchanged,
        "observed_symbols": observed, "eligible_symbols": eligible,
        "unexpected_symbol_count": len(unexpected_symbols),
        "unexpected_symbols": unexpected_symbols,
        "coverage_ratio": observed / eligible if eligible else None,
        "advance_decline_ratio": advancing / declining if declining else None,
        "status": "insufficient_coverage" if not eligible or observed < eligible else "observed",
    }


def security_footprint(rows: list[dict], minimum_history: int = 5) -> dict:
    if not isinstance(minimum_history, int) or minimum_history < 1:
        raise ValueError("minimum_history must be a positive integer")
    ordered = sorted(rows, key=lambda r: r["session_date"])
    if not ordered:
        return {"status": "insufficient_evidence", "reason": "no_rows"}
    session_dates = []
    for index, row in enumerate(ordered):
        try:
            session_dates.append(date.fromisoformat(str(row["session_date"])).isoformat())
            close_value = float(row["close"])
            volume_value = float(row["volume"])
            previous_value = float(row["previous_close"]) if row.get("previous_close") is not None else None
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"security footprint row {index}: invalid date or numeric field") from exc
        if (not math.isfinite(close_value) or close_value <= 0
                or not math.isfinite(volume_value) or volume_value < 0
                or (previous_value is not None and (not math.isfinite(previous_value) or previous_value <= 0))):
            raise ValueError(f"security footprint row {index}: prices must be finite positive and volume finite non-negative")
    if len(session_dates) != len(set(session_dates)):
        raise ValueError("security footprint contains duplicate session dates")
    current = ordered[-1]
    close = float(current["close"])
    previous = float(current["previous_close"]) if current.get("previous_close") is not None else None
    volume = float(current["volume"])
    historical_volumes = [float(r["volume"]) for r in ordered[:-1][-minimum_history:]]
    baseline = sum(historical_volumes) / len(historical_volumes) if historical_volumes else None
    return {
        "status": "observed" if previous and baseline is not None and len(historical_volumes) >= minimum_history else "insufficient_evidence",
        "session_date": current["session_date"],
        "close": close,
        "return_pct": ((close / previous) - 1) * 100 if previous else None,
        "volume": volume,
        "prior_volume_mean": baseline,
        "volume_ratio": volume / baseline if baseline and baseline > 0 else None,
        "history_sessions": len(historical_volumes),
        "interpretation": "descriptive_price_volume_observation_only",
    }


def broker_participation_summary(rows: list[dict]) -> dict:
    """Summarize verified broker flow with exact decimal amounts and explicit unknowns."""
    mapped = []
    unresolved = []
    buy = Decimal("0")
    sell = Decimal("0")
    for index, row in enumerate(rows):
        status = row.get("identity_status")
        broker_id = row.get("broker_entity_id")
        if status == "verified":
            if not broker_id:
                raise ValueError(f"row {index}: verified identity requires broker_entity_id")
            mapped.append(row)
        else:
            if broker_id is not None:
                raise ValueError(f"row {index}: unresolved identity cannot carry broker_entity_id")
            if status not in {"unmapped", "ambiguous", "rejected"}:
                raise ValueError(f"row {index}: unsupported identity_status")
            unresolved.append(row)
        if row.get("side") not in {"buy", "sell"}:
            raise ValueError(f"row {index}: side must be buy or sell")
        try:
            amount = Decimal(str(row.get("amount")))
        except (InvalidOperation, TypeError):
            raise ValueError(f"row {index}: amount must be a decimal")
        if not amount.is_finite() or amount < 0:
            raise ValueError(f"row {index}: amount must be finite and non-negative")
        if status == "verified":
            if row["side"] == "buy":
                buy += amount
            else:
                sell += amount
    total = buy + sell
    return {
        "verified_broker_rows": len(mapped),
        "unmapped_or_unverified_rows": len(unresolved),
        "unverified_row_share": len(unresolved) / len(rows) if rows else None,
        "verified_buy_amount": str(buy),
        "verified_sell_amount": str(sell),
        "verified_net_amount": str(buy - sell),
        "verified_amount_total": str(total),
        "status": "insufficient_evidence" if not mapped else "partial_identity_coverage" if unresolved else "observed",
    }


BROKER_WINDOWS = {
    "1D": 1, "1W": 5, "1M": 21, "3M": 63,
    "6M": 126, "1Y": 252, "2Y": 504,
}


def broker_footprint_features(rows: list[dict], *, minimum_amount_coverage: float = 0.80,
                              minimum_sessions: int = 5,
                              session_dates: list[str] | None = None) -> dict:
    """Build point-in-time broker footprint windows from normalized party rows.

    Required input grain is one buyer/seller party observation per contract,
    carrying trade_date, symbol, side, amount, quantity, identity_status,
    broker_entity_id and source_broker_code. Only verified canonical entities
    enter ranked broker tables. Unresolved observations remain in coverage
    denominators and are never merged by code/name guesses.
    """
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    if not isinstance(minimum_sessions, int) or isinstance(minimum_sessions, bool) or minimum_sessions < 1:
        raise ValueError("minimum_sessions must be a positive integer")
    if isinstance(minimum_amount_coverage, bool) or not isinstance(minimum_amount_coverage, (int, float)) or not 0 <= minimum_amount_coverage <= 1:
        raise ValueError("minimum_amount_coverage must be between 0 and 1")

    normalized = []
    required = ("trade_date", "symbol", "side", "amount", "quantity",
                "identity_status", "broker_entity_id", "source_broker_code")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or any(key not in row for key in required):
            return {"status": "insufficient_evidence", "reason": "broker_party_schema_missing",
                    "input_rows": len(rows), "security_features": {}, "market_windows": {},
                    "score": None}
        try:
            day = date.fromisoformat(str(row["trade_date"])).isoformat()
            amount = Decimal(str(row["amount"]))
            quantity = Decimal(str(row["quantity"]))
        except (TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"broker row {index}: invalid date, amount or quantity") from exc
        if not amount.is_finite() or amount < 0 or not quantity.is_finite() or quantity < 0:
            raise ValueError(f"broker row {index}: amount and quantity must be finite and non-negative")
        if row["side"] not in {"buy", "sell"}:
            raise ValueError(f"broker row {index}: side must be buy or sell")
        status = row["identity_status"]
        broker_id = row["broker_entity_id"]
        if status == "verified":
            if not isinstance(broker_id, str) or not broker_id.strip():
                raise ValueError(f"broker row {index}: verified identity requires broker_entity_id")
        elif status in {"unmapped", "ambiguous", "rejected"}:
            if broker_id is not None:
                raise ValueError(f"broker row {index}: unresolved identity cannot carry broker_entity_id")
        else:
            raise ValueError(f"broker row {index}: unsupported identity_status")
        symbol = str(row["symbol"]).strip().upper()
        if not symbol:
            raise ValueError(f"broker row {index}: symbol is required")
        source_code = row["source_broker_code"]
        if source_code is not None and (not isinstance(source_code, str) or not source_code.strip()):
            raise ValueError(f"broker row {index}: source_broker_code must be nonblank when supplied")
        normalized.append({**row, "trade_date": day, "symbol": symbol,
                           "_amount": amount, "_quantity": quantity})

    if not normalized:
        return {"status": "insufficient_evidence", "reason": "no_broker_party_rows",
                "input_rows": 0, "security_features": {}, "market_windows": {}, "score": None}

    all_dates = sorted({row["trade_date"] for row in normalized})
    if session_dates is None:
        calendar_dates = all_dates
    else:
        try:
            calendar_dates = [date.fromisoformat(str(item)).isoformat() for item in session_dates]
        except (TypeError, ValueError) as exc:
            raise ValueError("session_dates must contain ISO YYYY-MM-DD dates") from exc
        if calendar_dates != sorted(set(calendar_dates)):
            raise ValueError("session_dates must be sorted and unique")
        if not set(all_dates).issubset(set(calendar_dates)):
            raise ValueError("broker observations fall outside the verified complete-session list")

    def summarize(group_rows, window_name, session_count, expected_dates):
        gross_all = sum((r["_amount"] for r in group_rows), Decimal("0"))
        gross_verified = sum((r["_amount"] for r in group_rows if r["identity_status"] == "verified"), Decimal("0"))
        verified_buy = sum((r["_amount"] for r in group_rows if r["identity_status"] == "verified" and r["side"] == "buy"), Decimal("0"))
        verified_sell = sum((r["_amount"] for r in group_rows if r["identity_status"] == "verified" and r["side"] == "sell"), Decimal("0"))
        verified_qty = sum((r["_quantity"] for r in group_rows if r["identity_status"] == "verified"), Decimal("0"))
        all_qty = sum((r["_quantity"] for r in group_rows), Decimal("0"))
        amount_coverage = gross_verified / gross_all if gross_all else None
        observation_coverage = (sum(r["identity_status"] == "verified" for r in group_rows) / len(group_rows)) if group_rows else None
        broker_totals = {}
        for row in group_rows:
            if row["identity_status"] != "verified":
                continue
            broker = broker_totals.setdefault(row["broker_entity_id"], {
                "buy_amount": Decimal("0"), "sell_amount": Decimal("0"),
                "buy_quantity": Decimal("0"), "sell_quantity": Decimal("0"),
                "contract_party_count": 0,
            })
            broker[row["side"] + "_amount"] += row["_amount"]
            broker[row["side"] + "_quantity"] += row["_quantity"]
            broker["contract_party_count"] += 1
        gross_by_broker = {key: value["buy_amount"] + value["sell_amount"] for key, value in broker_totals.items()}
        ranked = []
        for broker_id, values in broker_totals.items():
            gross = gross_by_broker[broker_id]
            net = values["buy_amount"] - values["sell_amount"]
            share = gross / gross_verified if gross_verified else Decimal("0")
            ranked.append({
                "broker_entity_id": broker_id,
                "buy_amount": str(values["buy_amount"]),
                "sell_amount": str(values["sell_amount"]),
                "net_amount": str(net),
                "buy_quantity": str(values["buy_quantity"]),
                "sell_quantity": str(values["sell_quantity"]),
                "net_quantity": str(values["buy_quantity"] - values["sell_quantity"]),
                "gross_participation_pct": round(float(share * 100), 4) if gross_verified else None,
                "party_observation_count": values["contract_party_count"],
                "flow_class": "net_buyer" if net > 0 else "net_seller" if net < 0 else "balanced",
            })
        ranked.sort(key=lambda x: (Decimal(x["net_amount"]), x["broker_entity_id"]), reverse=True)
        top3_amount = sum((gross_by_broker[key] for key in sorted(gross_by_broker,
                         key=lambda k: gross_by_broker[k], reverse=True)[:3]), Decimal("0"))
        concentration = top3_amount / gross_verified if gross_verified else None
        net = verified_buy - verified_sell
        net_buyer_count = sum(1 for value in broker_totals.values()
                              if value["buy_amount"] > value["sell_amount"])
        net_seller_count = sum(1 for value in broker_totals.values()
                               if value["sell_amount"] > value["buy_amount"])
        directional_ratio = ((net_buyer_count - net_seller_count) / len(broker_totals)
                             if broker_totals else None)
        enough = (len({r["trade_date"] for r in group_rows}) >= min(session_count, minimum_sessions)
                  and amount_coverage is not None and float(amount_coverage) >= minimum_amount_coverage
                  and gross_verified > 0)
        # Directional breadth score is deliberately withheld if broker identity
        # coverage is inadequate. Net traded value itself is zero-sum across
        # matched buyer/seller party observations, so score uses broker breadth,
        # not aggregate net amount. It is not calibrated or a probability.
        score = max(0, min(100, round(50 + float(directional_ratio) * 100, 2))) if enough else None
        return {
            "window": window_name, "window_sessions": session_count,
            "expected_covered_sessions": len(expected_dates),
            "observed_sessions": len({r["trade_date"] for r in group_rows}),
            "window_complete": len(expected_dates) == session_count,
            "party_observation_count": len(group_rows),
            "verified_party_observation_count": sum(r["identity_status"] == "verified" for r in group_rows),
            "unresolved_party_observation_count": sum(r["identity_status"] != "verified" for r in group_rows),
            "gross_amount_all_identities": str(gross_all),
            "gross_amount_verified": str(gross_verified),
            "verified_buy_amount": str(verified_buy), "verified_sell_amount": str(verified_sell),
            "verified_net_amount": str(net),
            "verified_amount_coverage_pct": round(float(amount_coverage * 100), 4) if amount_coverage is not None else None,
            "verified_observation_coverage_pct": round(observation_coverage * 100, 4) if observation_coverage is not None else None,
            "verified_quantity_coverage_pct": round(float(verified_qty / all_qty * 100), 4) if all_qty else None,
            "top3_gross_concentration_pct": round(float(concentration * 100), 4) if concentration is not None else None,
            "top_net_buyers": [x for x in ranked if Decimal(x["net_amount"]) > 0][:10],
            "top_net_sellers": sorted([x for x in ranked if Decimal(x["net_amount"]) < 0],
                                      key=lambda x: Decimal(x["net_amount"]))[:10],
            "broker_positions": ranked,
            "broker_count": len(ranked), "net_buyer_count": net_buyer_count,
            "net_seller_count": net_seller_count, "broker_breadth_balance": directional_ratio,
            "score": score,
            "status": "observed" if enough else "insufficient_identity_coverage_or_history",
            "score_note": "uncalibrated net-buyer versus net-seller broker breadth balance; not a probability or standalone signal",
        }

    def windows_for(group_rows):
        output = {}
        for name, count in BROKER_WINDOWS.items():
            cutoff_index = max(0, len(calendar_dates) - count)
            expected_dates = calendar_dates[cutoff_index:]
            selected_dates = set(expected_dates)
            selected = [r for r in group_rows if r["trade_date"] in selected_dates]
            output[name] = summarize(selected, name, count, expected_dates)
        # Persistence labels require genuinely complete 1W/1M/3M windows;
        # partial histories are never promoted to multi-month accumulation.
        persistence_windows = ("1W", "1M", "3M")
        by_broker = {}
        for name in persistence_windows:
            window = output[name]
            if window["status"] != "observed" or not window["window_complete"]:
                continue
            for position in window["broker_positions"]:
                by_broker.setdefault(position["broker_entity_id"], {})[name] = position["flow_class"]
        persistent = []
        for broker_id, states in by_broker.items():
            buyers = sum(states.get(name) == "net_buyer" for name in persistence_windows)
            sellers = sum(states.get(name) == "net_seller" for name in persistence_windows)
            if len(states) < 2:
                label = "insufficient_history"
            elif buyers == 3 and sellers == 0:
                label = "strong_accumulation"
            elif buyers >= 2 and sellers <= 1:
                label = "moderate_accumulation"
            elif sellers == 3 and buyers == 0:
                label = "heavy_distribution"
            elif sellers >= 2 and buyers <= 1:
                label = "moderate_distribution"
            elif buyers and sellers:
                label = "mixed"
            else:
                label = "neutral"
            persistent.append({"broker_entity_id": broker_id, "classification": label,
                               "observed_complete_windows": sorted(states),
                               "net_buyer_windows": buyers, "net_seller_windows": sellers})
        output["persistent_broker_flow"] = sorted(
            persistent, key=lambda x: (x["classification"], x["broker_entity_id"])
        )
        return output

    security_features = {}
    for symbol in sorted({r["symbol"] for r in normalized}):
        group = [r for r in normalized if r["symbol"] == symbol]
        security_features[symbol] = windows_for(group)
    market_windows = windows_for(normalized)
    latest_market = market_windows["1D"]
    overall_score = latest_market["score"]
    return {
        "status": "observed" if any(v["1D"]["status"] == "observed" for v in security_features.values()) else "insufficient_evidence",
        "as_of_trade_date": calendar_dates[-1],
        "input_party_observation_count": len(normalized),
        "observed_session_count": len(all_dates),
        "covered_session_count": len(calendar_dates),
        "identity_coverage_policy": {
            "minimum_verified_amount_coverage_pct": minimum_amount_coverage * 100,
            "minimum_sessions": minimum_sessions,
            "unresolved_rows_retained_in_denominators": True,
            "unresolved_codes_not_ranked_as_canonical_brokers": True,
        },
        "market_windows": market_windows,
        "security_features": security_features,
        "score": overall_score,
        "score_note": "market-level 1D verified net-buyer breadth balance; uncalibrated and not a probability",
    }
