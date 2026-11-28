"""Private account records for a trusted reverse proxy authenticated deployment.
No self-issued user identifiers are accepted. Proxy must strip incoming identity headers."""
import os
import hmac
import sqlite3
import json
import re
from pathlib import Path
from fastapi import HTTPException, Request

def principal(request: Request):
    secret=os.getenv("NEPSE_PROXY_SECRET","")
    provided=request.headers.get("x-nepse-proxy-secret","")
    subject=request.headers.get("x-nepse-subject","")
    if len(secret)<32 or not hmac.compare_digest(secret.encode(),provided.encode()):
        raise HTTPException(401,"Authentication required")
    if not re.fullmatch(r"[A-Za-z0-9_.:@-]{1,200}",subject):
        raise HTTPException(401,"Verified subject required")
    return subject

def _connect():
    path=Path(os.getenv("NEPSE_PRIVATE_DB","private/accounts.sqlite3"))
    path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path)
    c.execute("CREATE TABLE IF NOT EXISTS watchlists (owner TEXT NOT NULL, symbol TEXT NOT NULL, PRIMARY KEY(owner,symbol))")
    c.execute("CREATE TABLE IF NOT EXISTS price_alerts (owner TEXT NOT NULL, symbol TEXT NOT NULL, direction TEXT NOT NULL, threshold TEXT NOT NULL, PRIMARY KEY(owner,symbol,direction,threshold))")
    c.execute("CREATE TABLE IF NOT EXISTS price_alert_events (owner TEXT NOT NULL, symbol TEXT NOT NULL, direction TEXT NOT NULL, threshold TEXT NOT NULL, session TEXT NOT NULL, PRIMARY KEY(owner,symbol,direction,threshold,session))")
    return c

def watchlist(owner):
    with _connect() as c:
        return [r[0] for r in c.execute("SELECT symbol FROM watchlists WHERE owner=? ORDER BY symbol",(owner,))]

def set_watchlist(owner,symbols):
    if len(symbols)>300 or any(not isinstance(s,str) or not re.fullmatch(r"[A-Z0-9]{1,20}",s) for s in symbols):
        raise ValueError("Invalid watchlist")
    with _connect() as c:
        c.execute("DELETE FROM watchlists WHERE owner=?",(owner,))
        c.executemany("INSERT INTO watchlists VALUES (?,?)",[(owner,s) for s in sorted(set(symbols))])
    return watchlist(owner)

def normalize_alert(symbol, direction, threshold):
    from decimal import Decimal, InvalidOperation
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z0-9]{1,20}",symbol) or direction not in ("above","below"):
        raise ValueError("Invalid alert")
    try:
        p=Decimal(str(threshold))
        if not p.is_finite() or p<=0 or p>100000000 or p!=p.quantize(Decimal("0.01")):
            raise ValueError("Invalid threshold")
        return symbol,direction,format(p,".2f")
    except (InvalidOperation,TypeError):
        raise ValueError("Invalid threshold") from None

def list_alerts(owner):
    with _connect() as c:
        return [{"symbol":s,"direction":d,"threshold":p} for s,d,p in c.execute("SELECT symbol,direction,threshold FROM price_alerts WHERE owner=? ORDER BY symbol,direction,threshold",(owner,))]

def add_alert(owner,symbol,direction,threshold):
    key=normalize_alert(symbol,direction,threshold)
    with _connect() as c:
        c.execute("BEGIN IMMEDIATE")
        exists=c.execute("SELECT 1 FROM price_alerts WHERE owner=? AND symbol=? AND direction=? AND threshold=?",(owner,*key)).fetchone()
        if not exists and c.execute("SELECT COUNT(*) FROM price_alerts WHERE owner=?",(owner,)).fetchone()[0]>=300:
            raise ValueError("Alert limit reached")
        c.execute("INSERT OR IGNORE INTO price_alerts VALUES (?,?,?,?)",(owner,*key))
    return list_alerts(owner)

def delete_alert(owner,symbol,direction,threshold):
    key=normalize_alert(symbol,direction,threshold)
    with _connect() as c:
        c.execute("DELETE FROM price_alerts WHERE owner=? AND symbol=? AND direction=? AND threshold=?",(owner,*key))
    return list_alerts(owner)

def evaluate_price_alerts(owner, observation):
    """Internal research evaluation only; upstream must attest provenance.
    Never expose this as a client-supplied price or live delivery endpoint.
    """
    from datetime import date
    from decimal import Decimal, InvalidOperation
    if not isinstance(observation,dict) or observation.get("source_validation_status")!="verified" or observation.get("finality_status")!="final":
        return []
    symbol=observation.get("symbol")
    session=observation.get("session_date")
    digest=observation.get("source_payload_sha256")
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z0-9]{1,20}",symbol) or not isinstance(digest,str) or not re.fullmatch(r"[a-fA-F0-9]{64}",digest) or not isinstance(observation.get("source_id"),str) or not observation["source_id"].strip():
        return []
    try:
        if date.fromisoformat(session).isoformat()!=session:
            return []
        close=Decimal(str(observation.get("close")))
        if not close.is_finite() or close<=0:
            return []
    except (ValueError,TypeError,InvalidOperation):
        return []
    events=[]
    with _connect() as c:
        c.execute("BEGIN IMMEDIATE")
        for direction,threshold in c.execute("SELECT direction,threshold FROM price_alerts WHERE owner=? AND symbol=?",(owner,symbol)).fetchall():
            p=Decimal(threshold)
            if not (close>=p if direction=="above" else close<=p):
                continue
            result=c.execute("INSERT OR IGNORE INTO price_alert_events VALUES (?,?,?,?,?)",(owner,symbol,direction,threshold,session))
            if result.rowcount==1:
                events.append({"symbol":symbol,"direction":direction,"threshold":threshold,"session":session,"close":str(close),"delivery_enabled":False})
    return events
