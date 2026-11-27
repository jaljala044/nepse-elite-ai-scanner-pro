from app.scanner_historical_replay_pipeline import build_historical_research_candidates

def test_strategy_score_alone_never_becomes_a_trade():
    snapshot={"security_id":"X","symbol":"XYZ","session_date":"2025-01-01",
      "decision_cutoff":"2025-01-01T18:00:00+05:45","feature_snapshot_sha256":"a"*64,
      "feature_status":"complete"}
    result=build_historical_research_candidates(snapshots=[snapshot],
      feature_evidence_by_key={"X|2025-01-01":{}},trade_plans_by_key={},
      partition_by_date={"2025-01-01":"train"})
    assert result["qualified_signal_count"]==0
    assert len(result["evaluations"])==24
    assert all(not batch for batch in result["signals_by_strategy_horizon"].values())

def test_unverified_or_missing_trade_plan_is_withheld():
    snapshot={"security_id":"X","symbol":"XYZ","session_date":"2025-01-01",
      "decision_cutoff":"2025-01-01T18:00:00+05:45","feature_snapshot_sha256":"a"*64,
      "feature_status":"complete"}
    result=build_historical_research_candidates(snapshots=[snapshot],
      feature_evidence_by_key={"X|2025-01-01":{}},
      trade_plans_by_key={"X|2025-01-01":{"trend_momentum":{"t_plus_2":{"evidence_status":"unverified"}}}},
      partition_by_date={"2025-01-01":"train"})
    assert result["qualified_signal_count"]==0
    assert all(not batch for batch in result["signals_by_strategy_horizon"].values())


def _snapshot():
    return {"security_id":"X","symbol":"XYZ","session_date":"2025-01-01",
        "decision_cutoff":"2025-01-01T18:00:00+05:45","feature_snapshot_sha256":"a"*64,
        "feature_status":"complete"}


def _plan(**changes):
    cutoff="2025-01-01T18:00:00+05:45"
    value={"signal_id":"signal-1","decision_date":"2025-01-01","decision_time":cutoff,
      "sample_partition":"train","entry_price":"100","liquidity_quantity_cap":"1000",
      "net_reward_risk":"2.5","evidence_status":"verified","source_id":"plan-src",
      "evidence_id":"plan-ev","available_at":"2025-01-01T17:00:00+05:45",
      "stop":{"price":"95","evidence_status":"verified","source_id":"stop-src",
        "evidence_id":"stop-ev","available_at":"2025-01-01T17:00:00+05:45"},
      "target":{"price":"115","evidence_status":"verified","source_id":"target-src",
        "evidence_id":"target-ev","available_at":"2025-01-01T17:00:00+05:45"}}
    value.update(changes)
    return value


def _build(plan, snapshot=None, evidence=None):
    from unittest.mock import patch
    snap=_snapshot() if snapshot is None else snapshot
    key=snap["security_id"]+"|"+snap["session_date"]
    plan_map={"trend_momentum":{"t_plus_2":plan}} if plan is not None else {}
    with patch("app.scanner_historical_replay_pipeline.evaluate_strategy",
               return_value={"status":"research_ranked","score":"90"}):
        return build_historical_research_candidates(
            snapshots=[snap],
            feature_evidence_by_key={key:{"feature_snapshot_sha256":snap["feature_snapshot_sha256"]} if evidence is None else evidence},
            trade_plans_by_key={key:plan_map},
            partition_by_date={snap["session_date"]:"train"},
        )


def test_verified_plan_requires_whole_share_cap_and_consistent_reward_risk():
    accepted=_build(_plan())
    assert accepted["qualified_signal_count"]==1
    assert accepted["signals_by_strategy_horizon"]["trend_momentum:t_plus_2"][0]["signal_id"]=="signal-1"

    overclaimed=_build(_plan(net_reward_risk="3.5"))
    assert overclaimed["qualified_signal_count"]==0

    fractional_cap=_build(_plan(liquidity_quantity_cap="1000.5"))
    assert fractional_cap["qualified_signal_count"]==0

    invalid_entry=_build(_plan(entry_price="NaN"))
    assert invalid_entry["qualified_signal_count"]==0

    infinite_rr=_build(_plan(net_reward_risk="Infinity"))
    assert infinite_rr["qualified_signal_count"]==0

    late_plan=_build(_plan(available_at="2025-01-01T18:01:00+05:45"))
    assert late_plan["qualified_signal_count"]==0

    invalid_stop=_build(_plan(stop={**_plan()["stop"],"price":"100"}))
    assert invalid_stop["qualified_signal_count"]==0

    invalid_target=_build(_plan(target={**_plan()["target"],"price":"100"}))
    assert invalid_target["qualified_signal_count"]==0

    invalid_partition=_build(_plan(sample_partition="test"))
    assert invalid_partition["qualified_signal_count"]==0


def test_trade_plan_requires_source_bound_available_stop_and_target():
    late_stop={"price":"95","evidence_status":"verified","source_id":"stop-src",
        "evidence_id":"stop-ev","available_at":"2025-01-01T18:01:00+05:45"}
    late_plan=_build(_plan(stop=late_stop))
    assert late_plan["qualified_signal_count"]==0

    missing_plan_evidence=_build(_plan(evidence_status="verified",source_id="",evidence_id=""))
    assert missing_plan_evidence["qualified_signal_count"]==0


def test_feature_evidence_must_bind_to_exact_snapshot_digest():
    snap=_snapshot()
    mismatched={"feature_snapshot_sha256":"b"*64}
    result=_build(_plan(),snapshot=snap,evidence=mismatched)
    assert result["qualified_signal_count"]==0
    assert result["evaluations"][0]["feature_evidence_gate"]=="missing_or_snapshot_mismatch"


def test_duplicate_or_future_snapshot_is_rejected():
    snap=_snapshot()
    from unittest.mock import patch
    key="X|2025-01-01"
    with patch("app.scanner_historical_replay_pipeline.evaluate_strategy",
               return_value={"status":"research_ranked"}):
        import pytest
        with pytest.raises(ValueError,match="duplicate_security_session_snapshot"):
            build_historical_research_candidates(
                snapshots=[snap,snap],feature_evidence_by_key={key:{}},
                trade_plans_by_key={},partition_by_date={"2025-01-01":"train"})

        future=dict(snap,session_date="2025-01-02")
        with pytest.raises(ValueError,match="future_snapshot_after_decision_cutoff"):
            build_historical_research_candidates(
                snapshots=[future],feature_evidence_by_key={},trade_plans_by_key={},
                partition_by_date={})

