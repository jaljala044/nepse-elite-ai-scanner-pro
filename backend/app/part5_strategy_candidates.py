"""Research-only strategy engine comparison on causal prefixes."""
from .trend_features import minervini_trend_template
from .wyckoff_features import wyckoff_event_features
from .smc_features import smc_features
from .idpat_v3 import evaluate_provisional
from .broker_archive_memory import profile
from .scanner import quality_errors

def candidates(rows, *, broker_db=None, symbol=None, broker_sessions=None):
    if not rows or quality_errors(rows):
        raise ValueError("valid prefix required")
    days=[str(r["date"]) for r in rows]
    if days!=sorted(set(days)):
        raise ValueError("chronological prefix required")
    bars=[{**r,"session_date":str(r["date"])} for r in rows]
    last=days[-1]
    trend=minervini_trend_template(bars)
    wy=wyckoff_event_features(bars)
    smc=smc_features(bars)
    provisional=evaluate_provisional(rows,eligible=True)
    out={"minervini":trend.get("checks_passed")==7 if trend.get("score") is not None else None,
         "wyckoff":any(e["session_date"]==last and e["direction"]=="bullish" for e in wy.get("events",[])) if wy.get("status")=="observed" else None,
         "smc":any(e["session_date"]==last and e["direction"]=="bullish" for e in smc.get("timeframes",{}).get("daily",{}).get("events",[])) if smc.get("timeframes",{}).get("daily",{}).get("status")=="observed" else None,
         "provisional":provisional.get("score")==100 if provisional.get("score") is not None else None,
         "broker":None,"authentic_idpat":None,"master":None}
    events=wy.get("events",[])
    today={e["event"] for e in events if e["session_date"]==last and e["direction"]=="bullish"}
    observed=wy.get("status")=="observed"
    out.update({
        "wyckoff_spring": "spring" in today if observed else None,
        "wyckoff_sos": "sos" in today if observed else None,
        "wyckoff_lps": "lps" in today if observed else None,
        "wyckoff_lps_smc": ("lps" in today and out["smc"]) if observed and out["smc"] is not None else None,
        "wyckoff_sos_trend": ("sos" in today and out["minervini"]) if observed and out["minervini"] is not None else None,
    })
    if broker_db is not None and broker_sessions and symbol:
        if list(broker_sessions)!=sorted(set(broker_sessions)) or broker_sessions[-1]>last:
            raise ValueError("future or invalid broker sessions")
        p=profile(broker_db,symbol,broker_sessions)
        if p.get("status")=="archive_research_only" and p.get("brokers"):
            out["broker"]=any(b["classification"]=="persistent_net_buy" for b in p["brokers"])
    return {"classification":"research_candidates_only","as_of":last,"candidates":out,"production_eligible":False}
