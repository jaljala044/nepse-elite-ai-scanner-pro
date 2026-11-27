"""Internal research service boundary; trusted principal must come from authentication."""
from .chronological_ledger_reconciliation import reconcile_chronological_ledger

def review_owned_portfolio(*,principal_id,portfolio_id,ownership_lookup,snapshot_lookup):
    if not principal_id or not portfolio_id or ownership_lookup(portfolio_id)!=principal_id:
        raise PermissionError("portfolio_access_denied")
    snapshot=snapshot_lookup(portfolio_id)
    if not isinstance(snapshot,dict) or snapshot.get("portfolio_id")!=portfolio_id:
        raise ValueError("portfolio_snapshot_unavailable")
    result=reconcile_chronological_ledger(ledger_inputs=snapshot["ledger_inputs"],events=snapshot["events"],opening_lots=snapshot.get("opening_lots"))
    return dict(portfolio_id=portfolio_id,review=result,production_eligible=False)
