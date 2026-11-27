"""Risk overlay: incomplete asset valuations never authorize new purchases."""
from decimal import Decimal
from .pending_corporate_assets import review_pending_assets
from .corporate_action_risk import assess_post_action_risk, _amount

def review_pending_asset_risk(*,snapshot,limits,entitlements,confirmations,assessment_time):
    assets=review_pending_assets(entitlements=entitlements,confirmations=confirmations,assessment_time=assessment_time)
    # Snapshot must already reflect confirmed receipts and paid subscriptions.
    if snapshot.get("corporate_asset_balance_basis")!="confirmed_receipts_and_payments_included_pending_assets_excluded":
        raise ValueError("corporate_asset_balance_basis_required")
    base=assess_post_action_risk(snapshot=snapshot,limits=limits,assessment_time=assessment_time)
    cash=_amount(snapshot["available_cash"],"cash")
    commitment=_amount(snapshot.get("pending_rights_payment",0),"rights_payment")
    rights=Decimal(assets["pending_paid_rights_at_cost"])
    dividends=Decimal(assets["pending_gross_dividends"])
    unresolved=[a["action_id"] for a in assets["assets"] if a["status"]!="CONFIRMED"]
    reasons=[]
    if unresolved: reasons.append("pending_corporate_asset_valuation_incomplete")
    if not base["new_entries_allowed_by_risk_gate"]: reasons.append("base_risk_gate_blocked")
    return dict(base_risk=base,corporate_assets=assets,
        spendable_cash_after_commitments=str(max(Decimal(0),cash-commitment)),
        conservative_risk_equity=base["equity"],
        pending_rights_carrying_cost=str(rights),pending_gross_dividends=str(dividends),
        complete_portfolio_fair_value=None if unresolved else base["equity"],
        unresolved_action_ids=unresolved,new_entries_allowed_by_risk_gate=not reasons,
        gate_reasons=reasons,execution_eligible=False,production_eligible=False,
        limitations=["Confirmed receipts and payments must already be reconciled into snapshot balances.",
        "Pending assets excluded from risk denominator; drawdown may overstate economic loss.",
        "No fair value or independent custody verification; all pending assets block new entries."])
