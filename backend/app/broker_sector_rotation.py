"""Evidence-gated broker sector rotation summaries.

Rotation means a measured change in broker-side transaction participation across
mapped sectors. It is not proof of intent, beneficial ownership, or a trade signal.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable


class BrokerRotationError(ValueError):
    pass


def _d(value, field):
    try:
        x=Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise BrokerRotationError(f"invalid_{field}") from None
    if not x.is_finite() or x < 0:
        raise BrokerRotationError(f"invalid_{field}")
    return x


def _ts(value):
    try: x=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (AttributeError,TypeError,ValueError):
        raise BrokerRotationError("invalid_as_of_timestamp") from None
    if x.tzinfo is None or x.utcoffset() is None:
        raise BrokerRotationError("as_of_timestamp_must_be_timezone_aware")
    return x


def build_broker_sector_rotation(
    observations: list[dict], *,
    security_sector_map: dict[str,str],
    verified_exchange_sessions: Iterable[str],
    complete_source_sessions: Iterable[str],
    as_of_date: str,
    as_of_timestamp: str,
    current_sessions: int=5,
    comparison_sessions: int=5,
    min_coverage: Decimal=Decimal("0.95"),
) -> dict:
    """Compare latest and immediately preceding complete windows per broker."""
    try: cutoff=date.fromisoformat(as_of_date)
    except (TypeError,ValueError): raise BrokerRotationError("invalid_as_of_date") from None
    available=_ts(as_of_timestamp)
    if isinstance(current_sessions,bool) or not isinstance(current_sessions,int) or current_sessions<1:
        raise BrokerRotationError("current_sessions_must_be_positive")
    if isinstance(comparison_sessions,bool) or not isinstance(comparison_sessions,int) or comparison_sessions<1:
        raise BrokerRotationError("comparison_sessions_must_be_positive")
    threshold=_d(min_coverage,"min_coverage")
    if threshold<=0 or threshold>1: raise BrokerRotationError("invalid_min_coverage")
    if not isinstance(security_sector_map,dict) or not security_sector_map:
        raise BrokerRotationError("security_sector_map_required")
    if any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip()
           for k,v in security_sector_map.items()):
        raise BrokerRotationError("invalid_security_sector_mapping")

    def calendar(values,label):
        out=[]
        for x in values:
            try: day=date.fromisoformat(x)
            except (TypeError,ValueError): raise BrokerRotationError(f"invalid_{label}_date") from None
            if day<=cutoff: out.append(day)
        if len(out)!=len(set(out)): raise BrokerRotationError(f"duplicate_{label}_date")
        return sorted(out)
    cal=calendar(verified_exchange_sessions,"exchange_session")
    complete=set(calendar(complete_source_sessions,"complete_source_session"))
    if not complete.issubset(set(cal)): raise BrokerRotationError("complete_session_not_verified")
    # Use only the most recent N+M verified exchange sessions. Incomplete
    # sessions reduce coverage; they are not skipped to reach farther back.
    needed=current_sessions+comparison_sessions
    selected=cal[-needed:]
    prior=selected[:comparison_sessions]
    current=selected[comparison_sessions:]
    if len(selected)<needed: return {
        "status":"insufficient_evidence","reason":"insufficient_verified_exchange_history",
        "required_sessions":needed,"available_sessions":len(selected),"brokers":[],
        "policy":"descriptive_only_no_signal"
    }
    prior_covered=[x for x in prior if x in complete]
    current_covered=[x for x in current if x in complete]
    prior_cov=Decimal(len(prior_covered))/Decimal(len(prior))
    current_cov=Decimal(len(current_covered))/Decimal(len(current))
    if prior_cov<threshold or current_cov<threshold:
        return {"status":"insufficient_evidence","reason":"source_coverage_below_threshold",
            "prior_coverage":str(prior_cov),"current_coverage":str(current_cov),
            "brokers":[],"policy":"descriptive_only_no_signal"}

    # One observation per broker/security/session/side/source/evidence.
    seen=set(); totals={}
    excluded=0
    for i,row in enumerate(observations):
        try:
            day=date.fromisoformat(row["session_date"])
            ts=_ts(row["available_at"])
        except (KeyError,TypeError,ValueError,BrokerRotationError):
            excluded+=1; continue
        if day>cutoff or ts>available or day not in complete:
            excluded+=1; continue
        sec=row.get("security_id"); broker=row.get("broker_id")
        if sec not in security_sector_map or not isinstance(broker,str) or not broker.strip():
            excluded+=1; continue
        if row.get("status")!="descriptive_only" or row.get("side") not in {"BUY","SELL"}:
            excluded+=1; continue
        try: amount=_d(row.get("amount"),"amount")
        except BrokerRotationError: excluded+=1; continue
        if not all(isinstance(row.get(k),str) and row[k].strip()
                   for k in ("source_id","evidence_id","source_payload_sha256")):
            excluded+=1; continue
        key=(broker,sec,day,row["side"],row["source_id"],row["evidence_id"])
        if key in seen: raise BrokerRotationError("duplicate_observation_natural_key")
        seen.add(key)
        sector=security_sector_map[sec]
        bucket=totals.setdefault((broker,sector,day),{"buy":Decimal(0),"sell":Decimal(0)})
        bucket[row["side"].lower()]+=amount

    broker_ids=sorted({key[0] for key in totals})
    results=[]
    for broker in broker_ids:
        sectors=sorted({sector for b,sector,_ in totals if b==broker})
        sector_rows=[]
        for sector in sectors:
            def sums(days):
                buy=sum((totals.get((broker,sector,d),{}).get("buy",Decimal(0)) for d in days),Decimal(0))
                sell=sum((totals.get((broker,sector,d),{}).get("sell",Decimal(0)) for d in days),Decimal(0))
                return buy,sell,buy+sell,buy-sell
            pb,ps,pg,pn=sums(prior_covered)
            cb,cs,cg,cn=sums(current_covered)
            # Denominator is the broker's total mapped-sector turnover,
            # not the current sector's own turnover multiplied by sector count.
            prior_total=sum((
                totals.get((broker, other_sector, day), {}).get("buy", Decimal(0))
                + totals.get((broker, other_sector, day), {}).get("sell", Decimal(0))
                for other_sector in sectors for day in prior_covered
            ), Decimal(0))
            current_total=sum((
                totals.get((broker, other_sector, day), {}).get("buy", Decimal(0))
                + totals.get((broker, other_sector, day), {}).get("sell", Decimal(0))
                for other_sector in sectors for day in current_covered
            ), Decimal(0))
            prior_share=pg/prior_total if prior_total else None
            current_share=cg/current_total if current_total else None
            shift=(current_share-prior_share) if prior_share is not None and current_share is not None else None
            sector_rows.append({
                "sector":sector,"prior_buy_amount":str(pb),"prior_sell_amount":str(ps),
                "prior_net_amount":str(pn),"prior_gross_amount":str(pg),
                "current_buy_amount":str(cb),"current_sell_amount":str(cs),
                "current_net_amount":str(cn),"current_gross_amount":str(cg),
                "prior_activity_share":str(prior_share) if prior_share is not None else None,
                "current_activity_share":str(current_share) if current_share is not None else None,
                "activity_share_change":str(shift) if shift is not None else None,
                "classification":(
                    "participation_increased" if shift is not None and shift>Decimal("0.05") else
                    "participation_decreased" if shift is not None and shift<Decimal("-0.05") else
                    "no_material_share_change" if shift is not None else "insufficient_activity_denominator"
                ),
            })
        increases=[x for x in sector_rows if x["classification"]=="participation_increased"]
        decreases=[x for x in sector_rows if x["classification"]=="participation_decreased"]
        results.append({"broker_id":broker,"prior_sessions":len(prior_covered),
            "current_sessions":len(current_covered),"prior_coverage":str(prior_cov),
            "current_coverage":str(current_cov),"sector_rotation_candidates":{
                "increased_participation":[x["sector"] for x in increases],
                "decreased_participation":[x["sector"] for x in decreases]},
            "sectors":sector_rows,
            "interpretation":"Descriptive change in broker-side transaction mix; not proof of intent, accumulation, distribution or a trade signal."})
    return {"status":"descriptive_only","as_of_date":cutoff.isoformat(),
        "as_of_timestamp":available.isoformat(),"prior_window":[x.isoformat() for x in prior],
        "current_window":[x.isoformat() for x in current],
        "prior_complete_sessions":[x.isoformat() for x in prior_covered],
        "current_complete_sessions":[x.isoformat() for x in current_covered],
        "prior_coverage":str(prior_cov),"current_coverage":str(current_cov),
        "excluded_rows":excluded,"brokers":results,
        "policy":"broker_side_turnover_mix_not_ownership_or_trade_signal"}
