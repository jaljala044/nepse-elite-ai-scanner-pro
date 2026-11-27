"""Matched-fold feature ablation diagnostics using identical OOS execution assumptions.

Each row compares a full-feature baseline with one feature group removed. The upstream
runner must regenerate both variants on the same point-in-time panel and fold.
"""
from decimal import Decimal, InvalidOperation
from app.scanner_strategy_lab import HORIZONS, STRATEGIES

def _d(v):
    try: n=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return n if n.is_finite() else None

def _stats(trades):
    if not isinstance(trades,list): return None
    vals=[]
    for t in trades:
        if not isinstance(t,dict): return None
        ret=_d(t.get("net_return_pct")); day=t.get("exit_date")
        if ret is None or not isinstance(day,str): return None
        vals.append((day,ret))
    vals.sort(key=lambda x:x[0])
    if not vals: return {"trade_count":0,"expectancy_net_pct_per_trade":None,"win_rate_pct":None,"profit_factor":None,"max_drawdown_pct":None}
    gains=sum((r for _,r in vals if r>0),Decimal("0"))
    losses=abs(sum((r for _,r in vals if r<0),Decimal("0")))
    equity=peak=Decimal("1"); maxdd=Decimal("0")
    for _,ret in vals:
        equity*=Decimal("1")+ret/100
        peak=max(peak,equity)
        if peak: maxdd=max(maxdd,(peak-equity)/peak*100)
    wins=sum(1 for _,r in vals if r>0)
    return {"trade_count":len(vals),
        "expectancy_net_pct_per_trade":str(sum((r for _,r in vals),Decimal("0"))/len(vals)),
        "win_rate_pct":str(Decimal(wins)/len(vals)*100),
        "profit_factor":"infinity" if losses==0 and gains>0 else (str(gains/losses) if losses else None),
        "max_drawdown_pct":str(maxdd)}

def compare_feature_ablations(*, ablation_runs, minimum_total_trades=30, minimum_folds=3):
    if not isinstance(ablation_runs,list): raise ValueError("ablation_runs_must_be_list")
    if isinstance(minimum_total_trades,bool) or not isinstance(minimum_total_trades,int) or minimum_total_trades<1:
        raise ValueError("minimum_total_trades_invalid")
    if isinstance(minimum_folds,bool) or not isinstance(minimum_folds,int) or minimum_folds<2:
        raise ValueError("minimum_folds_invalid")
    groups={}; seen=set(); rejected=[]
    for row in ablation_runs:
        if not isinstance(row,dict) or row.get("partition")!="out_of_sample": continue
        strategy,horizon,fold,feature=row.get("strategy_id"),row.get("horizon"),row.get("fold_id"),row.get("feature_group")
        if strategy not in STRATEGIES or horizon not in HORIZONS or not isinstance(fold,str) or not fold or not isinstance(feature,str) or not feature:
            rejected.append({"reason":"invalid_strategy_horizon_fold_or_feature_group"}); continue
        key=(strategy,horizon,feature,fold)
        if key in seen: raise ValueError("duplicate_feature_ablation_fold")
        seen.add(key)
        baseline=row.get("baseline"); ablated=row.get("ablated")
        if not isinstance(baseline,dict) or not isinstance(ablated,dict):
            rejected.append({"strategy_id":strategy,"horizon":horizon,"feature_group":feature,"fold_id":fold,"reason":"variant_missing"}); continue
        # These IDs must be identical so the measured change is attributable to feature removal.
        invariant_fields=("universe_fingerprint","panel_fingerprint","cost_model_id","execution_model_id")
        if any(not baseline.get(k) or baseline.get(k)!=ablated.get(k) for k in invariant_fields):
            rejected.append({"strategy_id":strategy,"horizon":horizon,"feature_group":feature,"fold_id":fold,"reason":"comparison_assumptions_or_panel_mismatch"}); continue
        b=_stats(baseline.get("closed_trades")); a=_stats(ablated.get("closed_trades"))
        if b is None or a is None or b["trade_count"]==0 or a["trade_count"]==0:
            rejected.append({"strategy_id":strategy,"horizon":horizon,"feature_group":feature,"fold_id":fold,"reason":"trade_outcomes_missing_or_invalid"}); continue
        groups.setdefault((strategy,horizon,feature),[]).append({"fold_id":fold,"baseline":b,"ablated":a})
    results=[]
    for (strategy,horizon,feature),folds in sorted(groups.items()):
        folds.sort(key=lambda x:x["fold_id"])
        btotal=sum(x["baseline"]["trade_count"] for x in folds)
        atotal=sum(x["ablated"]["trade_count"] for x in folds)
        breturns=[_d(x["baseline"]["expectancy_net_pct_per_trade"]) for x in folds]
        areturns=[_d(x["ablated"]["expectancy_net_pct_per_trade"]) for x in folds]
        delta=sum(areturns,Decimal("0"))/len(areturns)-sum(breturns,Decimal("0"))/len(breturns)
        fold_deltas=[areturns[i]-breturns[i] for i in range(len(folds))]
        positive=sum(1 for x in fold_deltas if x>0)
        eligible=(len(folds)>=minimum_folds and btotal>=minimum_total_trades and atotal>=minimum_total_trades)
        results.append({"strategy_id":strategy,"horizon":horizon,"feature_group_removed":feature,
            "fold_count":len(folds),"baseline_trade_count":btotal,"ablated_trade_count":atotal,
            "mean_fold_expectancy_delta_net_pct_per_trade":str(delta),
            "folds_improved_by_removal":positive,"folds_tested":len(folds),
            "direction":"removal_improves" if delta>0 else ("removal_harms" if delta<0 else "no_mean_change"),
            "eligible_for_interpretation":eligible,
            "interpretation":"candidate for removal" if eligible and delta>0 else ("feature appears useful" if eligible and delta<0 else "insufficient matched OOS sample"),
            "fold_details":folds})
    return {"schema_version":"nepse-feature-ablation-1.0.0",
        "partition_used":"out_of_sample","minimum_total_trades_per_variant":minimum_total_trades,
        "minimum_folds":minimum_folds,"results":results,"rejected_records":rejected,
        "policy":"compare one feature group at a time on identical panel, universe, costs, execution model and OOS folds; do not infer causality from unmatched variants",
        "limitations":["Feature removal may change selected trades; this comparison measures the resulting portfolio variant, not isolated feature causality.",
            "No statistical significance or future performance probability is claimed.",
            "All folds must be generated chronologically with no training/selection leakage."],
        "performance_claimed":False,"production_enabled":False}
