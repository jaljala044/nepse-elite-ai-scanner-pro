"""Research receipt journal; deltas are not applied to customer balances."""
import sqlite3
import hashlib
import json
from contextlib import closing
from .pending_corporate_assets import review_pending_assets

class CorporateReceiptJournal:
    def __init__(self,path):
        self.path=str(path)
        if self.path==":memory:": raise ValueError("persistent_path_required")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS corporate_receipts (
                portfolio_id TEXT NOT NULL, action_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(portfolio_id,action_id))""")

    def record(self,*,portfolio_id,entitlement,confirmation,assessment_time):
        if not isinstance(portfolio_id,str) or not portfolio_id.strip():
            raise ValueError("portfolio_id_required")
        review=review_pending_assets(entitlements=[entitlement],confirmations=[confirmation],
            assessment_time=assessment_time)
        payload=json.dumps(dict(entitlement=entitlement,confirmation=confirmation),sort_keys=True,
            separators=(",",":"),allow_nan=False)
        digest=hashlib.sha256(payload.encode()).hexdigest()
        aid=entitlement["action_id"]
        with closing(sqlite3.connect(self.path,timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            old=db.execute("SELECT payload_hash FROM corporate_receipts WHERE portfolio_id=? AND action_id=?",
                (portfolio_id,aid)).fetchone()
            if old:
                if old[0]!=digest: raise ValueError("conflicting_receipt_replay")
                return dict(status="ALREADY_RECORDED",payload_hash=digest,new_cash_delta="0",new_share_delta={},production_eligible=False)
            db.execute("INSERT INTO corporate_receipts VALUES (?,?,?,?)",(portfolio_id,aid,digest,payload))
        return dict(status="RECORDED",payload_hash=digest,
            new_cash_delta=review["confirmed_cash_receipt_delta"],
            new_share_delta=review["confirmed_share_credit_delta"],production_eligible=False)

    def history(self,portfolio_id):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute("SELECT payload_hash,payload FROM corporate_receipts WHERE portfolio_id=? ORDER BY rowid",(portfolio_id,)).fetchall()
        return [dict(payload_hash=h,**json.loads(p)) for h,p in rows]
