"""Execute bounded, predeclared execution sensitivity scenarios, research only."""
from .historical_trade_simulation import simulate
from .part5_research_dashboard import stress_report

def run_execution_sweep(symbol, rows, observations, *, base, variants):
    if not isinstance(variants,dict) or not 1<=len(variants)<=20 or "baseline" in variants:
        raise ValueError("1-20 named variants required")
    allowed={"stop_fraction","target_fraction","max_participation","holding_sessions","quantity","costs"}
    configurations={"baseline":dict(base)}
    for name,changes in variants.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(changes,dict) or set(changes)-allowed:
            raise ValueError("invalid scenario override")
        config={**base,**changes}
        if "costs" in changes:
            config["costs"]={**(base.get("costs") or {}),**changes["costs"]}
        configurations[name]=config
    runs={name:simulate(symbol,rows,observations,**config) for name,config in configurations.items()}
    summary=stress_report({name:run["trades"] for name,run in runs.items()},initial_capital=base["initial_capital"])
    return {**summary,"runs":runs,"parameters":{name:{k:config.get(k) for k in sorted(allowed)} for name,config in configurations.items()},
            "limitations":["Fixed observations; not a model retraining or parameter optimization.","Unresolved trades excluded from closed-trade statistics; inspect each run."]}
