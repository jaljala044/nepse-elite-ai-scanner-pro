"""Technical evidence descriptors, not production scores."""
from statistics import mean
from .automatic_evidence_adapter import derive_chart_evidence
from .idpat_v3 import evaluate_idpat_v3

def derive_advanced_technical(*,symbol,rows,benchmark_rows,sessions,assessment_time):
    base=derive_chart_evidence(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,
                               sessions=sessions,assessment_time=assessment_time)
    bars=sorted(rows,key=lambda r:r["date"])
    index=sorted(benchmark_rows,key=lambda r:r["date"])
    c=[float(r["close"]) for r in bars]
    b=[float(r["close"]) for r in index]
    windows={"1W":(5,.2),"1M":(21,.3),"3M":(63,.3),"6M":(126,.2)}
    rs={k:100*(c[-1]/c[-1-n]-b[-1]/b[-1-n]) if len(c)>n else None for k,(n,w) in windows.items()}
    weighted=sum(rs[k]*w for k,(n,w) in windows.items()) if all(v is not None for v in rs.values()) else None
    trend={}
    if len(c)>=252:
        m50,m150,m200=[mean(c[-n:]) for n in (50,150,200)]
        trend=dict(above_averages=c[-1]>max(m50,m150,m200),
                   ordered_averages=m50>m150>m200,
                   rising_200=m200>mean(c[-221:-21]),
                   near_52week_high=c[-1]>=.75*max(float(r["high"]) for r in bars[-252:]))
    volume=None
    if len(c)>=21:
        prior=mean(float(r["volume"]) for r in bars[-21:-1])
        last=bars[-1]
        spread=float(last["high"])-float(last["low"])
        volume=dict(relative_volume=float(last["volume"])/prior if prior else None,
                    close_location=(c[-1]-float(last["low"]))/spread if spread else None,
                    spread=spread)
    return dict(base,weighted_rs_pct=weighted,rs_windows_pct=rs,
                minervini_checks=trend,minervini_status="PARTIAL" if trend else "UNKNOWN",
                vsa_descriptors=volume,wyckoff_status="UNKNOWN",
                idpat=evaluate_idpat_v3(bars,eligible=False),
                advanced_limitations=["Session-count windows approximate calendar periods.",
                    "252 sessions approximate 52 weeks; higher highs/lows not evaluated.",
                    "VSA descriptors do not establish absorption or Wyckoff phases.",
                    "IDPAT specification and production eligibility remain unverified."])
