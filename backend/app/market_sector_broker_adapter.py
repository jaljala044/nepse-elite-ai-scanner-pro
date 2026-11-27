"""Descriptive adapters; not a certified market health or sector rotation engine."""
from .automatic_evidence_adapter import derive_chart_evidence
from .portfolio_broker_memory import replay_broker_patterns

def derive_context(*, symbol, sector_symbol, stock_rows, index_rows, sector_rows,
                   broker_records, broker_numbers, sessions, assessment_time):
    chart=derive_chart_evidence(symbol=symbol,rows=stock_rows,benchmark_rows=index_rows,
                                sessions=sessions,assessment_time=assessment_time)
    market=derive_chart_evidence(symbol="NEPSE",rows=index_rows,benchmark_rows=index_rows,
                                 sessions=sessions,assessment_time=assessment_time)
    sector=derive_chart_evidence(symbol=sector_symbol,rows=sector_rows,benchmark_rows=index_rows,
                                 sessions=sessions,assessment_time=assessment_time)
    metrics=market["screen"]["metrics"]
    trend="UNKNOWN"
    if metrics:
        trend="BULLISH" if metrics["close"]>metrics["sma20"] and metrics["change_20_sessions_pct"]>0 else (
            "BEARISH" if metrics["close"]<metrics["sma20"] and metrics["change_20_sessions_pct"]<0 else "NEUTRAL")
    if not broker_numbers or len(set(broker_numbers))!=len(broker_numbers):
        raise ValueError("explicit_unique_broker_cohort_required")
    replay=replay_broker_patterns(records=broker_records,sessions=sessions,assessment_time=assessment_time)
    matches=[h for h in replay["histories"] if h["symbol"]==symbol and h["broker_numbers"]==sorted(broker_numbers)]
    broker="UNKNOWN"
    if matches and matches[0]["coverage"]==1:
        streak=matches[0]["latest_streak"]
        broker="BULLISH" if streak>=3 else "BEARISH" if streak<=-3 else "NEUTRAL"
    labels=dict(chart["labels"],sector=sector["labels"]["relative_strength"])
    return dict(symbol=symbol,labels=labels,market_trend=trend,broker_direction=broker,
                chart=chart,market=market,sector=sector,broker_memory=replay,
                market_health_score=None,market_regime="UNKNOWN",production_eligible=False,
                limitations=["Market trend proxy is not market regime or breadth.",
                             "Sector excess return is not full sector rotation ranking.",
                             "Explicit broker cohort only; no ownership inference.",
                             "Caller-attested records; no live data acquisition."])
