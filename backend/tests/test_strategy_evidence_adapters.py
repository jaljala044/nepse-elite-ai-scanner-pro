from app.scanner_strategy_evidence_adapters import adapt_strategy_evidence, adapt_all_strategy_evidence

def item(day="2026-01-02T10:00:00+00:00", score="80"):
    return {"status":"verified","source_id":"official-feed","evidence_id":"E1","available_at":day,"score":score}

def test_adapter_preserves_only_verified_pre_cutoff_features():
    result=adapt_strategy_evidence(strategy_id="idpat_smart_money",
        source_evidence={"idpat_price_volume":item(),"broker_flow":item("2026-01-03T00:00:00+00:00")},
        decision_cutoff="2026-01-02T18:00:00+00:00")
    assert result["verified_feature_count"] == 1
    assert "idpat_price_volume" in result["evidence"]
    assert result["withheld"]["broker_flow"] == "unverified_or_invalid_or_future_dated"
    assert result["status"] == "partial"

def test_adapter_never_fills_missing_features_and_supports_all_six():
    result=adapt_all_strategy_evidence(source_evidence={},
        decision_cutoff="2026-01-02T18:00:00+00:00")
    assert len(result) == 6
    assert all(x["verified_feature_count"] == 0 and x["status"] == "partial" for x in result.values())

def test_invalid_cutoff_and_strategy_rejected():
    import pytest
    with pytest.raises(ValueError): adapt_strategy_evidence(strategy_id="unknown",source_evidence={},decision_cutoff="2026-01-02")
    with pytest.raises(ValueError): adapt_strategy_evidence(strategy_id="trend_momentum",source_evidence={},decision_cutoff="2026-01-02")
