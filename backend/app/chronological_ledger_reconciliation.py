"""Cross-engine research reconciliation; matching totals are not custody proof."""
from decimal import Decimal
from .chronological_lot_replay import replay_lot_events
from .unified_portfolio_event_engine import run_unified_portfolio_event_ledger
from .corporate_action_trade_plan import _time

def reconcile_chronological_ledger(*,ledger_inputs,events):
    if ledger_inputs.get("initial_holdings"):
        raise ValueError("opening_lot_reconciliation_required")
    now=ledger_inputs["evidence_cutoff"]
    if _time(now).date().isoformat()!=ledger_inputs["as_of_date"]:
        raise ValueError("assessment_date_mismatch")
    unified=run_unified_portfolio_event_ledger(**ledger_inputs)
    chronological=replay_lot_events(events=events,sessions=ledger_inputs["portfolio_sessions"],
        assessment_time=now,initial_cash=ledger_inputs["initial_cash"])
    differences={}
    def compare(key,left,right):
        if abs(Decimal(str(left))-Decimal(str(right)))>Decimal("0.0000001"):
            differences[key]={"unified":str(left),"chronological":str(right)}
    final=unified["equity_curve"][-1]
    compare("cash",final["cash"],chronological["available_cash"])
    compare("sale_receivables",final["sale_receivables"],chronological["sale_receivables"])
    quantities={}
    for lot in chronological["lots"].values():
        quantities[lot["symbol"]]=quantities.get(lot["symbol"],0)+lot["quantity"]
    for symbol in set(quantities)|set(final["holdings"]):
        compare("quantity:"+symbol,final["holdings"].get(symbol,0),quantities.get(symbol,0))
    expected={t["trade_id"]:t for t in unified["executed_trade_scenarios"]}
    observed={e["event_id"]:e for e in events if e["type"] in ("buy","sell")}
    if set(expected)!=set(observed):
        differences["trade_ids"]={"unified":sorted(expected),"chronological":sorted(observed)}
    for tid in set(expected)&set(observed):
        t,e=expected[tid],observed[tid]
        if (t["symbol"],t["side"].lower(),t["date"])!=(e["symbol"],e["type"],e["date"]):
            differences["trade_identity:"+tid]={"unified":t,"chronological":e}
        compare("trade_quantity:"+tid,t["quantity"],e["quantity"])
        if e["type"]=="buy":
            compare("purchase_cost:"+tid,Decimal(str(t["quantity"]))*Decimal(str(t["price"]))+Decimal(str(t["fees"])),e["total_cost"])
        else:
            compare("sale_price:"+tid,t["price"],e["price"])
            compare("sale_fees:"+tid,t["fees"],e["fees"])
    action_ids={a["action_id"] for a in ledger_inputs.get("corporate_actions") or []}
    record_ids={e["action_id"] for e in events if e["type"]=="record"}
    if action_ids!=record_ids:
        differences["action_ids"]={"unified":sorted(action_ids),"chronological":sorted(record_ids)}
    return dict(balance_checks_passed=not differences,differences=differences,
        unified=unified,chronological=chronological,full_accounting_reconciled=False,
        production_eligible=False,limitations=["Ending balances and trade identities only; cost basis, realized P&L, individual entitlement terms and settlement evidence not fully reconciled.",
        "Different intraday settlement assumptions may reject otherwise comparable histories."])
