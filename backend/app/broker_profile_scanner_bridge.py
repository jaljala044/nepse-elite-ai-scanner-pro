"""Point-in-time descriptive broker breadth; never promotes flow to a score."""
from datetime import datetime,date
from decimal import Decimal,InvalidOperation
POLICY="complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only"

def build_broker_profile_scanner_context(snapshot,*,decision_time,expected_security_ids):
    cutoff=datetime.fromisoformat(decision_time)
    if cutoff.tzinfo is None: raise ValueError("timezone required")
    base={"status":"withheld","score_eligible":False,"securities":{},"rejected_profile_rows":0}
    if not isinstance(snapshot,dict) or snapshot.get("policy")!=POLICY:
        return dict(base,reason="rolling_profile_policy_unrecognized")
    try:
        ts=datetime.fromisoformat(snapshot["as_of_timestamp"])
        day=date.fromisoformat(snapshot["as_of_date"])
        if ts.tzinfo is None or day!=ts.date(): raise ValueError()
    except (ValueError,TypeError,KeyError):
        return dict(base,reason="invalid_snapshot_timestamp")
    if ts>cutoff: return dict(base,reason="rolling_profile_is_after_scanner_decision_time")
    expected=set(expected_security_ids)
    groups={};rejected=0
    for row in snapshot.get("profiles",[]):
        if not isinstance(row,dict): rejected+=1;continue
        sec,window,broker=(row.get(k) for k in ("security_id","window","broker_id"))
        if sec not in expected or not isinstance(window,str) or not isinstance(broker,str) or not broker:
            rejected+=1;continue
        group=groups.setdefault((sec,window),{"brokers":{},"duplicate":False})
        try:
            counts=[row[k] for k in ("requested_sessions","expected_sessions","complete_source_sessions")]
            valid=(row.get("status")=="descriptive_only" and Decimal(str(row["coverage_ratio"]))==1
                   and all(type(n) is int and n>0 for n in counts) and len(set(counts))==1
                   and row.get("directional_summary") in {"net_buy_dominant","net_sell_dominant","balanced"})
        except (KeyError,InvalidOperation,TypeError,ValueError): valid=False
        if not valid: rejected+=1;continue
        if broker in group["brokers"]: group["duplicate"]=True
        group["brokers"][broker]=row["directional_summary"]
    result={s:{"windows":{}} for s in sorted(expected)}
    for (sec,window),group in groups.items():
        values=list(group["brokers"].values())
        item={"status":"insufficient_evidence","score":None,"directional_breadth":None,"broker_count":len(values)}
        if group["duplicate"]: item["reason"]="duplicate_broker_window_profile"
        elif len(values)<3: item["reason"]="minimum_broker_count_not_met"
        else:
            buys=values.count("net_buy_dominant");sells=values.count("net_sell_dominant")
            item.update(status="descriptive_only",directional_breadth="buy_side_breadth" if buys>sells else "sell_side_breadth" if sells>buys else "balanced",net_buy_brokers=buys,net_sell_brokers=sells)
        result[sec]["windows"][window]=item
    return dict(base,status="descriptive_only",securities=result,rejected_profile_rows=rejected)
