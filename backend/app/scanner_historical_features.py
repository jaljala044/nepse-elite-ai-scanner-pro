"""Point-in-time historical feature snapshots for NEPSE strategy research.

Computes transparent price/volume features from admitted OHLCV. It deliberately
does not turn a feature into a BUY recommendation or claim Wyckoff/SMC events.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
import hashlib, json

WINDOWS=(5,20,50,150,200)
_NEPAL_TZ=ZoneInfo("Asia/Kathmandu")


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


def _day(value, field):
    if not isinstance(value,str):
        raise ValueError(field+"_must_be_canonical_YYYY_MM_DD")
    try: parsed=date.fromisoformat(value)
    except ValueError: raise ValueError(field+"_must_be_canonical_YYYY_MM_DD") from None
    if parsed.isoformat()!=value:
        raise ValueError(field+"_must_be_canonical_YYYY_MM_DD")
    return parsed


def _sma(values,n):
    return sum(values[-n:],Decimal("0"))/Decimal(n) if len(values)>=n else None


def _rsi(values,n=14):
    if len(values)<n+1: return None
    changes=[values[i]-values[i-1] for i in range(len(values)-n,len(values))]
    gains=sum((max(x,Decimal("0")) for x in changes),Decimal("0"))/n
    losses=sum((max(-x,Decimal("0")) for x in changes),Decimal("0"))/n
    if losses==0: return Decimal("100") if gains>0 else Decimal("50")
    return Decimal("100")-(Decimal("100")/(Decimal("1")+gains/losses))


def _history_lineage(rows):
    return [{
        "session_date":row["_day"].isoformat(),
        "open":str(row["_v"]["open"]),
        "high":str(row["_v"]["high"]),
        "low":str(row["_v"]["low"]),
        "close":str(row["_v"]["close"]),
        "volume":str(row["_v"]["volume"]),
        "turnover":str(row["_v"]["turnover"]),
        "source_id":row["source_id"],
        "evidence_id":row["evidence_id"],
        "available_at":row["available_at"],
    } for row in rows]


def build_point_in_time_feature_snapshots(*, panel_rows, decision_cutoffs, benchmark_rows=None):
    """Build one point-in-time snapshot per security/session.

    Historical inputs are re-filtered against each snapshot's own cutoff. A
    bar admitted for a different (later) cutoff is never carried into an
    earlier decision. The caller remains responsible for exchange-calendar
    and source-byte admission; this function does not infer missing sessions.
    """
    if not isinstance(panel_rows,list) or not isinstance(decision_cutoffs,dict):
        raise ValueError("panel_rows_and_decision_cutoffs_required")
    grouped={}
    seen=set()
    for row in panel_rows:
        if not isinstance(row,dict): raise ValueError("panel_row_invalid")
        sid=row.get("security_id")
        if not isinstance(sid,str) or not sid.strip():
            raise ValueError("panel_security_id_invalid")
        sid=sid.strip().upper()
        parsed=_day(row.get("session_date"),"panel_session_date")
        day=parsed.isoformat()
        identity=(sid,day)
        if identity in seen: raise ValueError("duplicate_security_session:"+sid+":"+day)
        seen.add(identity)
        source_id=row.get("source_id"); evidence_id=row.get("evidence_id")
        if not isinstance(source_id,str) or not source_id.strip() or not isinstance(evidence_id,str) or not evidence_id.strip():
            raise ValueError("panel_provenance_missing")
        available=_time(row.get("available_at"))
        if available is None:
            raise ValueError("panel_provenance_missing")
        if available.astimezone(_NEPAL_TZ).date()<parsed:
            raise ValueError("bar_available_before_session:"+sid+":"+day)
        values={k:_dec(row.get(k)) for k in ("open","high","low","close","volume","turnover")}
        if any(v is None for v in values.values()):
            raise ValueError("panel_ohlcv_invalid")
        if min(values[k] for k in ("open","high","low","close"))<=0:
            raise ValueError("panel_ohlcv_invalid")
        if values["volume"]<=0 or values["volume"]!=values["volume"].to_integral_value():
            raise ValueError("panel_ohlcv_invalid")
        if values["turnover"]<=0:
            raise ValueError("panel_ohlcv_invalid")
        if values["high"]<max(values["open"],values["close"],values["low"]) or values["low"]>min(values["open"],values["close"],values["high"]):
            raise ValueError("panel_ohlc_inconsistent")
        symbol=row.get("symbol")
        if not isinstance(symbol,str) or not symbol.strip():
            raise ValueError("panel_symbol_invalid")
        grouped.setdefault(sid,[]).append({**row,"security_id":sid,"symbol":symbol.strip().upper(),
            "_day":parsed,"_available":available,"_v":values})

    benchmark={}
    for row in benchmark_rows or []:
        if not isinstance(row,dict): raise ValueError("benchmark_row_invalid")
        parsed=_day(row.get("session_date"),"benchmark_session_date")
        d=parsed.isoformat()
        if d in benchmark: raise ValueError("duplicate_benchmark_session:"+d)
        value=_dec(row.get("close"))
        available=_time(row.get("available_at"))
        source_id=row.get("source_id"); evidence_id=row.get("evidence_id")
        if (value is None or value<=0 or available is None
                or not isinstance(source_id,str) or not source_id.strip()
                or not isinstance(evidence_id,str) or not evidence_id.strip()):
            raise ValueError("benchmark_provenance_or_close_invalid")
        if available.astimezone(_NEPAL_TZ).date()<parsed:
            raise ValueError("benchmark_available_before_session:"+d)
        benchmark[d]={"close":value,"available":available,"source_id":source_id,
            "evidence_id":evidence_id,"available_at":row["available_at"]}

    output=[]; errors=[]
    for sid,rows in sorted(grouped.items()):
        rows.sort(key=lambda x:x["_day"])
        for index,row in enumerate(rows):
            day=row["_day"].isoformat()
            cutoff=_time(decision_cutoffs.get(day))
            if cutoff is None:
                errors.append("decision_cutoff_missing_or_invalid:"+day)
                continue
            local_cutoff_date=cutoff.astimezone(_NEPAL_TZ).date()
            if row["_day"]>local_cutoff_date:
                errors.append("future_session_after_decision_cutoff:"+sid+":"+day)
                continue
            if row["_available"]>cutoff:
                errors.append("bar_not_available_at_decision:"+sid+":"+day)
                continue

            # Re-evaluate every historical input against this decision cutoff.
            # Do not reuse rows admitted under another session's later cutoff.
            as_of_rows=[candidate for candidate in rows[:index+1]
                if candidate["_day"]<=row["_day"] and candidate["_available"]<=cutoff]
            if not as_of_rows or as_of_rows[-1] is not row:
                errors.append("current_bar_missing_from_point_in_time_history:"+sid+":"+day)
                continue
            closes=[item["_v"]["close"] for item in as_of_rows]
            volumes=[item["_v"]["volume"] for item in as_of_rows]
            prior_dates=[item["_day"].isoformat() for item in as_of_rows]
            returns={}
            for n in (5,20,60,120):
                returns["return_"+str(n)+"_session_pct"]=str((closes[-1]/closes[-n-1]-1)*100) if len(closes)>n else None
            averages={str(n):_sma(closes,n) for n in WINDOWS}
            vol_avg=_sma(volumes,20)
            bench=benchmark.get(day)
            if bench and bench["available"]>cutoff:
                errors.append("benchmark_not_available_at_decision:"+day)
                bench=None
            bench_return=None
            benchmark_history=[]
            if bench:
                benchmark_history=[benchmark.get(x) for x in prior_dates]
                if all(x is not None and x["available"]<=cutoff for x in benchmark_history):
                    for n in (20,60):
                        if len(benchmark_history)>n:
                            bench_return=(bench["close"]/benchmark_history[-n-1]["close"]-1)*100
                            break
            close=closes[-1]
            current_lineage=_history_lineage(as_of_rows)
            benchmark_lineage=[{
                "session_date":prior_dates[i],"source_id":item["source_id"],
                "evidence_id":item["evidence_id"],"available_at":item["available_at"],
                "close":str(item["close"]),
            } for i,item in enumerate(benchmark_history) if item is not None]
            digest_payload={
                "security_id":sid,"symbol":row["symbol"],"session_date":day,
                "decision_cutoff":cutoff.isoformat(),"history_session_count":len(as_of_rows),
                "history_lineage":current_lineage,"benchmark_lineage":benchmark_lineage,
                "returns":returns,
                "sma":{k:(str(v) if v is not None else None) for k,v in averages.items()},
                "rsi14":str(_rsi(closes)) if _rsi(closes) is not None else None,
                "benchmark_return_used_pct":str(bench_return) if bench_return is not None else None,
            }
            digest=hashlib.sha256(json.dumps(digest_payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            output.append({"security_id":sid,"symbol":row["symbol"],"session_date":day,
                "decision_cutoff":cutoff.isoformat(),"close":str(close),"returns":returns,
                "sma":{k:(str(v) if v is not None else None) for k,v in averages.items()},
                "price_above_sma50":close>averages["50"] if averages["50"] is not None else None,
                "sma_stack_50_150_200":(averages["50"]>averages["150"]>averages["200"]) if all(averages[k] is not None for k in ("50","150","200")) else None,
                "rsi14":str(_rsi(closes)) if _rsi(closes) is not None else None,
                "volume_ratio_20":str(volumes[-1]/vol_avg) if vol_avg and vol_avg>0 else None,
                "benchmark_close":str(bench["close"]) if bench else None,
                "benchmark_return_used_pct":str(bench_return) if bench_return is not None else None,
                "history_session_count":len(as_of_rows),
                "feature_snapshot_sha256":digest,
                "feature_status":"complete" if averages["200"] is not None and _rsi(closes) is not None else "warmup_incomplete",
                "evidence":{"source_id":row["source_id"],"evidence_id":row["evidence_id"],"available_at":row["available_at"]}})
    return {"schema_version":"nepse-point-in-time-features-1.0.0",
        "status":"validated_for_research" if output and not errors else "partial_or_blocked",
        "snapshot_count":len(output),"snapshots":output,"errors":sorted(set(errors)),
        "feature_policy":"strict point-in-time history; reject future/noncanonical dates, zero/fractional share volume and invalid OHLC; no future bars; moving averages 5/20/50/150/200; RSI14; 20-session volume ratio; returns 5/20/60/120; benchmark only when point-in-time aligned",
        "limitations":["Warm-up-incomplete snapshots are not trade signals.",
            "The caller must supply a verified exchange-session/calendar and admitted source bytes; this function does not certify completeness or rights.",
            "Benchmark-relative return requires complete aligned benchmark history; no missing sessions are imputed.",
            "No Wyckoff/SMC/broker/fundamental evidence is fabricated.",
            "No BUY/SELL recommendation, probabilities or performance claims are produced."],
        "performance_claimed":False,"production_enabled":False}
