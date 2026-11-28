"""Mode-specific descriptive broker research; never a trade confirmation."""
from decimal import Decimal
from .broker_context_integration import stamp
from .broker_context_server import server_context
from .broker_lifecycle_gate import load_lifecycle,lifecycle_reason
POLICIES={"swing":{"holding_days":[3,15],"required_sessions":5},"positional":{"holding_weeks":[2,8],"required_sessions":21}}

def mode_research(snapshot,prices,memberships,sector_prices,*,mode,decision_time,expected_sessions):
    if mode not in POLICIES: raise ValueError("unknown research mode")
    policy=POLICIES[mode]
    base={"mode":mode,"policy":dict(policy),"status":"insufficient_evidence","score":None,
          "score_eligible":False,"production_eligible":False,"signals_enabled":False,
          "source_authentication_performed":False,"profiles":[],"confirmation":None}
    if len(expected_sessions)!=policy["required_sessions"]:
        return dict(base,reason="mode_session_count_mismatch")
    result=server_context(snapshot,prices,memberships,sector_prices,decision_time=decision_time,expected_sessions=expected_sessions)
    if result["status"]!="descriptive_only":
        return dict(base,reason=result.get("reason","broker_context_unavailable"))
    lifecycle=load_lifecycle()
    exclusions={}
    for row in result["profiles"]:
        if row["status"]!="descriptive_only":
            reason="broker_context_ineligible"
        else:
            reason=lifecycle_reason(row["security_id"],row["symbol"],expected_sessions[0],expected_sessions[-1],lifecycle)
        exclusions[reason]=exclusions.get(reason,0)+1
    # No historical identity has been independently certified by these inputs.
    # Keep the scanner's action and scoring path entirely separate.
    return dict(base,reason="historical_identity_not_certified",exclusions=exclusions,
                evaluated_profiles=len(result["profiles"]),input_sha256=result.get("input_sha256"))
