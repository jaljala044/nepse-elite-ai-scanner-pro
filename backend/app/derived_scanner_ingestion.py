"""Pinned archive ingestion; integrity is not historical certification."""
import csv
import io
import hashlib
from .scanner_archive_audit import audit_archive

RELEASE="4255cc293a347857ac77c04a947beb784203062f"
LOOKBACK={"T+2":21,"swing":61,"positional":127,"investment":253}

def load_candidate(symbol,manifest_bytes,price_bytes,release):
    if release!=RELEASE: raise ValueError("unexpected_release")
    matches=[r for r in csv.DictReader(io.StringIO(manifest_bytes.decode())) if r["symbol"]==symbol]
    if len(matches)!=1: raise ValueError("manifest_identity")
    m=matches[0]
    digest=hashlib.sha1(b"blob "+str(len(price_bytes)).encode()+b"\0"+price_bytes).hexdigest()
    if digest!=m["derived_blob_sha"]: raise ValueError("blob_mismatch")
    text=price_bytes.decode()
    audit=audit_archive(text)
    if audit["rows"]!=int(m["rows"]): raise ValueError("row_count_mismatch")
    return dict(symbol=symbol,release=release,blob=digest,audit=audit,rows=list(csv.DictReader(io.StringIO(text))),production_eligible=False)

def horizon_eligibility(*,horizon,expected_sessions,verified_bars,benchmark_dates,broker_dates,action_basis_verified):
    n=LOOKBACK[horizon]
    days=list(expected_sessions)
    if days!=sorted(set(days)): raise ValueError("invalid_sessions")
    window=days[-n:]
    reasons=[]
    if len(window)<n: reasons.append("insufficient_sessions")
    if set(window)-set(verified_bars): reasons.append("missing_verified_bars")
    if set(window)-set(benchmark_dates): reasons.append("missing_benchmark")
    if len(window)<5 or set(window[-5:])-set(broker_dates): reasons.append("missing_recent_broker")
    if action_basis_verified is not True: reasons.append("unverified_action_basis")
    return dict(horizon=horizon,missing=reasons,candidate_ready=not reasons,production_eligible=False)
