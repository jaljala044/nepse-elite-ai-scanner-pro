"""Conservative composition of evidence trade plan, signal and execution gates."""
from __future__ import annotations
from decimal import Decimal
from app.scanner_trade_plan import build_evidence_backed_trade_plan
from app.scanner_signal_qualification import qualify_scanner_signal
from app.scanner_risk_engine import calculate_risk_limited_position, evaluate_execution_constraints

def build_research_decision(*, symbol,horizon,decision_time,component_evidence,
    gate_evidence,levels,round_trip_cost_pct,slippage_pct,execution_snapshot,
    risk_inputs=None):
    plan=build_evidence_backed_trade_plan(symbol=symbol,horizon=horizon,
        decision_time=decision_time,levels=levels,
        round_trip_cost_pct=round_trip_cost_pct,slippage_pct=slippage_pct)
    execution={}
    if isinstance(execution_snapshot,dict):
        execution=evaluate_execution_constraints(**execution_snapshot)
    else:
        execution={"status":"blocked","failures":["execution_snapshot_missing"],"production_enabled":False}
    gates=dict(gate_evidence) if isinstance(gate_evidence,dict) else {}
    if execution.get("status")!="execution_checks_passed_for_human_review":
        gates.pop("execution",None)
    trade_plan={
        "entry":plan["entry"]["high"] if plan.get("entry") else None,
        "stop":plan["stop"]["price"] if plan.get("stop") else None,
        "T1":plan["targets"]["T1"]["price"] if plan.get("targets",{}).get("T1") else None,
        "T2":plan["targets"]["T2"]["price"] if plan.get("targets",{}).get("T2") else None,
        "T3":plan["targets"]["T3"]["price"] if plan.get("targets",{}).get("T3") else None,
        "round_trip_cost_pct":round_trip_cost_pct,"slippage_pct":slippage_pct,
        "invalidation":"Structural stop from verified source evidence",
    }
    qualification=qualify_scanner_signal(symbol=symbol,decision_time=decision_time,
        horizon=horizon,component_evidence=component_evidence,gates=gates,
        trade_plan=trade_plan)
    if plan.get("status")!="research_plan_ready_for_human_review":
        qualification["action"]="NO_TRADE"
        qualification["status"]="not_qualified"
        qualification["trade_plan_errors"]=list(qualification.get("trade_plan_errors",[]))+plan.get("errors",[])
    if execution.get("status")!="execution_checks_passed_for_human_review":
        qualification["action"]="NO_TRADE"
        qualification["status"]="not_qualified"
    sizing={"status":"not_attempted","quantity":0,"reason":"research_signal_or_execution_gate_not_passed"}
    if qualification.get("action")=="BUY" and isinstance(risk_inputs,dict):
        params=dict(risk_inputs)
        params.setdefault("entry_price",trade_plan["entry"])
        params.setdefault("structural_stop",trade_plan["stop"])
        params.setdefault("round_trip_cost_pct",round_trip_cost_pct)
        params.setdefault("slippage_pct",slippage_pct)
        sizing=calculate_risk_limited_position(**params)
        if sizing.get("status")!="sized_for_human_review":
            qualification["action"]="NO_TRADE"
            qualification["status"]="not_qualified"
    elif qualification.get("action")=="BUY":
        sizing={"status":"blocked","quantity":0,"reason":"risk_sizing_inputs_missing"}
        qualification["action"]="NO_TRADE"
        qualification["status"]="not_qualified"
    return {
        "schema_version":"nepse-research-decision-1.0.0","symbol":symbol.upper(),
        "horizon":horizon,"decision_time":decision_time,
        "action":"RESEARCH_BUY_FOR_HUMAN_REVIEW" if qualification["action"]=="BUY" else "NO_TRADE",
        "qualification":qualification,"trade_plan":plan,"execution_check":execution,
        "position_sizing":sizing,"production_enabled":False,
        "warnings":["A passing execution snapshot is not a guaranteed fill; refresh all market and broker facts before any order.","A research BUY is not an exchange order or personalized investment advice.","Settlement sellable quantity and date must be independently broker-confirmed."]
    }
