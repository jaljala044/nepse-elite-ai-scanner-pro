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

    def reconcile(self,portfolio_id,assessment_time):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN")
            rows=db.execute("SELECT action,digest,payload FROM receipt_balance_events WHERE portfolio=?",(portfolio_id,)).fetchall()
            actual=dict(db.execute("SELECT asset,amount FROM receipt_balance_totals WHERE portfolio=?",(portfolio_id,)).fetchall())
        expected={}
        for action,digest,payload in rows:
            if hashlib.sha256(payload.encode()).hexdigest()!=digest:
                raise ValueError("receipt_payload_hash_mismatch")
            data=json.loads(payload)
            if data["entitlement"]["action_id"]!=action:
                raise ValueError("receipt_action_key_mismatch")
            result=review_pending_assets(entitlements=[data["entitlement"]],confirmations=[data["confirmation"]],assessment_time=assessment_time)
            changes={"cash:NPR":result["confirmed_cash_receipt_delta"]}
            changes.update({"shares:"+s:q for s,q in result["confirmed_share_credit_delta"].items()})
            for asset,delta in changes.items():
                expected[asset]=expected.get(asset,Decimal(0))+Decimal(str(delta))
        differences={}
        for asset in sorted(set(expected)|set(actual)):
            want=expected.get(asset,Decimal(0))
            have=Decimal(actual.get(asset,"0"))
            if asset not in expected or asset not in actual or want!=have:
                differences[asset]={"expected":str(want),"actual":str(have)}
        return dict(reconciled=not differences,event_count=len(rows),differences=differences,
            production_eligible=False)

    def migrate_legacy(self,source_path,assessment_time,*,source_frozen=False):
        """Import receipt totals only, never credit an external customer account."""
        if source_frozen is not True:
            raise ValueError("legacy_writer_must_be_retired")
        from pathlib import Path
        uri=Path(source_path).resolve().as_uri()+"?mode=ro"
        with closing(sqlite3.connect(uri,uri=True)) as source, source:
            source.execute("BEGIN")
            rows=source.execute("SELECT portfolio_id,action_id,payload_hash,payload FROM corporate_receipts").fetchall()
        imported=skipped=0
        with closing(sqlite3.connect(self.path,timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            for portfolio,action,digest,payload in rows:
                if not portfolio or hashlib.sha256(payload.encode()).hexdigest()!=digest:
                    raise ValueError("invalid_legacy_receipt")
                data=json.loads(payload)
                if data["entitlement"]["action_id"]!=action:
                    raise ValueError("legacy_action_key_mismatch")
                result=review_pending_assets(entitlements=[data["entitlement"]],confirmations=[data["confirmation"]],assessment_time=assessment_time)
                old=db.execute("SELECT digest FROM receipt_balance_events WHERE portfolio=? AND action=?",(portfolio,action)).fetchone()
                if old:
                    if old[0]!=digest: raise ValueError("conflicting_legacy_receipt")
                    skipped+=1
                    continue
                db.execute("INSERT INTO receipt_balance_events VALUES (?,?,?,?)",(portfolio,action,digest,payload))
                changes={"cash:NPR":result["confirmed_cash_receipt_delta"]}
                changes.update({"shares:"+s:q for s,q in result["confirmed_share_credit_delta"].items()})
                for asset,delta in changes.items():
                    old=db.execute("SELECT amount FROM receipt_balance_totals WHERE portfolio=? AND asset=?",(portfolio,asset)).fetchone()
                    total=Decimal(old[0] if old else "0")+Decimal(str(delta))
                    db.execute("INSERT INTO receipt_balance_totals VALUES (?,?,?) ON CONFLICT(portfolio,asset) DO UPDATE SET amount=excluded.amount",(portfolio,asset,str(total)))
                imported+=1
        return dict(imported=imported,skipped=skipped,production_eligible=False)
