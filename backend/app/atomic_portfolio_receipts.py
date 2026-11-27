"""Research snapshot store; not a custody or broker account."""
import sqlite3,json,hashlib
from decimal import Decimal
from .pending_corporate_assets import review_pending_assets

class AtomicPortfolioReceipts:
    def __init__(self,path):
        self.path=path
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS research_portfolios (id TEXT PRIMARY KEY, cash TEXT NOT NULL, shares TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS research_postings (portfolio_id TEXT, action_id TEXT, digest TEXT NOT NULL, PRIMARY KEY(portfolio_id,action_id))")
            db.execute("CREATE TABLE IF NOT EXISTS research_costs (portfolio_id TEXT PRIMARY KEY, costs TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS research_rights (portfolio_id TEXT, action_id TEXT, digest TEXT, amount TEXT, PRIMARY KEY(portfolio_id,action_id))")
    def initialize(self,portfolio_id,cash,shares,costs=None):
        cash=Decimal(str(cash))
        if not portfolio_id or not cash.is_finite() or cash<0 or any(type(q) is not int or q<0 for q in shares.values()):
            raise ValueError("invalid_opening_snapshot")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO research_portfolios VALUES (?,?,?)",(portfolio_id,str(cash),json.dumps(shares,sort_keys=True)))
            if costs is not None:
                if set(costs)!=set(shares) or any(not Decimal(str(c)).is_finite() or Decimal(str(c))<0 for c in costs.values()):
                    raise ValueError("invalid_opening_costs")
                db.execute("INSERT INTO research_costs VALUES (?,?)",(portfolio_id,json.dumps({s:str(Decimal(str(c))) for s,c in costs.items()})))
    def pay_rights(self,*,portfolio_id,entitlement,assessment_time):
        result=review_pending_assets(entitlements=[entitlement],confirmations=[],assessment_time=assessment_time)
        amount=Decimal(result["pending_paid_rights_at_cost"])
        if entitlement["action_type"]!="rights" or amount<=0: raise ValueError("invalid_rights_payment")
        digest=hashlib.sha256(json.dumps(entitlement,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        aid=entitlement["action_id"]
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT cash FROM research_portfolios WHERE id=?",(portfolio_id,)).fetchone()
            if row is None: raise ValueError("unknown_portfolio")
            prior=db.execute("SELECT digest FROM research_rights WHERE portfolio_id=? AND action_id=?",(portfolio_id,aid)).fetchone()
            if prior:
                if prior[0]!=digest: raise ValueError("conflicting_rights_payment")
                return False
            if not db.execute("SELECT 1 FROM research_costs WHERE portfolio_id=?",(portfolio_id,)).fetchone(): raise ValueError("opening_costs_required")
            if Decimal(row[0])<amount: raise ValueError("insufficient_rights_cash")
            db.execute("INSERT INTO research_rights VALUES (?,?,?,?)",(portfolio_id,aid,digest,str(amount)))
            db.execute("UPDATE research_portfolios SET cash=? WHERE id=?",(str(Decimal(row[0])-amount),portfolio_id))
            return True
    def post(self,*,portfolio_id,entitlement,confirmation,assessment_time):
        result=review_pending_assets(entitlements=[entitlement],confirmations=[confirmation],assessment_time=assessment_time)
        cash=Decimal(result["confirmed_cash_receipt_delta"])
        shares=result["confirmed_share_credit_delta"]
        if cash<0 or any(q<0 for q in shares.values()) or (not cash and not any(shares.values())):
            raise ValueError("no_confirmed_positive_receipt")
        # Rights credits require a matching prior atomic payment.
        if entitlement.get("action_type") not in ("bonus","dividend","rights"):
            raise ValueError("unsupported_atomic_receipt_type")
        aid=entitlement["action_id"]
        digest=hashlib.sha256(json.dumps([entitlement,confirmation],sort_keys=True,separators=(",",":")).encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT cash,shares FROM research_portfolios WHERE id=?",(portfolio_id,)).fetchone()
            if row is None: raise ValueError("unknown_portfolio")
            prior=db.execute("SELECT digest FROM research_postings WHERE portfolio_id=? AND action_id=?",(portfolio_id,aid)).fetchone()
            if prior:
                if prior[0]!=digest: raise ValueError("conflicting_receipt")
                return dict(applied=False,production_eligible=False)
            holdings=json.loads(row[1])
            if entitlement["action_type"]=="rights":
                payment=db.execute("SELECT digest,amount FROM research_rights WHERE portfolio_id=? AND action_id=?",(portfolio_id,aid)).fetchone()
                expected=hashlib.sha256(json.dumps(entitlement,sort_keys=True,separators=(",",":")).encode()).hexdigest()
                if not payment or payment[0]!=expected: raise ValueError("matching_rights_payment_required")
                costrow=db.execute("SELECT costs FROM research_costs WHERE portfolio_id=?",(portfolio_id,)).fetchone()
                if not costrow: raise ValueError("opening_costs_required")
                costs=json.loads(costrow[0])
                symbol=entitlement["symbol"]
                costs[symbol]=str(Decimal(costs.get(symbol,"0"))+Decimal(payment[1]))
                db.execute("UPDATE research_costs SET costs=? WHERE portfolio_id=?",(json.dumps(costs,sort_keys=True),portfolio_id))
            for symbol,q in shares.items(): holdings[symbol]=holdings.get(symbol,0)+q
            db.execute("INSERT INTO research_postings VALUES (?,?,?)",(portfolio_id,aid,digest))
            db.execute("UPDATE research_portfolios SET cash=?,shares=? WHERE id=?",(str(Decimal(row[0])+cash),json.dumps(holdings,sort_keys=True),portfolio_id))
            return dict(applied=True,production_eligible=False)
