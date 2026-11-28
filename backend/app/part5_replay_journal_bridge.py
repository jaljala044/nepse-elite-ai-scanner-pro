"""Internal adapter for a stored research signal and a hypothetical replay outcome."""
from .signal_store import get_signal
from .part5_paper_store import store_paper
from .point_in_time import _aware
from zoneinfo import ZoneInfo
from datetime import date

def record_replay_outcome(owner, signal_id, replay, *, observed_at):
    """No automatic account fan-out; trusted caller must supply authorized owner."""
    original=get_signal(signal_id)
    if original is None:
        raise ValueError("stored signal required")
    if replay.get("classification")!="hypothetical_research_only" or replay.get("production_approved") is not False:
        raise ValueError("research replay required")
    day=_aware(original["decision_time"]).astimezone(ZoneInfo("Asia/Kathmandu")).date().isoformat()
    trades=[t for t in replay.get("trades",[]) if t.get("decision_date")==day and t.get("horizon")==original["horizon"]]
    if len(trades)!=1 or trades[0].get("status")!="closed_scenario":
        raise ValueError("one completed matching scenario required")
    trade=trades[0]
    if date.fromisoformat(trade["exit_date"])>_aware(observed_at).astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("future outcome")
    # Symbol and methodology are bound by the trusted replay caller, not inferred from prices.
    if replay.get("symbol")!=original["symbol"] or replay.get("methodology")!=original["methodology"]:
        raise ValueError("replay identity mismatch")
    return store_paper(owner,{"signal_id":signal_id,"record":original},trade,observed_at=observed_at)
