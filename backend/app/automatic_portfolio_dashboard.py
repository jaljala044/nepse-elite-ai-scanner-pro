"""Automatic research evidence orchestration, not independent source verification."""
import hashlib
import json
from .liquidity_trap_review import review_liquidity_trap
from .portfolio_dashboard_review import portfolio_dashboard_review
from .corporate_action_trade_plan import _number, _time

def automatic_portfolio_dashboard(*,holding,quote,snapshot,limits,market,sector,
                                  assessment_time,reduction_fraction,rows,benchmark_rows,
                                  sessions,broker_records,broker_numbers,cost_assumptions=None,
                                  trailing_config=None):
    symbol=holding["symbol"]
    trap=review_liquidity_trap(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,
        sessions=sessions,assessment_time=assessment_time,broker_records=broker_records,
        broker_numbers=broker_numbers)
    latest=max(rows,key=lambda r:r["date"])
    if latest["basis_id"]!=holding["basis_id"] or _number(latest["close"])!=_number(quote["close"]):
        raise ValueError("chart_holding_basis_or_quote_mismatch")
    if latest["date"]!=_time(quote["observed_at"]).date().isoformat():
        raise ValueError("chart_quote_session_mismatch")
    if _time(latest["available_at"])>_time(quote["available_at"]):
        raise ValueError("chart_quote_availability_mismatch")
    sources=sorted({r["source_id"] for r in rows+benchmark_rows+broker_records})
    digest=hashlib.sha256(json.dumps(dict(rows=rows,benchmark=benchmark_rows,brokers=broker_records,
        cohort=broker_numbers,sessions=sessions,assessment_time=assessment_time),sort_keys=True,
        separators=(",",":"),default=str).encode()).hexdigest()
    # Internal adapter status denotes accepted caller-attested inputs, not exchange certification.
    distribution=dict(symbol=symbol,action=trap["action"],as_of_session=trap["as_of_session"],
        status="verified",source_id="derived-research:"+digest,available_at=assessment_time,
        input_source_ids=sources,classification="derived_caller_attested_research")
    trailing=None
    if trailing_config is not None:
        allowed={"original_quantity","remaining_quantity","previous_stop","targets","cumulative_fractions"}
        if set(trailing_config)!=allowed: raise ValueError("invalid_trailing_config")
        trailing=dict(trailing_config,rows=rows,benchmark_rows=benchmark_rows,sessions=sessions)
    result=portfolio_dashboard_review(holding=holding,quote=quote,snapshot=snapshot,limits=limits,
        distribution=distribution,market=market,sector=sector,assessment_time=assessment_time,
        reduction_fraction=reduction_fraction,cost_assumptions=cost_assumptions,trailing_inputs=trailing)
    return dict(result,distribution_evidence=distribution,liquidity_trap_review=trap,
                broker_memory_status="DERIVED_FROM_SUPPLIED_HISTORY",
                production_eligible=False,execution_eligible=False)
