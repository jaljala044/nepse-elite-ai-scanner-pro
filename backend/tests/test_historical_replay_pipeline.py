from app.scanner_historical_replay_pipeline import build_historical_research_candidates, _valid_trade_plan

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


def test_verified_trade_plan_requires_complete_provenance_and_valid_long_geometry():
    snapshot={"session_date":"2025-01-01",
        "decision_cutoff":"2025-01-01T18:00:00+05:45",
        "feature_snapshot_sha256":"a"*64}
    plan={"signal_id":"signal-1","decision_date":"2025-01-01",
        "decision_time":"2025-01-01T18:00:00+05:45","sample_partition":"train",
        "entry_price":"100","liquidity_quantity_cap":"100",
        "net_reward_risk":"2.2","feature_snapshot_sha256":"a"*64,
        "evidence_status":"verified","source_id":"plan-source",
        "evidence_id":"plan-evidence","available_at":"2025-01-01T17:00:00+05:45",
        "stop":{"price":"90","evidence_status":"verified","source_id":"stop-source",
            "evidence_id":"stop-evidence","available_at":"2025-01-01T17:01:00+05:45"},
        "target":{"price":"125","evidence_status":"verified","source_id":"target-source",
            "evidence_id":"target-evidence","available_at":"2025-01-01T17:02:00+05:45"}}

    assert _valid_trade_plan(plan,snapshot,"2025-01-01","train") is True

    invalid=[]
    invalid.append({**plan,"source_id":""})
    invalid.append({**plan,"available_at":"2025-01-01T18:01:00+05:45"})
    invalid.append({**plan,"entry_price":"NaN"})
    invalid.append({**plan,"liquidity_quantity_cap":"0"})
    invalid.append({**plan,"liquidity_quantity_cap":"10.5"})
    invalid.append({**plan,"net_reward_risk":"Infinity"})
    invalid.append({**plan,"stop":{**plan["stop"],"price":"100"}})
    invalid.append({**plan,"target":{**plan["target"],"price":"100"}})
    invalid.append({**plan,"stop":{**plan["stop"],"available_at":"2025-01-01T18:01:00+05:45"}})
    invalid.append({**plan,"target":{**plan["target"],"evidence_id":""}})
    invalid.append({**plan,"sample_partition":"test"})

    assert all(not _valid_trade_plan(candidate,snapshot,"2025-01-01","train")
               for candidate in invalid)
