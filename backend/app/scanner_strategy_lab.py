"""Six-strategy NEPSE research lab with de-duplicated evidence and shared risk gates."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

HORIZONS = {"t_plus_2": 21, "swing": 40, "positional": 60, "investment": 120}
STRATEGIES = {
 "trend_momentum": {"label":"Trend & Momentum Elite","weights":{"trend":25,"relative_strength":20,"wyckoff":15,"volume":15,"smc":10,"liquidity":10,"sector":5},"clusters":{"trend":"price_trend","relative_strength":"relative_strength","wyckoff":"price_structure","volume":"breakout_confirmation","smc":"price_structure","liquidity":"tradability","sector":"sector_context"}},
 "idpat_smart_money": {"label":"IDPAT Smart Money","weights":{"idpat_price_volume":20,"accumulation_distribution":20,"hidden_levels":15,"wyckoff":15,"volume":10,"broker_flow":10,"liquidity":5,"smc":5},"clusters":{"idpat_price_volume":"price_volume","accumulation_distribution":"accumulation_distribution","hidden_levels":"liquidity_structure","wyckoff":"accumulation_distribution","volume":"price_volume","broker_flow":"broker_flow","liquidity":"tradability","smc":"liquidity_structure"}},
 "broker_footprint": {"label":"Broker Footprint Intelligence","weights":{"broker_flow":30,"broker_persistence":20,"price_confirmation":15,"distribution_risk":15,"sector":10,"liquidity":10},"clusters":{"broker_flow":"broker_flow","broker_persistence":"broker_flow","price_confirmation":"price_confirmation","distribution_risk":"distribution_risk","sector":"sector_context","liquidity":"tradability"}},
 "smc_ict_liquidity": {"label":"SMC / ICT Liquidity","weights":{"market_structure":20,"liquidity_sweeps":20,"order_blocks":15,"fvg":10,"premium_discount":10,"volume":10,"relative_strength":5,"liquidity":10},"clusters":{"market_structure":"price_structure","liquidity_sweeps":"liquidity_event","order_blocks":"price_structure","fvg":"price_structure","premium_discount":"range_location","volume":"breakout_confirmation","relative_strength":"relative_strength","liquidity":"tradability"}},
 "hybrid_consensus": {"label":"Hybrid Consensus Master","weights":{"trend":15,"relative_strength":10,"wyckoff":15,"idpat_price_volume":10,"accumulation_distribution":10,"broker_flow":10,"market_structure":10,"liquidity_sweeps":5,"volume":10,"liquidity":5},"clusters":{"trend":"price_trend","relative_strength":"relative_strength","wyckoff":"price_structure","idpat_price_volume":"price_volume","accumulation_distribution":"accumulation_distribution","broker_flow":"broker_flow","market_structure":"price_structure","liquidity_sweeps":"liquidity_event","volume":"price_volume","liquidity":"tradability"}},
 "fundamental_investment": {"label":"Fundamental & Investment Intelligence","weights":{"valuation":20,"earnings_quality":20,"balance_sheet":15,"corporate_actions":10,"sector":10,"relative_strength":10,"trend":5,"liquidity":10},"clusters":{"valuation":"valuation","earnings_quality":"earnings","balance_sheet":"balance_sheet","corporate_actions":"corporate_actions","sector":"sector_context","relative_strength":"relative_strength","trend":"price_trend","liquidity":"tradability"}},
}

def _decimal(value):
 try: result=Decimal(str(value))
 except (InvalidOperation,TypeError,ValueError): return None
 return result if result.is_finite() else None

def _timestamp(value):
 if not isinstance(value,str): return None
 try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
 except ValueError: return None
 if result.tzinfo is None or result.utcoffset() is None: return None
 return result.astimezone(timezone.utc)

def strategy_catalog():
 return {"schema_version":"strategy-lab-1.0.0","strategies":{k:{"label":v["label"],"weights":dict(v["weights"]),"weight_total":sum(v["weights"].values())} for k,v in STRATEGIES.items()},"horizons_minimum_sessions":dict(HORIZONS),"evaluation_policy":"same point-in-time universe, dates, costs, execution assumptions and untouched holdout","production_enabled":False}

def evaluate_strategy(*,strategy_id,symbol,horizon,decision_time,history_sessions,feature_evidence,minimum_coverage=Decimal("0.95")):
 if strategy_id not in STRATEGIES: raise ValueError("unsupported_strategy")
 if horizon not in HORIZONS: raise ValueError("unsupported_horizon")
 cutoff=_timestamp(decision_time)
 if cutoff is None: raise ValueError("decision_time_must_be_timezone_aware")
 if isinstance(history_sessions,bool) or not isinstance(history_sessions,int) or history_sessions<0: raise ValueError("history_sessions_must_be_non_negative_integer")
 threshold=_decimal(minimum_coverage)
 if threshold is None or threshold<=0 or threshold>1: raise ValueError("minimum_coverage_out_of_range")
 if not isinstance(symbol,str) or not symbol.strip(): raise ValueError("symbol_required")
 spec=STRATEGIES[strategy_id]; evidence=feature_evidence if isinstance(feature_evidence,dict) else {}; clusters={}; rejected=[]; raw_covered=Decimal("0")
 for feature,weight in spec["weights"].items():
  item=evidence.get(feature)
  if not isinstance(item,dict): continue
  score=_decimal(item.get("score")); available=_timestamp(item.get("available_at"))
  if item.get("status")!="verified" or score is None or score<0 or score>100 or not item.get("source_id") or not item.get("evidence_id") or available is None or available>cutoff:
   rejected.append(feature); continue
  raw_covered+=Decimal(weight)\n  clusters.setdefault(spec["clusters"][feature],[]).append((feature,weight,score,item))
 covered=Decimal("0"); points=Decimal("0"); accepted={}
 for cluster,members in clusters.items():
  cap=max(Decimal(m[1]) for m in members); selected=max(members,key=lambda m:(m[2],m[1])); feature,_,score,item=selected
  covered+=cap; points+=score*cap
  accepted[cluster]={"selected_feature":feature,"score":str(score),"credited_weight":str(cap),"evidence_id":item["evidence_id"],"source_id":item["source_id"],"cluster_members_observed":[m[0] for m in members]}
 total=Decimal(sum(spec["weights"].values())); coverage=raw_covered/total; score=points/covered if covered else None
 history_ok=history_sessions>=HORIZONS[horizon]; coverage_ok=coverage>=threshold
 status="research_ranked" if history_ok and coverage_ok and not rejected and score is not None else "withheld"
 return {"schema_version":"strategy-lab-1.0.0","strategy_id":strategy_id,"strategy_label":spec["label"],"symbol":symbol,"horizon":horizon,"decision_time":cutoff.isoformat(),"history_sessions":history_sessions,"minimum_history_sessions":HORIZONS[horizon],"history_passed":history_ok,"score":str(score) if score is not None else None,"evidence_coverage_pct":str(coverage*100),"coverage_passed":coverage_ok,"accepted_evidence_clusters":accepted,"rejected_features":rejected,"missing_features":[n for n in spec["weights"] if n not in evidence],"action":"RESEARCH_ONLY_NO_TRADE" if status=="research_ranked" else "NO_TRADE","status":status,"probability":None,"production_enabled":False,"limitations":["Weights are research design assumptions, not calibrated.","Correlated features sharing a cluster receive one capped contribution.","Research ranking is not a BUY instruction; execution and trade-plan gates remain separate.","Compare all strategies on identical point-in-time inputs and realistic costs."]}

def settlement_aware_exit_status(*,stop_triggered,position_quantity,broker_confirmed_sellable_quantity,sellable_from_date,decision_date,current_price,stress_gap_pct=Decimal("0")):
 """Use broker-confirmed sellable quantity/date; do not hard-code settlement rules."""
 for name,value in (("position_quantity",position_quantity),("broker_confirmed_sellable_quantity",broker_confirmed_sellable_quantity)):
  if isinstance(value,bool) or not isinstance(value,int) or value<0: raise ValueError(name+"_invalid")
 if broker_confirmed_sellable_quantity>position_quantity: raise ValueError("sellable_quantity_exceeds_position")
 try:
  today=date.fromisoformat(decision_date); sellable_date=date.fromisoformat(sellable_from_date) if sellable_from_date else None
 except (TypeError,ValueError): raise ValueError("invalid_settlement_date") from None
 price=_decimal(current_price); stress=_decimal(stress_gap_pct)
 if price is None or price<=0 or stress is None or stress<0 or stress>=100: raise ValueError("invalid_price_or_stress_gap")
 pending=position_quantity-broker_confirmed_sellable_quantity
 if not stop_triggered: state="HOLD_OR_MONITOR"
 elif broker_confirmed_sellable_quantity==0: state="EXIT_PENDING"
 elif pending>0: state="PARTIAL_EXIT_POSSIBLE_REMAINDER_PENDING"
 else: state="EXIT_EXECUTABLE_SUBJECT_TO_MARKET_LIQUIDITY"
 stressed=price*(Decimal("1")-stress/Decimal("100"))
 return {"state":state,"stop_triggered":bool(stop_triggered),"position_quantity":position_quantity,"broker_confirmed_sellable_quantity":broker_confirmed_sellable_quantity,"pending_quantity":pending,"sellable_from_date":sellable_date.isoformat() if sellable_date else None,"sellable_date_reached":sellable_date is not None and today>=sellable_date,"current_price":str(price),"stress_gap_pct_assumption":str(stress),"stress_price_scenario_not_forecast":str(stressed),"execution_warning":"A stop trigger is not a guaranteed fill; verify sellable balance, circuit status, bid depth and broker execution.","settlement_calendar_assumed":False}
