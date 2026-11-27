"""Independent descriptive scanner adapters; not calibrated trading signals."""
import hashlib,json
from .automatic_evidence_adapter import derive_chart_evidence
from .wyckoff_features import wyckoff_event_features
from .trend_features import minervini_trend_template
from .idpat_horizon_research import broker_persistence

def momentum(closes):
    def ema(values,n):
        if len(values)<n: return []
        result=[sum(values[:n])/n]
        for v in values[n:]: result.append(result[-1]+2/(n+1)*(v-result[-1]))
        return result
    rsi=None
    if len(closes)>=15:
        changes=[b-a for a,b in zip(closes,closes[1:])]
        gain=sum(max(x,0) for x in changes[:14])/14
        loss=sum(max(-x,0) for x in changes[:14])/14
        for x in changes[14:]:
            gain=(13*gain+max(x,0))/14; loss=(13*loss+max(-x,0))/14
        rsi=100-100/(1+gain/loss) if loss else 100 if gain else 50
    fast,slow=ema(closes,12),ema(closes,26)
    macd=[a-b for a,b in zip(fast[14:],slow)]
    signal=ema(macd,9)
    return dict(rsi14=rsi,macd=macd[-1] if macd else None,signal=signal[-1] if signal else None,
        histogram=macd[-1]-signal[-1] if signal else None)

def native_reviews(*,symbol,horizon,rows,benchmark_rows,sessions,assessment_time,broker_records):
    chart=derive_chart_evidence(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,sessions=sessions,assessment_time=assessment_time)
    bars=[dict(r,session_date=r["date"]) for r in sorted(rows,key=lambda r:r["date"])]
    wy=wyckoff_event_features(bars)
    recent=set(sessions[-5:])
    directions={e["direction"].upper() for e in wy["events"] if e["session_date"] in recent}
    wd=next(iter(directions)) if len(directions)==1 else "UNKNOWN"
    trend=minervini_trend_template(bars)
    mom=momentum([float(r["close"]) for r in bars])
    md="BULLISH" if trend.get("checks_passed")==7 and mom["histogram"] is not None and mom["histogram"]>0 else "UNKNOWN"
    flow=broker_persistence(broker_records,sessions,symbol,assessment_time) if len(sessions)>=5 else "UNKNOWN"
    bd={"PERSISTENT_BUYING_PROXY":"BULLISH","PERSISTENT_SELLING_PROXY":"BEARISH","MIXED":"NEUTRAL"}.get(flow,"UNKNOWN")
    payloads={"WYCKOFF":(wd,wy),"SMC":(chart["labels"]["smc"],chart["structure"]),"BROKER":(bd,dict(flow=flow)),"MINERVINI_MOMENTUM":(md,dict(trend=trend,momentum=mom))}
    result={}
    for name,(direction,evidence) in payloads.items():
        payload=dict(symbol=symbol,horizon=horizon,available_at=assessment_time,direction=direction,evidence=evidence,method=name,production_eligible=False)
        result[name]=dict(payload,evidence_id=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
    return result
