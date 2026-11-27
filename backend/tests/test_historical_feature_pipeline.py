from app.nepse_historical_universe import build_effective_universe
from app.scanner_historical_features import build_point_in_time_feature_snapshots

def test_universe_flags_unknown_interval_and_symbol_collision():
    rows=[
      {"security_id":"A","symbol":"ABC","effective_from":"2020-01-01","effective_to":"2020-01-02","listing_status":"ACTIVE"},
      {"security_id":"A","symbol":"ABC","effective_from":"2020-01-05","listing_status":"DELISTED"},
      {"security_id":"B","symbol":"ABC","effective_from":"2020-01-01","listing_status":"ACTIVE"},
    ]
    result=build_effective_universe(universe_rows=rows,session_dates=["2020-01-01","2020-01-03","2020-01-05"])
    assert "uncovered_universe_interval:A" in result["errors"]
    assert "simultaneous_symbol_collision:2020-01-01:ABC" in result["errors"]

def test_universe_keeps_later_ipo_and_delisted_history():
    rows=[
      {"security_id":"OLD","symbol":"OLD","effective_from":"2020-01-01","listing_status":"ACTIVE"},
      {"security_id":"NEW","symbol":"NEW","effective_from":"2020-01-03","listing_status":"ACTIVE"},
      {"security_id":"OLD","symbol":"OLD","effective_from":"2020-01-04","listing_status":"DELISTED"},
    ]
    result=build_effective_universe(universe_rows=rows,session_dates=["2020-01-01","2020-01-03","2020-01-04"])
    assert result["active_by_session"]["2020-01-01"]=={"OLD":"OLD"}
    assert result["active_by_session"]["2020-01-03"]=={"OLD":"OLD","NEW":"NEW"}
    assert "OLD" in result["security_ids"]
    assert result["inactive_security_count"]==1

def test_features_are_point_in_time_and_warmup_is_explicit():
    rows=[]
    for i in range(205):
        day=f"2025-01-{(i%28)+1:02d}" if i<28 else f"2025-{(i//28)+1:02d}-{(i%28)+1:02d}"
        # Use monotonically increasing close values and distinct chronological dates below.
        from datetime import date,timedelta
        d=(date(2025,1,1)+timedelta(days=i)).isoformat()
        rows.append({"security_id":"X","symbol":"XYZ","session_date":d,"open":str(100+i),
            "high":str(102+i),"low":str(99+i),"close":str(101+i),"volume":"1000","turnover":"101000",
            "source_id":"src","evidence_id":"ev-"+str(i),"available_at":d+"T16:00:00+05:45"})
    cutoffs={r["session_date"]:r["session_date"]+"T18:00:00+05:45" for r in rows}
    result=build_point_in_time_feature_snapshots(panel_rows=rows,decision_cutoffs=cutoffs)
    assert result["status"]=="validated_for_research"
    assert result["snapshot_count"]==205
    assert result["snapshots"][-1]["feature_status"]=="complete"
    assert result["snapshots"][0]["feature_status"]=="warmup_incomplete"


def _valid_panel_row(day="2025-01-01", *, volume="1000", evidence_id="ev-1",
                     available_at=None, open_="10", high="11", low="9", close="10"):
    return {"security_id":"X","symbol":"XYZ","session_date":day,
        "open":open_,"high":high,"low":low,"close":close,
        "volume":volume,"turnover":"10000","source_id":"src",
        "evidence_id":evidence_id,
        "available_at":available_at or day+"T09:00:00+05:45"}


def test_feature_builder_rejects_future_session_after_nepal_local_cutoff():
    row=_valid_panel_row("2025-01-02", available_at="2025-01-02T09:00:00+05:45")
    result=build_point_in_time_feature_snapshots(
        panel_rows=[row],
        decision_cutoffs={"2025-01-02":"2025-01-01T18:00:00+05:45"},
    )
    assert result["snapshot_count"]==0
    assert "future_session_after_decision_cutoff:X:2025-01-02" in result["errors"]


def test_feature_builder_rejects_zero_and_fractional_share_volume():
    for volume in ("0","1.5"):
        with __import__("pytest").raises(ValueError, match="panel_ohlcv_invalid"):
            build_point_in_time_feature_snapshots(
                panel_rows=[_valid_panel_row(volume=volume)],
                decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"},
            )


def test_feature_builder_rejects_inconsistent_ohlc():
    with __import__("pytest").raises(ValueError, match="panel_ohlc_inconsistent"):
        build_point_in_time_feature_snapshots(
            panel_rows=[_valid_panel_row(high="9.5")],
            decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"},
        )


def test_feature_snapshot_hash_binds_source_and_evidence_lineage():
    rows=[_valid_panel_row(evidence_id="ev-A")]
    cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"}
    first=build_point_in_time_feature_snapshots(panel_rows=rows,decision_cutoffs=cutoffs)
    second=build_point_in_time_feature_snapshots(
        panel_rows=[_valid_panel_row(evidence_id="ev-B")],decision_cutoffs=cutoffs)
    assert first["snapshots"][0]["feature_snapshot_sha256"] != second["snapshots"][0]["feature_snapshot_sha256"]


def test_each_snapshot_rechecks_prior_bar_availability_at_its_own_cutoff():
    rows=[
        _valid_panel_row("2025-01-01",evidence_id="ev-1",available_at="2025-01-02T11:00:00+05:45"),
        _valid_panel_row("2025-01-02",evidence_id="ev-2",available_at="2025-01-02T09:00:00+05:45"),
    ]
    result=build_point_in_time_feature_snapshots(
        panel_rows=rows,
        decision_cutoffs={
            "2025-01-01":"2025-01-03T12:00:00+05:45",
            "2025-01-02":"2025-01-02T10:00:00+05:45",
        },
    )
    latest=result["snapshots"][-1]
    assert latest["session_date"]=="2025-01-02"
    assert latest["history_session_count"]==1


def test_feature_builder_rejects_compact_session_date():
    with __import__("pytest").raises(ValueError, match="canonical_YYYY_MM_DD"):
        build_point_in_time_feature_snapshots(
            panel_rows=[_valid_panel_row("20250101")],
            decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"},
        )


def test_duplicate_benchmark_sessions_fail_closed():
    benchmark=[
        {"session_date":"2025-01-01","close":"2000","source_id":"index","evidence_id":"a","available_at":"2025-01-01T17:00:00+05:45"},
        {"session_date":"2025-01-01","close":"2001","source_id":"index","evidence_id":"b","available_at":"2025-01-01T17:00:00+05:45"},
    ]
    with __import__("pytest").raises(ValueError, match="duplicate_benchmark_session"):
        build_point_in_time_feature_snapshots(
            panel_rows=[_valid_panel_row()],
            decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"},
            benchmark_rows=benchmark,
        )

def test_feature_builder_rejects_future_available_bar():
    row={"security_id":"X","symbol":"XYZ","session_date":"2025-01-01","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000","source_id":"src","evidence_id":"ev","available_at":"2025-01-02T10:00:00+05:45"}
    result=build_point_in_time_feature_snapshots(panel_rows=[row],decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"})
    assert result["status"]=="partial_or_blocked"
    assert any("bar_not_available_at_decision" in x for x in result["errors"])


def test_feature_fingerprint_binds_cutoff_and_full_source_lineage():
    row={"security_id":"X","symbol":"XYZ","session_date":"2025-01-01",
        "open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000",
        "source_id":"source-a","evidence_id":"evidence-a",
        "available_at":"2025-01-01T16:00:00+05:45"}
    def build(candidate, cutoff="2025-01-01T18:00:00+05:45"):
        return build_point_in_time_feature_snapshots(
            panel_rows=[candidate],decision_cutoffs={"2025-01-01":cutoff}
        )["snapshots"][0]["feature_snapshot_sha256"]

    original=build(row)
    changed_source=build({**row,"source_id":"source-b"})
    changed_evidence=build({**row,"evidence_id":"evidence-b"})
    changed_availability=build({**row,"available_at":"2025-01-01T16:30:00+05:45"})
    changed_cutoff=build(row,"2025-01-01T19:00:00+05:45")
    changed_ohlcv=build({**row,"turnover":"1001"})

    assert len(original)==64
    assert len({original,changed_source,changed_evidence,changed_availability,
                changed_cutoff,changed_ohlcv})==6
