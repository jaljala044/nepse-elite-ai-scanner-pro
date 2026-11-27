"""Point-in-time historical feature snapshots for NEPSE strategy research.

Computes transparent price/volume features from admitted OHLCV. It deliberately
does not turn a feature into a BUY recommendation or claim Wyckoff/SMC events.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib, json

WINDOWS=(5,20,50,150,200)

def _dec(value):
    try:
        x=Decimal(str(value))
        return x if x.is_finite() else None
    except (InvalidOperation,TypeError,ValueError):
        return None

def _time(value):
    if not isinstance(value,str): return None
    try: x=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if x.tzinfo is None or x.utcoffset() is None: return None
    return x.astimezone(timezone.utc)

def _sma(values,n):
    return sum(values[-n:],Decimal("0"))/Decimal(n) if len(values)>=n else None

def _rsi(values,n=14):
    if len(values)<n+1: return None
    changes=[values[i]-values[i-1] for i in range(len(values)-n,len(values))]
    gains=sum((max(x,Decimal("0")) for x in changes),Decimal("0"))/n
    losses=sum((max(-x,Decimal("0")) for x in changes),Decimal("0"))/n
    if losses==0: return Decimal("100") if gains>0 else Decimal("50")
    return Decimal("100")-(Decimal("100")/(Decimal("1")+gains/losses))

def build_point_in_time_feature_snapshots(*, panel_rows, decision_cutoffs, benchmark_rows=None):
    """Build one snapshot per security/session; all inputs must be available by cutoff."""
    if not isinstance(panel_rows,list) or not isinstance(decision_cutoffs,dict):
        raise ValueError("panel_rows_and_decision_cutoffs_required")
    grouped={}
    for row in panel_rows:
        if not isinstance(row,dict): raise ValueError("panel_row_invalid")
        sid=str(row.get("security_id","")).strip().upper()
        day=str(row.get("session_date",""))
        try: parsed=date.fromisoformat(day)
        except ValueError: raise ValueError("panel_session_date_invalid") from None
        available=_time(row.get("available_at"))
        if not sid or not row.get("source_id") or not row.get("evidence_id") or available is None:
            raise ValueError("panel_provenance_missing")
        values={k:_dec(row.get(k)) for k in ("open","high","low","close","volume","turnover")}
        if any(v is None for v in values.values()) or min(values[k] for k in ("open","high","low","close"))<=0 or values["volume"]<0 or values["turnover"]<0:
            raise ValueError("panel_ohlcv_invalid")
        grouped.setdefault(sid,[]).append({**row,"_day":parsed,"_available":available,"_v":values})
    benchmark={}
    for row in benchmark_rows or []:
        d=str(row.get("session_date",""))
        try: date.fromisoformat(d)
        except ValueError: raise ValueError("benchmark_session_date_invalid") from None
        value=_dec(row.get("close"))
        available=_time(row.get("available_at"))
        if value is None or value<=0 or available is None or not row.get("source_id") or not row.get("evidence_id"):
            raise ValueError("benchmark_provenance_or_close_invalid")
        benchmark[d]=(value,available)
    output=[]; errors=[]
    for sid,rows in sorted(grouped.items()):
        rows.sort(key=lambda x:x["_day"])
        if len({x["_day"] for x in rows})!=len(rows): raise ValueError("duplicate_security_session:"+sid)
        closes=[]; volumes=[]; prior_dates=[]
        for row in rows:
            day=row["_day"].isoformat()
            cutoff=_time(decision_cutoffs.get(day))
            if cutoff is None: errors.append("decision_cutoff_missing_or_invalid:"+day); continue
            if row["_available"]>cutoff: errors.append("bar_not_available_at_decision:"+sid+":"+day); continue
            closes.append(row["_v"]["close"]); volumes.append(row["_v"]["volume"]); prior_dates.append(day)
            returns={}
            for n in (5,20,60,120):
                returns["return_"+str(n)+"_session_pct"]=str((closes[-1]/closes[-n-1]-1)*100) if len(closes)>n else None
            averages={str(n):_sma(closes,n) for n in WINDOWS}
            vol_avg=_sma(volumes,20)
            bench=benchmark.get(day)
            if bench and bench[1]>cutoff: errors.append("benchmark_not_available_at_decision:"+day); bench=None
            bench_return=None
            if bench:
                # Relative strength uses aligned benchmark closes only when matching history is supplied.
                bench_hist=[benchmark.get(x) for x in prior_dates]
                if all(x is not None and x[1]<=cutoff for x in bench_hist):
                    for n in (20,60):
                        if len(bench_hist)>n:
                            bench_return=(bench[0]/bench_hist[-n-1][0]-1)*100
                            break
            close=closes[-1]
            digest_payload={"security_id":sid,"session_date":day,"close":str(close),"volume":str(volumes[-1]),
                "returns":returns,"sma":{k:(str(v) if v is not None else None) for k,v in averages.items()},
                "rsi14":str(_rsi(closes)) if _rsi(closes) is not None else None}
            digest=hashlib.sha256(json.dumps(digest_payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            output.append({"security_id":sid,"symbol":row.get("symbol"),"session_date":day,
                "decision_cutoff":cutoff.isoformat(),"close":str(close),"returns":returns,
                "sma":{k:(str(v) if v is not None else None) for k,v in averages.items()},
                "price_above_sma50":close>averages["50"] if averages["50"] is not None else None,
                "sma_stack_50_150_200":(averages["50"]>averages["150"]>averages["200"]) if all(averages[k] is not None for k in ("50","150","200")) else None,
                "rsi14":str(_rsi(closes)) if _rsi(closes) is not None else None,
                "volume_ratio_20":str(volumes[-1]/vol_avg) if vol_avg and vol_avg>0 else None,
                "benchmark_close":str(bench[0]) if bench else None,
                "benchmark_return_used_pct":str(bench_return) if bench_return is not None else None,
                "feature_snapshot_sha256":digest,"feature_status":"complete" if averages["200"] is not None and _rsi(closes) is not None else "warmup_incomplete",
                "evidence":{"source_id":row["source_id"],"evidence_id":row["evidence_id"],"available_at":row["available_at"]}})
    return {"schema_version":"nepse-point-in-time-features-1.0.0","status":"validated_for_research" if output and not errors else "partial_or_blocked",
        "snapshot_count":len(output),"snapshots":output,"errors":sorted(set(errors)),
        "feature_policy":"strict chronological history; no future bars; moving averages 5/20/50/150/200; RSI14; 20-session volume ratio; returns 5/20/60/120; benchmark only when point-in-time aligned",
        "limitations":["Warm-up-incomplete snapshots are not trade signals.","Benchmark-relative return requires a complete aligned benchmark history and is not inferred from an index label.","No Wyckoff/SMC/broker/fundamental evidence is fabricated.","No BUY/SELL recommendation, probabilities or performance claims are produced."],
        "performance_claimed":False,"production_enabled":False}
