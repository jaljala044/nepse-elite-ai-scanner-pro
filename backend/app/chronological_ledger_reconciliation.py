"""Cross-engine research reconciliation; matching totals are not custody proof."""
from decimal import Decimal
from .chronological_lot_replay import replay_lot_events
from .unified_portfolio_event_engine import run_unified_portfolio_event_ledger
from .corporate_action_trade_plan import _time

def reconcile_chronological_ledger(*,ledger_inputs,events,opening_lots=None):
    opening={}
    for lot in opening_lots or []:
        q,c=opening.get(lot["symbol"],(Decimal(0),Decimal(0)))
        opening[lot["symbol"]]=(q+Decimal(str(lot["quantity"])),c+Decimal(str(lot["total_cost"])))
    holdings=ledger_inputs.get("initial_holdings") or {}
    if set(opening)!=set(holdings):
        raise ValueError("opening_lot_reconciliation_required")
    for symbol,(q,c) in opening.items():
        h=holdings[symbol]
        if q!=Decimal(str(h["quantity"])) or abs(c-q*Decimal(str(h["average_cost"])))>Decimal("0.0000001"):
            raise ValueError("opening_lot_balance_mismatch:"+symbol)
    now=ledger_inputs["evidence_cutoff"]
    if _time(now).date().isoformat()!=ledger_inputs["as_of_date"]:
        raise ValueError("assessment_date_mismatch")
    unified=run_unified_portfolio_event_ledger(**ledger_inputs)
    chronological=replay_lot_events(events=events,sessions=ledger_inputs["portfolio_sessions"],
        assessment_time=now,initial_cash=ledger_inputs["initial_cash"],opening_lots=opening_lots)
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
    costs={}
    for lot in chronological["lots"].values():
        costs[lot["symbol"]]=costs.get(lot["symbol"],Decimal(0))+Decimal(lot["cost"])
    for symbol in set(costs)|set(unified["ending_cost_basis"]):
        compare("remaining_cost:"+symbol,unified["ending_cost_basis"].get(symbol,0),costs.get(symbol,0))
    for sale in chronological["realized"]:
        t=expected.get(sale["event_id"])
        if t and t["side"].lower()=="sell":
            compare("allocated_cost:"+sale["event_id"],t["allocated_cost"],sale["cost"])
            compare("realized_pnl:"+sale["event_id"],t["realized_pnl"],sale["pnl"])
    action_ids={a["action_id"] for a in ledger_inputs.get("corporate_actions") or []}
    record_ids={e["action_id"] for e in events if e["type"]=="record"}
    if action_ids!=record_ids:
        differences["action_ids"]={"unified":sorted(action_ids),"chronological":sorted(record_ids)}
    # Compare individual action events, not merely net cash or share totals.
    records={e["action_id"]:e for e in events if e["type"]=="record"}
    action_audit={(a["action_id"],a["type"]):a for a in unified["corporate_action_audit"]}
    observed_audit=set()
    for e in events:
        if e["type"] not in ("credit","rights_payment"): continue
        aid=e["action_id"]
        record=records[aid]
        kind=record["action_type"]
        typ="rights_subscription_payment" if e["type"]=="rights_payment" else {"bonus":"bonus_shares","split":"split_conversion","rights":"rights_shares","dividend":"dividend_cash"}[kind]
        key=(aid,typ)
        observed_audit.add(key)
        a=action_audit.get(key)
        if not a:
            differences["missing_action_event:"+aid+":"+typ]="missing_unified_event"
            continue
        if (a["symbol"],a["effective_date"])!=(e["symbol"],e["date"]):
            differences["action_event_identity:"+aid+":"+typ]="symbol_or_date_mismatch"
        if typ=="rights_subscription_payment":
            compare("rights_payment:"+aid,-a["cash_delta"],e["amount"])
            compare("rights_subscription_quantity:"+aid,a["quantity"],sum(e["subscriptions"].values()))
        elif typ=="dividend_cash":
            compare("dividend_cash:"+aid,a["cash_delta"],e["net_amount"])
        elif typ=="split_conversion":
            compare("split_factor:"+aid,a["factor"],record["ratio"])
        else:
            compare("share_credit:"+aid,a["quantity"],sum(e["quantities"].values()))
    for aid,typ in set(action_audit)-observed_audit:
        differences["missing_chronological_event:"+aid+":"+typ]="missing_chronological_event"
    compare("pending_paid_rights",final["rights_paid_at_cost"],chronological["pending_paid_rights"])
    supplied={t["trade_id"]:t for t in ledger_inputs["trades"]}
    for tid in set(observed)&set(supplied):
        if observed[tid]["settlement_date"]!=supplied[tid]["settlement_date"]:
            differences["settlement_date:"+tid]="settlement_date_mismatch"
    for a in unified["corporate_action_entitlements"]:
        if a["action_id"] in chronological["record_entitlements"]:
            compare("record_quantity:"+a["action_id"],a["entitlement_quantity"],chronological["record_entitlements"][a["action_id"]])
        e=records.get(a["action_id"])
        if e and (e["symbol"],e["date"])!=(a["symbol"],a["record_date"]):
            differences["record_identity:"+a["action_id"]]="symbol_or_date_mismatch"
    return dict(balance_checks_passed=not differences,differences=differences,
        unified=unified,chronological=chronological,full_accounting_reconciled=False,
        production_eligible=False,limitations=["Aggregate average-cost versus explicit lot allocation differences are reported, not treated as proof of error. Individual credit events compared; record-date quantities and supplied settlement dates compared, but custody evidence not independently reconciled. Gross versus net dividend differences are reported.",
        "Different intraday settlement assumptions may reject otherwise comparable histories."])
