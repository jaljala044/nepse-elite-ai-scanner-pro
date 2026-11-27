import pytest
from app.scanner_trade_audit import build_trade_audit_report

def test_trade_audit_separates_closed_pending_rejected_and_unmatched():
    signals=[{"signal_id":sid,"sample_partition":"out_of_sample","symbol":sid,
        "strategy_id":"trend_momentum","horizon":"swing"} for sid in ("A","B","C","D")]
    bundle={"runs":[{"strategy_id":"trend_momentum","horizon":"swing","partition":"out_of_sample",
        "trades":[{"source_signal_id":"A","entry_date":"2026-01-03","entry_price":"100",
            "exit_date":"2026-01-06","exit_price":"120","exit_reason":"target",
            "net_return_pct":"18","stop_triggered_during_lock":False}],
        "pending_exits":[{"source_signal_id":"B"}],
        "rejected_signals":[{"signal_id":"C","reason":"bad_data"}]}]}
    report=build_trade_audit_report(replay_bundle=bundle,signals=signals)
    assert report["closed_trade_count"] == 1
    assert report["pending_signal_count"] == 1
    assert report["rejected_signal_count"] == 1
    assert report["unmatched_signal_count"] == 1
    assert [x["status"] for x in report["signals"]] == [
        "closed_trade","settlement_or_data_pending","rejected_by_replay","no_replay_outcome_unmatched"]
    assert report["runs"][0]["target_hit_rate_pct"] == "100.0"

def test_audit_rejects_duplicate_signal_ids_and_bad_partition():
    with pytest.raises(ValueError, match="duplicate_signal_id"):
        build_trade_audit_report(replay_bundle={"runs":[]},signals=[
            {"signal_id":"A","sample_partition":"out_of_sample"},
            {"signal_id":"A","sample_partition":"out_of_sample"}])
    with pytest.raises(ValueError, match="explicit_partition_required"):
        build_trade_audit_report(replay_bundle={"runs":[]},signals=[],partition="all")
