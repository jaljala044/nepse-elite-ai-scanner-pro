import hashlib

from app.historical_source_bundle_runner import (
    run_replay_from_validated_source_bundle,
    validate_real_source_bundle,
)


def _valid_contract(source_id, publisher_id, dataset_kind, host):
    return {
        "source_id": source_id, "publisher_id": publisher_id, "dataset_kind": dataset_kind,
        "endpoint_url": f"https://{host}/history", "allowed_hosts": [host],
        "allowed_content_types": ["text/csv"], "window_start": "2025-01-01T00:00:00+05:45",
        "window_end": "2025-12-31T23:59:59+05:45", "reviewed_at": "2026-01-01T00:00:00+05:45",
        "review_status": "approved", "approved_by_human": True, "reviewer_id": "reviewer-1",
        "authority_evidence_ref": "review-ticket-123", "licence_reviewed": True,
        "access_policy_reviewed": True, "authentication_mode": "public",
        "page_parameter": "page", "terminal_signal": "has_more_false", "max_pages": 20,
        "minimum_request_interval_seconds": 1.0, "capture_id": f"capture-{source_id}",
        "publisher_identity_reviewed": True,
    }


def _bundle(source_id, publisher_id, host):
    raw = b"symbol,close\nAAA,100\n"
    digest = hashlib.sha256(raw).hexdigest()
    manifest = {
        "source_id": source_id, "publisher_id": publisher_id,
        "request_url": f"https://{host}/history?page=1",
        "captured_at": "2026-01-02T00:00:00+05:45", "available_at": "2026-01-02T00:00:00+05:45",
        "window_start": "2025-01-01T00:00:00+05:45", "window_end": "2025-12-31T23:59:59+05:45",
        "pages": [{"page_number": 1, "payload_id": f"payload-{source_id}", "raw_sha256": digest,
                   "http_status": 200, "final_page": True}],
        "expected_page_count": 1, "capture_complete": True,
        "response_content_type": "text/csv", "capture_id": f"capture-{source_id}",
    }
    return {"manifest": manifest, "payloads": {f"payload-{source_id}": raw}}


def _common():
    contracts = [
        _valid_contract("nepse_official", "nepse", "official_eod_ohlcv", "exchange.example"),
        _valid_contract("cdsc", "cdsc", "cdsc_first_trade", "depository.example"),
        _valid_contract("sharesansar", "ss", "official_eod_ohlcv", "ss.example"),
        _valid_contract("chukul", "chukul", "official_eod_ohlcv", "chukul.example"),
    ]
    bundles = [
        _bundle("nepse_official", "nepse", "exchange.example"),
        _bundle("cdsc", "cdsc", "depository.example"),
        _bundle("sharesansar", "ss", "ss.example"),
        _bundle("chukul", "chukul", "chukul.example"),
    ]
    return contracts, bundles


def _schema(**kwargs):
    return {"status": "passed", "row_count": 10}


def _archive(**kwargs):
    return {"status": "archived", "archive_ref": "immutable://bundle/capture",
            "archive_manifest_sha256": "a" * 64}


def _reports():
    return (
        {"status": "RECONCILIATION_PASSED", "unresolved_critical_anomalies": 0,
         "independent_publisher_count": 4, "report_sha256": "b" * 64},
        {"official_session_completeness_verified": True, "report_sha256": "c" * 64},
        {"point_in_time_universe_verified": True, "ipo_delist_suspension_coverage_verified": True,
         "report_sha256": "d" * 64},
    )


def test_raw_capture_bundle_uses_existing_manifest_validator_and_archive_gate():
    contracts, bundles = _common()
    reconciliation, calendar, universe = _reports()
    result = validate_real_source_bundle(
        source_contracts=contracts, capture_bundles=bundles,
        decision_cutoff="2026-02-01T00:00:00+05:45",
        schema_validator=_schema, archive_verifier=_archive,
        reconciliation=reconciliation, calendar_evidence=calendar, universe_evidence=universe,
    )
    assert result["status"] == "HISTORICAL_PILOT_EVIDENCE_READY_FOR_HUMAN_REVIEW"
    assert len(result["capture_reports"]) == 4
    assert result["historical_replay_executed"] is False
    assert result["backtest_admission_allowed"] is False


def test_payload_hash_mismatch_blocks_bundle():
    contracts, bundles = _common()
    bundles[0]["payloads"]["payload-nepse_official"] += b"tampered"
    reconciliation, calendar, universe = _reports()
    result = validate_real_source_bundle(
        source_contracts=contracts, capture_bundles=bundles,
        decision_cutoff="2026-02-01T00:00:00+05:45",
        schema_validator=_schema, archive_verifier=_archive,
        reconciliation=reconciliation, calendar_evidence=calendar, universe_evidence=universe,
    )
    assert result["status"] == "HISTORICAL_PILOT_BLOCKED"
    assert result["historical_replay_executed"] is False


def test_missing_archive_or_report_provenance_blocks_bundle():
    contracts, bundles = _common()
    reconciliation, calendar, universe = _reports()
    result = validate_real_source_bundle(
        source_contracts=contracts, capture_bundles=bundles,
        decision_cutoff="2026-02-01T00:00:00+05:45",
        schema_validator=_schema,
        archive_verifier=lambda **kwargs: {"status": "archived"},
        reconciliation={**reconciliation, "report_sha256": None},
        calendar_evidence=calendar, universe_evidence=universe,
    )
    assert result["status"] == "HISTORICAL_PILOT_BLOCKED"
    assert any(x["reason"] == "immutable_raw_archive_not_verified" for x in result["errors"])
    assert any(x["reason"] == "reconciliation_report_sha256_missing_or_invalid" for x in result["errors"])


def test_replay_runner_never_invokes_strategy_when_bundle_is_blocked():
    contracts, bundles = _common()
    reconciliation, calendar, universe = _reports()
    called = []
    result = run_replay_from_validated_source_bundle(
        source_bundle_kwargs={
            "source_contracts": contracts, "capture_bundles": bundles[:1],
            "decision_cutoff": "2026-02-01T00:00:00+05:45",
            "schema_validator": _schema, "archive_verifier": _archive,
            "reconciliation": reconciliation, "calendar_evidence": calendar, "universe_evidence": universe,
        },
        replay_kwargs={"run_one": lambda **kwargs: called.append(kwargs)},
    )
    assert result["status"] == "BLOCKED_SOURCE_BUNDLE_NOT_READY"
    assert called == []
    assert result["historical_replay_executed"] is False
