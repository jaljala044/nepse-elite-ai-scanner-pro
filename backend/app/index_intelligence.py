"""Reviewed index trends and transparent relative-rotation proxies."""
from datetime import date
from math import isfinite
WINDOWS=(5,21,63,126,252)

def index_intelligence(rows, *, sessions, benchmark, expected_indices, calendar_verified=False):
    base={"status":"unavailable","production_score":None,"indices":{}}
    days=[date.fromisoformat(str(x)).isoformat() for x in sessions]
    if not calendar_verified or len(days)<51 or days!=sorted(set(days)):
        return dict(base,reason="verified_calendar_or_history_missing")
    expected=set(expected_indices)
    if benchmark not in expected:return dict(base,reason="benchmark_missing")
    series={k:{} for k in expected}
    for r in rows:
        k=r.get("index");day=str(r.get("date"))
        if k not in expected or day not in days or day in series[k]:
            return dict(base,reason="duplicate_or_out_of_scope")
        if r.get("reviewed") is not True or not r.get("evidence_id"):
            return dict(base,reason="unreviewed_index_row")
        try:
            if isinstance(r["close"],bool):raise ValueError()
            p=float(r["close"])
            if not isfinite(p) or p<=0:raise ValueError()
        except (ValueError,TypeError,KeyError,OverflowError):
            return dict(base,reason="invalid_index_close")
        series[k][day]=p
    out={}
    for k,s in sorted(series.items()):
        if any(d not in s for d in days[-51:]):
            out[k]={"status":"unavailable","reason":"missing_recent_sessions"};continue
        v=s[days[-1]]
        sma20=sum(s[d] for d in days[-20:])/20
        sma50=sum(s[d] for d in days[-50:])/50
        trend="bullish" if v>sma20>sma50 else "bearish" if v<sma20<sma50 else "mixed"
        returns={str(n):100*(v/s[days[-n-1]]-1) if len(days)>n and all(d in s for d in days[-n-1:]) else None for n in WINDOWS}
        out[k]={"status":"research_only","close":v,"sma20":sma20,"sma50":sma50,"trend":trend,"returns_pct":returns}
    b=series[benchmark]
    for k,item in out.items():
        s=series[k]
        if item["status"]!="research_only" or any(d not in b for d in days[-51:]):continue
        trail=[]
        for i in range(max(26,len(days)-6),len(days)):
            segment=days[i-26:i+1]
            if any(d not in s or d not in b for d in segment):continue
            ratio=lambda j:s[days[j]]/b[days[j]]
            strength=100*(ratio(i)/ratio(i-21)-1)
            prior=100*(ratio(i-5)/ratio(i-26)-1)
            momentum=strength-prior
            quadrant="leading" if strength>=0 and momentum>=0 else "weakening" if strength>=0 else "improving" if momentum>=0 else "lagging"
            trail.append({"date":days[i],"relative_return_pct":strength,"momentum_change_pp":momentum,"quadrant":quadrant})
        item["rotation_trail"]=trail
    return dict(base,status="research_only" if out.get(benchmark,{}).get("status")=="research_only" else "unavailable",
                as_of=days[-1],benchmark=benchmark,indices=out,
                methodology="21-session relative return and five-session change; not proprietary RRG",
                independent_validation=False)
