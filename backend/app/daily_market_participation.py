"""Descriptive daily participation from trusted, independently reviewed inputs."""
from datetime import date
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from .market_breadth_features import _utc, _digest


def daily_market_participation(rows, *, expected_symbols, universe, calendar,
                               decision_time, top_n=10, benchmark_rows=None):
    """No inferred trades, imputation or production recommendations."""
    cutoff = _utc(decision_time, "decision_time")
    base = {"status": "insufficient_evidence", "pressure": None,
            "sentiment": None, "rankings": None, "signals_enabled": False}
    if not isinstance(top_n, int) or isinstance(top_n, bool) or not 1 <= top_n <= 100:
        raise ValueError("invalid_top_n")
    if (not isinstance(expected_symbols, list) or not expected_symbols or
        any(not isinstance(s, str) or not s or s != s.strip().upper()
            for s in expected_symbols) or len(set(expected_symbols)) != len(expected_symbols)):
        raise ValueError("invalid_universe")
    def trusted(obj):
        return (isinstance(obj, dict) and obj.get("status") == "verified"
                and isinstance(obj.get("source_id"), str) and bool(obj["source_id"].strip())
                and _digest(obj.get("source_payload_sha256"))
                and _utc(obj.get("available_at"), "available_at") <= cutoff)
    if not trusted(universe) or not trusted(calendar):
        return dict(base, reason="unverified_universe_or_calendar")
    days = calendar.get("sessions", [])
    if (not isinstance(days, list) or len(days) < 2 or
        any(not isinstance(d, str) or date.fromisoformat(d).isoformat() != d for d in days)
        or sorted(set(days)) != days):
        raise ValueError("invalid_calendar")
    if days[-1] > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date().isoformat():
        return dict(base, reason="future_calendar")
    if universe.get("as_of_session") != days[-1] or universe.get("symbols") != sorted(expected_symbols):
        return dict(base, reason="universe_mismatch")
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("invalid_rows")
    def number(v):
        if isinstance(v, bool):
            raise ValueError("invalid_number")
        try:
            n = Decimal(str(v))
        except (InvalidOperation, ValueError):
            raise ValueError("invalid_number") from None
        if not n.is_finite() or n <= 0:
            raise ValueError("invalid_number")
        return n
    accepted = {}
    seen = set()
    expected = set(expected_symbols)
    for r in rows:
        s = r.get("symbol")
        if not isinstance(s, str) or s not in expected or r.get("session_date") != days[-1]:
            continue
        if s in seen:
            raise ValueError("duplicate_symbol")
        seen.add(s)
        if (r.get("source_validation_status") != "verified" or r.get("finality_status") != "final"
            or r.get("prior_session") != days[-2] or r.get("prior_close_verified") is not True
            or r.get("corporate_action_status") != "verified_clear"
            or not isinstance(r.get("source_id"), str) or not r["source_id"].strip()
            or not _digest(r.get("source_payload_sha256"))):
            continue
        if _utc(r.get("available_at"), "available_at") > cutoff:
            continue
        prior, close, volume, turnover = [number(r.get(k)) for k in
                                         ("prior_close", "close", "volume", "turnover")]
        if volume != volume.to_integral_value():
            raise ValueError("nonintegral_volume")
        accepted[s] = {"symbol": s, "return_pct": (close / prior - 1) * 100,
                       "volume": volume, "turnover": turnover}
    missing = sorted(expected - accepted.keys())
    base.update(as_of_session=days[-1], coverage=len(accepted)/len(expected),
                missing_symbols=missing)
    if missing:
        return dict(base, reason="incomplete_equity_coverage")
    values = list(accepted.values())
    adv = sum(v["return_pct"] > 0 for v in values)
    dec = sum(v["return_pct"] < 0 for v in values)
    def rank(key, reverse=True, predicate=lambda v: True):
        ordered = sorted((v for v in values if predicate(v)),
                         key=lambda v: (-v[key] if reverse else v[key], v["symbol"]))
        return [{"symbol": v["symbol"], "value": str(v[key])} for v in ordered[:top_n]]
    relative = None
    if benchmark_rows is not None:
        from .relative_strength_features import _close_series
        if not isinstance(benchmark_rows, list):
            raise ValueError("invalid_benchmark_rows")
        relevant = [r for r in benchmark_rows if isinstance(r, dict)
                    and r.get("session_date") in days[-2:]
                    and _utc(r.get("available_at"), "available_at") <= cutoff]
        series, excluded = _close_series(relevant, "benchmark", benchmark=True)
        if set(series) == set(days[-2:]) and not any(excluded.values()):
            index_return = (Decimal(str(series[days[-1]])) /
                            Decimal(str(series[days[-2]])) - 1) * 100
            for v in values:
                v["excess_return_pct"] = v["return_pct"] - index_return
            relative = {
                "benchmark": "NEPSE",
                "benchmark_return_pct": str(index_return),
                "leaders": rank("excess_return_pct", predicate=lambda v: v["excess_return_pct"] > 0),
                "laggards": rank("excess_return_pct", False, lambda v: v["excess_return_pct"] < 0),
            }
    return dict(base, benchmark_relative=relative, status="research_only", pressure=(adv-dec)/len(values),
                sentiment="positive" if adv > dec else "negative" if dec > adv else "balanced",
                counts={"advance": adv, "decline": dec, "unchanged": len(values)-adv-dec},
                rankings={"gainers": rank("return_pct", predicate=lambda v: v["return_pct"] > 0),
                          "losers": rank("return_pct", False, lambda v: v["return_pct"] < 0),
                          "volume": rank("volume"), "turnover": rank("turnover")},
                interpretation="breadth_direction_only_not_investor_intent")
