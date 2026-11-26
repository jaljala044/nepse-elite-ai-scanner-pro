"""Research-only broker/SMC confluence on reconciled, as-of evidence."""
from datetime import date
from decimal import Decimal, InvalidOperation
from .footprint_features import broker_footprint_features

def broker_smc_confluence(symbol, structure, party_rows, *, as_of, verified_sessions,
                          reconciled_sessions, eligible=False, mode="swing"):
    base = {"status":"unavailable","action":"NO TRADE","production_score":None,
            "symbol":symbol,"mode":mode}
    if mode not in ("swing","positional"):
        raise ValueError("unsupported mode")
    if not eligible or not verified_sessions or not reconciled_sessions:
        return dict(base,reason="evidence_gate")
    cutoff = date.fromisoformat(str(as_of))
    calendar = [date.fromisoformat(str(d)) for d in verified_sessions]
    if calendar != sorted(set(calendar)):
        raise ValueError("calendar must be unique and ascending")
    calendar = [d for d in calendar if d <= cutoff]
    n = 5 if mode == "swing" else 21
    if len(calendar) < n or calendar[-1] != cutoff:
        return dict(base,reason="calendar_window_incomplete")
    required = {str(d) for d in calendar[-n:]}
    if not required <= {str(d) for d in reconciled_sessions}:
        return dict(base,reason="unreconciled_sessions")
    if structure.get("status") != "research_only" or structure.get("as_of") != str(cutoff):
        return dict(base,reason="structure_cutoff_mismatch")
    rows = [r for r in party_rows if r.get("symbol")==symbol and str(r.get("trade_date")) in required]
    if {str(r["trade_date"]) for r in rows} != required:
        return dict(base,reason="missing_symbol_sessions")
    pairs = {}
    try:
        for r in rows:
            if not r.get("contract_id") or r.get("side") not in ("buy","sell"):
                return dict(base,reason="contract_identity_missing")
            key=(str(r["trade_date"]),str(r["contract_id"]))
            sides=pairs.setdefault(key,{})
            if r["side"] in sides:
                return dict(base,reason="duplicate_contract_party")
            a,q=Decimal(str(r["amount"])),Decimal(str(r["quantity"]))
            if not a.is_finite() or not q.is_finite() or a<=0 or q<=0:
                return dict(base,reason="invalid_contract_values")
            sides[r["side"]]=(a,q)
    except (KeyError,InvalidOperation,ValueError,TypeError):
        return dict(base,reason="invalid_contract_values")
    if any(set(p)!={"buy","sell"} or p["buy"]!=p["sell"] for p in pairs.values()):
        return dict(base,reason="unbalanced_contract_parties")
    flow=broker_footprint_features(rows,minimum_amount_coverage=1.0)
    window=flow.get("security_features",{}).get(symbol,{}).get("1W" if n==5 else "1M",{})
    if window.get("status")!="observed" or not window.get("window_complete"):
        return dict(base,reason="broker_identity_or_history_incomplete")
    daily=structure.get("timeframes",{}).get("daily",{}).get("structure",{})
    bias=daily.get("bias")
    events=[e for e in daily.get("events",[]) if e.get("date") in required]
    if any(str(e.get("date"))>str(cutoff) for e in daily.get("events",[])):
        return dict(base,reason="future_structure_event")
    shift=any(e.get("type") in ("bos","choch") and e.get("direction")==bias for e in events)
    sweep=any(e.get("type")=="liquidity_sweep" and e.get("side")==("low" if bias=="bullish" else "high") for e in events)
    breadth=window["broker_breadth_balance"]
    agreement=(bias=="bullish" and breadth>0) or (bias=="bearish" and breadth<0)
    return dict(base,status="research_only",as_of=str(cutoff),bias=bias,
                structural_shift=shift,liquidity_sweep=sweep,broker_breadth_balance=breadth,
                directional_agreement=agreement,confluence_candidate=bool(shift and sweep and agreement),
                top_net_buyers=window["top_net_buyers"],top_net_sellers=window["top_net_sellers"],
                top3_gross_concentration_pct=window["top3_gross_concentration_pct"],
                contract_count=len(pairs),window_sessions=n,
                limitations=["Broker breadth is not aggregate market net buying.",
                             "Agreement is uncalibrated, not proof of ownership or manipulation.",
                             "Caller must supply independently reconciled and point-in-time available evidence."])
