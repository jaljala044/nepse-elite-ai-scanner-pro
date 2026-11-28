"""Independent-evidence corporate-action verification and explicit adjustment factors."""
from __future__ import annotations
import hashlib, json, math
from collections import defaultdict
from datetime import date
from typing import Iterable, Mapping

def verify_corporate_actions(*, primary_rows: Iterable[Mapping[str, object]], secondary_rows: Iterable[Mapping[str, object]], previous_closes: Mapping[str, float], approved_conventions: Mapping[str, str]) -> dict:
    grouped=defaultdict(list)
    for row in list(primary_rows)+list(secondary_rows):
        key=(str(row.get("symbol","")).upper(),str(row.get("action_type","")).lower(),str(row.get("ex_date","")),str(row.get("terms_reference","")))
        grouped[key].append(row)
    events=[]; errors=[]
    for (symbol,kind,ex_date,terms),records in sorted(grouped.items()):
        sources={str(r.get("source_id","")) for r in records if r.get("source_id")}
        publishers={str(r.get("publisher_id","")) for r in records if r.get("publisher_id")}
        if len(sources)<2 or len(publishers)<2:
            errors.append({"symbol":symbol,"ex_date":ex_date,"reason":"two_independent_sources_required"}); continue
        signatures={(r.get("ratio_numerator"),r.get("ratio_denominator"),r.get("cash_amount"),r.get("rights_issue_price")) for r in records}
        if len(signatures)!=1:
            errors.append({"symbol":symbol,"ex_date":ex_date,"reason":"corporate_action_terms_conflict"}); continue
        try:
            date.fromisoformat(ex_date); n,d,cash,rights=next(iter(signatures))
            close=float(previous_closes[symbol])
            if not math.isfinite(close) or close<=0: raise ValueError
            if kind in {"bonus","stock_dividend","split","stock_split"}:
                n=float(n); d=float(d)
                if n<=0 or d<=0: raise ValueError
                factor=d/(d+n)
            elif kind in {"cash_dividend","dividend"}:
                cash=float(cash)
                if cash<0 or cash>=close: raise ValueError
                factor=(close-cash)/close
            elif kind in {"rights","rights_issue"}:
                n=float(n); d=float(d); rights=float(rights)
                if n<=0 or d<=0 or rights<0: raise ValueError
                factor=(close*d+rights*n)/(close*(d+n))
            else: raise ValueError("unsupported_action_type")
            if not math.isfinite(factor) or factor<=0: raise ValueError
            if approved_conventions.get(kind)!="THEORETICAL_EX_PRICE_V1": raise ValueError("approved_adjustment_convention_missing")
            event={"symbol":symbol,"action_type":kind,"ex_date":ex_date,"terms_reference":terms,"source_ids":sorted(sources),"publisher_ids":sorted(publishers),"previous_close":close,"adjustment_factor":factor,"adjusted_historical_price_rule":"raw_price * adjustment_factor","factor_method":"THEORETICAL_EX_PRICE_V1","status":"VERIFIED_TERMS_FACTOR_CALCULATED"}
            event["event_sha256"]=hashlib.sha256(json.dumps(event,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
            events.append(event)
        except (KeyError,TypeError,ValueError,OverflowError):
            errors.append({"symbol":symbol,"ex_date":ex_date,"reason":"factor_inputs_or_approved_convention_invalid"})
    return {"status":"VERIFIED" if events and not errors else "REVIEW_REQUIRED","verified_event_count":len(events),"events":events,"errors":errors,"independent_publishers_required":2,"raw_prices_preserved":True,"automatic_adjustment_applied":False,"backtest_admission_allowed":False,"production_enabled":False,"limitations":["Theoretical factors require human-approved action semantics and source independence.","No factor is calculated for unrecognized, conflicting or incomplete terms.","This report does not prove publisher authenticity or entitlement/payment completion."]}
