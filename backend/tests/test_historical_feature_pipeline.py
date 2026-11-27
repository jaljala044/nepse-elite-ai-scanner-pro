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

def test_feature_builder_rejects_future_available_bar():
    row={"security_id":"X","symbol":"XYZ","session_date":"2025-01-01","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000","source_id":"src","evidence_id":"ev","available_at":"2025-01-02T10:00:00+05:45"}
    result=build_point_in_time_feature_snapshots(panel_rows=[row],decision_cutoffs={"2025-01-01":"2025-01-01T18:00:00+05:45"})
    assert result["status"]=="partial_or_blocked"
    assert any("bar_not_available_at_decision" in x for x in result["errors"])
