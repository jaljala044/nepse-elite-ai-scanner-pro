"""Owner-scoped persistent hypothetical paper journal, no trade execution."""
import json
from .private_accounts import _connect
from .part5_paper_journal import freeze_paper_outcome, verify_paper_outcome

def _table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS part5_paper_journal (
        owner TEXT NOT NULL, paper_id TEXT NOT NULL, signal_id TEXT NOT NULL,
        payload TEXT NOT NULL, PRIMARY KEY(owner,paper_id), UNIQUE(owner,signal_id))""")

def store_paper(owner, signal, trade, *, observed_at):
    if not isinstance(owner,str) or not owner.strip():
        raise ValueError("owner required")
    envelope=freeze_paper_outcome(signal,trade,observed_at=observed_at)
    payload=json.dumps(envelope,sort_keys=True,separators=(",",":"),allow_nan=False)
    con=_connect()
    try:
        with con:
            _table(con)
            existing=con.execute("SELECT paper_id,payload FROM part5_paper_journal WHERE owner=? AND signal_id=?",
                (owner,signal["signal_id"])).fetchone()
            if existing:
                if existing!=(envelope["paper_id"],payload):
                    raise ValueError("immutable outcome conflict")
                return {"status":"already_stored","paper_id":existing[0]}
            con.execute("INSERT INTO part5_paper_journal VALUES (?,?,?,?)",
                (owner,envelope["paper_id"],signal["signal_id"],payload))
            return {"status":"stored","paper_id":envelope["paper_id"]}
    finally:
        con.close()

def list_paper(owner):
    if not isinstance(owner,str) or not owner.strip():
        raise ValueError("owner required")
    con=_connect()
    try:
        _table(con)
        rows=con.execute("SELECT payload FROM part5_paper_journal WHERE owner=? ORDER BY paper_id",(owner,)).fetchall()
        envelopes=[json.loads(r[0]) for r in rows]
        if not all(verify_paper_outcome(e) for e in envelopes):
            raise ValueError("invalid stored paper envelope")
        return envelopes
    finally:
        con.close()
