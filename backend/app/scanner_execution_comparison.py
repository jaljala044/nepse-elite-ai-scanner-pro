"""Compare caller-supplied frozen research signals under identical scenario inputs."""
from .execution_backtest import simulate_execution_scenario, aggregate_execution_scenarios

def compare_scanners(candidates,scenario_inputs):
    if not candidates: raise ValueError("missing_scanners")
    results={}
    for name,signals in candidates.items():
        seen=set(); scenarios=[]
        for signal in signals:
            key=(signal["symbol"],signal["horizon"],signal["details"]["decision_date"])
            if key in seen: raise ValueError("duplicate_decision")
            seen.add(key)
            if key not in scenario_inputs:
                scenarios.append(dict(status="unavailable",reason="missing_common_scenario_inputs"))
                continue
            scenarios.append(simulate_execution_scenario(signal=signal,**scenario_inputs[key]))
        results[name]=dict(summary=aggregate_execution_scenarios(scenarios),scenarios=scenarios)
    return dict(scanners=results,production_eligible=False,winner=None,
        limitations=["Caller-supplied frozen candidates, not automatically generated IDPAT signals. Different candidate coverage and selection may prevent fair comparison; no portfolio simulation or calibrated ranking."])
