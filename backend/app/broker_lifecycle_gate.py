"""Conservative lifecycle exclusion, not historical identity certification."""
from datetime import date
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[2]/"data/reference"
def load_lifecycle(root=ROOT):
    def rows(name):
        with (root/name).open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
    return (rows("nepse_equity_lifecycle_coverage_input_2026-11-26.csv"),
            rows("nepse_security_lifecycle_events_2026-11-26.csv"),
            json.loads((root/"nepse_historical_identity_evidence_2026-11-26.json").read_text())["records"])
def lifecycle_reason(security_id,symbol,start,end,evidence):
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    if start>end: raise ValueError("inverted window")
    identities,events,predecessors=evidence
    matching=[r for r in identities if r["security_id"]==security_id and r["symbol"]==symbol and r["instrument_type"]=="equity"]
    # A dated lifecycle event inside the requested window is the most
    # specific exclusion and must be reported before broader predecessor
    # identity uncertainty. This preserves the actual event evidence while
    # still failing closed on windows without a dated event.
    for r in events:
        if r["security_id"]!=security_id and r["symbol"]!=symbol: continue
        if r["event_type"] in {"merger_joint_operations_start","post_merger_shares_listed","post_merger_shares_listed_and_trading_released","trading_suspension_start","trading_resumption","delisting"}:
            if start<=date.fromisoformat(r["event_date"])<=end: return "lifecycle_event_in_window"
    for r in predecessors:
        if r.get("symbol")==symbol and r.get("effective_date_verified") is not True:
            return "unresolved_predecessor_identity"
    if len(matching)!=1: return "missing_or_ambiguous_lifecycle_identity"
    r=matching[0]
    if not r["valid_from"]: return "trading_start_unverified"
    if start<date.fromisoformat(r["valid_from"]): return "before_reported_trading_start"
    if r["valid_to"] and end>date.fromisoformat(r["valid_to"]): return "after_reported_trading_end"
    return "historical_identity_not_certified"
