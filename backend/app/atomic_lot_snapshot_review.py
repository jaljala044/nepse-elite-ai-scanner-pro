"""Read-only research reconciliation; does not mutate acquisition lots."""
import sqlite3,json
from decimal import Decimal
from .portfolio_lot_accounting import _qty,_amount
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time

def review_atomic_lots(*,path,portfolio_id,lots,assessment_time):
    now=_time(assessment_time)
    quantities={}
    costs={}
    seen=set()
    for lot in lots:
        _available(lot,now,"lot")
        lid=lot["lot_id"]
        if not lid or lid in seen: raise ValueError("duplicate_lot")
        seen.add(lid)
        symbol=lot["symbol"]
        quantities[symbol]=quantities.get(symbol,0)+_qty(lot["quantity"])
        costs[symbol]=costs.get(symbol,Decimal(0))+_amount(lot["total_cost"])
    with sqlite3.connect(path) as db:
        db.execute("BEGIN")
        row=db.execute("SELECT shares FROM research_portfolios WHERE id=?",(portfolio_id,)).fetchone()
        costrow=db.execute("SELECT costs FROM research_costs WHERE portfolio_id=?",(portfolio_id,)).fetchone()
        if not row or not costrow: raise ValueError("portfolio_cost_snapshot_required")
        expected=json.loads(row[0])
        expected_cost=json.loads(costrow[0])
    differences={}
    for s in set(expected)|set(quantities)|set(costs)|set(expected_cost):
        if expected.get(s,0)!=quantities.get(s,0) or Decimal(expected_cost.get(s,"0"))!=costs.get(s,Decimal(0)):
            differences[s]="quantity_or_cost_mismatch"
    return dict(balance_checks_passed=not differences,differences=differences,production_eligible=False)
