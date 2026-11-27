"""Research-only persistent receipt balance projection, not a full portfolio ledger."""
from contextlib import closing
from decimal import Decimal
import sqlite3
import hashlib
import json
from .pending_corporate_assets import review_pending_assets

class ReceiptBalanceLedger:
    def __init__(self,path):
        self.path=str(path)
        if self.path==":memory:": raise ValueError("persistent_path_required")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS receipt_balance_events (portfolio TEXT, action TEXT, digest TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(portfolio,action))")
            db.execute("CREATE TABLE IF NOT EXISTS receipt_balance_totals (portfolio TEXT, asset TEXT, amount TEXT NOT NULL, PRIMARY KEY(portfolio,asset))")
    def apply(self,*,portfolio_id,entitlement,confirmation,assessment_time):
        if not isinstance(portfolio_id,str) or not portfolio_id.strip(): raise ValueError("portfolio_required")
        result=review_pending_assets(entitlements=[entitlement],confirmations=[confirmation],assessment_time=assessment_time)
        payload=json.dumps(dict(entitlement=entitlement,confirmation=confirmation),sort_keys=True,separators=(",",":"),allow_nan=False)
        digest=hashlib.sha256(payload.encode()).hexdigest()
        with closing(sqlite3.connect(self.path,timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            key=(portfolio_id,entitlement["action_id"])
            old=db.execute("SELECT digest FROM receipt_balance_events WHERE portfolio=? AND action=?",key).fetchone()
            if old:
                if old[0]!=digest: raise ValueError("conflicting_receipt_replay")
                return {"status":"ALREADY_RECORDED","production_eligible":False}
            db.execute("INSERT INTO receipt_balance_events VALUES (?,?,?,?)",(*key,digest,payload))
            changes={"cash:NPR":result["confirmed_cash_receipt_delta"]}
            changes.update({"shares:"+s:q for s,q in result["confirmed_share_credit_delta"].items()})
            for asset,delta in changes.items():
                old=db.execute("SELECT amount FROM receipt_balance_totals WHERE portfolio=? AND asset=?",(portfolio_id,asset)).fetchone()
                total=Decimal(old[0] if old else "0")+Decimal(str(delta))
                db.execute("INSERT INTO receipt_balance_totals VALUES (?,?,?) ON CONFLICT(portfolio,asset) DO UPDATE SET amount=excluded.amount",(portfolio_id,asset,str(total)))
        return {"status":"RECORDED","production_eligible":False}
    def balances(self,portfolio_id):
        with closing(sqlite3.connect(self.path)) as db:
            return dict(db.execute("SELECT asset,amount FROM receipt_balance_totals WHERE portfolio=?",(portfolio_id,)).fetchall())
