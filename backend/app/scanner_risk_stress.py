"""Deterministic sensitivity analysis, not forecasts or executable fills."""
from .execution_backtest import _d

def stress_holding(*,quantity,entry,stop,shock_fractions):
    q=_d(quantity,"quantity",positive=True); e=_d(entry,"entry",positive=True); s=_d(stop,"stop",positive=True)
    if q!=int(q) or s>=e: raise ValueError("invalid_risk_geometry")
    planned=q*(e-s)
    scenarios=[]
    for shock in shock_fractions:
        f=_d(shock,"shock")
        if not 0<=f<1: raise ValueError("invalid_shock")
        mark=e*(1-f); loss=q*(e-mark)
        scenarios.append(dict(shock_fraction=str(f),reference_mark=str(mark),gross_loss=str(loss),loss_to_planned_risk=float(loss/planned),stop_breached=mark<=s,exit_fill=None))
    return dict(planned_risk=str(planned),scenarios=scenarios,production_eligible=False,probability=None,limitations=["Caller-selected shocks, no liquidity, fees or verified settlement execution."])
