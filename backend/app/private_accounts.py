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
