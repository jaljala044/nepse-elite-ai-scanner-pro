"""Research reconciliation for action-free ledger replays."""
from decimal import Decimal
from .portfolio_lot_accounting import reconcile_lots
from .unified_portfolio_event_engine import run_unified_portfolio_event_ledger

def reconcile_ledger_lots(*,ledger_inputs,lots,sales,marks):
    if ledger_inputs.get("corporate_actions"):
        raise ValueError("corporate_action_lot_reconciliation_required")
    ledger=run_unified_portfolio_event_ledger(**ledger_inputs)
    executed=ledger["executed_trade_scenarios"]
    actual={t["trade_id"]:t for t in executed if t["side"]=="SELL"}
    if len(sales)!=len(actual) or {s["sale_id"] for s in sales}!=set(actual):
        raise ValueError("sale_ledger_coverage_mismatch")
    for s in sales:
        t=actual[s["sale_id"]]
        if s["symbol"]!=t["symbol"] or s["trade_date"]!=t["date"] or any(
            Decimal(str(s[k]))!=Decimal(str(t[k])) for k in ("quantity","price","fees")):
            raise ValueError("sale_ledger_value_mismatch")
    # Match each purchase to its actual executed quantity and fee-inclusive cost.
    buys={t["trade_id"]:t for t in executed if t["side"]=="BUY"}
    trades={t["trade_id"]:t for t in ledger_inputs["trades"]}
    opening={}
    for lot in lots:
        if lot["lot_id"] in buys:
            t=buys[lot["lot_id"]]
            if (lot["symbol"]!=t["symbol"] or lot["acquisition_date"]!=t["date"]
                or lot["settlement_date"]!=trades[lot["lot_id"]]["settlement_date"]
                or Decimal(str(lot["quantity"]))!=Decimal(str(t["quantity"]))
                or Decimal(str(lot["total_cost"]))!=Decimal(str(t["quantity"]))*Decimal(str(t["price"]))+Decimal(str(t["fees"]))):
                raise ValueError("purchase_lot_mismatch")
        else:
            if lot["settlement_date"]>ledger_inputs["portfolio_sessions"][0]:
                raise ValueError("opening_lot_not_settled")
            q,c=opening.get(lot["symbol"],(Decimal(0),Decimal(0)))
            opening[lot["symbol"]]=(q+Decimal(str(lot["quantity"])),c+Decimal(str(lot["total_cost"])))
    if not set(buys)<= {l["lot_id"] for l in lots}: raise ValueError("purchase_lot_missing")
    expected={s:(Decimal(str(v["quantity"])),Decimal(str(v["quantity"]))*Decimal(str(v["average_cost"])))
              for s,v in ledger_inputs["initial_holdings"].items() if v["quantity"]}
    if opening!=expected: raise ValueError("opening_lot_mismatch")
    result=reconcile_lots(lots=lots,sales=sales,marks=marks,assessment_time=ledger_inputs["evidence_cutoff"])
    quantities={}
    for lot in result["remaining_lots"]:
        if lot["settled"]: quantities[lot["symbol"]]=quantities.get(lot["symbol"],0)+lot["quantity"]
    if quantities!=ledger["equity_curve"][-1]["holdings"]: raise ValueError("ending_quantity_mismatch")
    return dict(ledger=ledger,lot_accounting=result,quantity_reconciled=True,production_eligible=False,
        limitations=["Explicit allocations may differ from aggregate average cost; no statutory tax calculation.",
                     "Corporate actions withheld until lot entitlement reconciliation is implemented."])
