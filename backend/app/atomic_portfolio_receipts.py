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
    def initialize(self,portfolio_id,cash,shares):
        cash=Decimal(str(cash))
        if not portfolio_id or not cash.is_finite() or cash<0 or any(type(q) is not int or q<0 for q in shares.values()):
            raise ValueError("invalid_opening_snapshot")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO research_portfolios VALUES (?,?,?)",(portfolio_id,str(cash),json.dumps(shares,sort_keys=True)))
    def post(self,*,portfolio_id,entitlement,confirmation,assessment_time):
        result=review_pending_assets(entitlements=[entitlement],confirmations=[confirmation],assessment_time=assessment_time)
        cash=Decimal(result["confirmed_cash_receipt_delta"])
        shares=result["confirmed_share_credit_delta"]
        if cash<0 or any(q<0 for q in shares.values()) or (not cash and not any(shares.values())):
            raise ValueError("no_confirmed_positive_receipt")
        # Rights cost and acquisition lot updates require a separate atomic payment workflow.
        if entitlement.get("action_type") not in ("bonus","dividend"):
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
            for symbol,q in shares.items(): holdings[symbol]=holdings.get(symbol,0)+q
            db.execute("INSERT INTO research_postings VALUES (?,?,?)",(portfolio_id,aid,digest))
            db.execute("UPDATE research_portfolios SET cash=?,shares=? WHERE id=?",(str(Decimal(row[0])+cash),json.dumps(holdings,sort_keys=True),portfolio_id))
            return dict(applied=True,production_eligible=False)
