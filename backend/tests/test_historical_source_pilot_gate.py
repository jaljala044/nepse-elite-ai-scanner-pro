from app.historical_source_pilot_gate import (
    PROVIDER_CATALOG, audit_nepse_source_coverage,
    evaluate_historical_pilot_evidence, run_controlled_historical_pilot,
)


def test_catalog_includes_requested_cross_check_providers_without_claiming_approval():
    assert {"sharesansar", "chukul", "sharehub_nepal", "punji"}.issubset(PROVIDER_CATALOG)
    result = audit_nepse_source_coverage(source_contracts=[], decision_cutoff="2026-11-28T12:00:00Z")
    assert result["status"] == "SOURCE_COVERAGE_BLOCKED"
    assert result["network_access_performed"] is False
    assert result["endpoints_invented"] is False
    assert result["publisher_authenticity_proven"] is False


def test_unverified_punji_identity_never_counts_as_independent_source():
    contract = {"source_id": "punji", "publisher_identity_reviewed": False}
    result = audit_nepse_source_coverage(source_contracts=[contract], decision_cutoff="2026-11-28T12:00:00Z")
    punji = next(x for x in result["providers"] if x["source_id"] == "punji")
    assert punji["status"] == "IDENTITY_REVIEW_REQUIRED"
    assert "punji" not in result["approved_third_party_sources"]


def test_pilot_evidence_fails_closed_without_real_capture_and_reconciliation():
    result = evaluate_historical_pilot_evidence(
        source_coverage={"status": "SOURCE_COVERAGE_BLOCKED"},
        capture_evidence=[],
        reconciliation={},
        calendar_evidence={},
        universe_evidence={},
    )
    assert result["status"] == "HISTORICAL_PILOT_BLOCKED"
    assert result["backtest_admission_allowed"] is False
    assert result["replay_executed"] is False


def test_capture_requires_hash_pagination_schema_and_archived_payload():
    result = evaluate_historical_pilot_evidence(
        source_coverage={"status": "SOURCE_COVERAGE_READY", "approved_official_sources": ["nepse_official", "cdsc"],
                         "approved_third_party_sources": ["sharesansar"], "coverage_sha256": "a" * 64},
        capture_evidence=[{"capture_id": "c1", "source_id": "nepse_official", "raw_payload_sha256": "b" * 64,
                           "row_count": 12, "pagination_complete": False, "schema_validation_status": "passed",
                           "raw_payload_archived": True, "window_start": "2026-01-01", "window_end": "2026-01-31",
                           "publisher_id": "exchange"}],
        reconciliation={"status": "RECONCILIATION_PASSED", "unresolved_critical_anomalies": 0,
                        "independent_publisher_count": 3},
        calendar_evidence={"official_session_completeness_verified": True},
        universe_evidence={"point_in_time_universe_verified": True, "ipo_delist_suspension_coverage_verified": True},
    )
    assert result["status"] == "HISTORICAL_PILOT_BLOCKED"
    assert any(x["reason"] == "capture_pagination_incomplete" for x in result["issues"])


def test_controlled_runner_never_calls_replay_for_blocked_pilot():
    called = []
    result = run_controlled_historical_pilot(
        pilot_evidence={"status": "HISTORICAL_PILOT_BLOCKED"},
        replay_kwargs={"run_one": lambda **kwargs: called.append(kwargs)},
    )
    assert result["status"] == "BLOCKED_NO_VERIFIED_PILOT_PANEL"
    assert called == []
    assert result["historical_replay_executed"] is False


def test_capture_evidence_requires_all_approved_sources():
    result = evaluate_historical_pilot_evidence(
        source_coverage={"status": "SOURCE_COVERAGE_READY", "approved_official_sources": ["nepse_official", "cdsc"],
                         "approved_third_party_sources": ["sharesansar", "chukul"], "coverage_sha256": "c" * 64},
        capture_evidence=[{"capture_id": "c1", "source_id": "nepse_official", "raw_payload_sha256": "d" * 64,
                           "row_count": 3, "pagination_complete": True, "schema_validation_status": "passed",
                           "raw_payload_archived": True, "window_start": "2026-01-01", "window_end": "2026-01-31",
                           "publisher_id": "exchange"}],
        reconciliation={"status": "RECONCILIATION_PASSED", "unresolved_critical_anomalies": 0,
                        "independent_publisher_count": 3},
        calendar_evidence={"official_session_completeness_verified": True},
        universe_evidence={"point_in_time_universe_verified": True, "ipo_delist_suspension_coverage_verified": True},
    )
    assert result["status"] == "HISTORICAL_PILOT_BLOCKED"
    assert any(x["reason"] == "approved_sources_missing_capture_evidence" for x in result["issues"])
