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
