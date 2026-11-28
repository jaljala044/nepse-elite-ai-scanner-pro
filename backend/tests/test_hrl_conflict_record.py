from __future__ import annotations

import pytest

from backend.validation.hrl_conflict_record import HRLConflictRecord


HISTORY_SHA = "2aaac3df4b8bf236d1d1864fc5af96e6548eac95dc20c23f97cec82d0c972db3"
SMC_SHA = "2d4c103cc07d54bd8b197784763c9a5f8c4a6fe014452ae0c91f28d03ccbc83b"


def make_record(**kw):
    base = dict(
        symbol_id="HRL",
        trade_date="2026-11-19",
        raw_low=480.00,
        project_designated_low=483.90,
        open=483.00,
        high=488.00,
        close=486.00,
        raw_archive_sha256=HISTORY_SHA,
        source_archive_sha256={
            "nepse-history-starter": HISTORY_SHA,
            "nepse-smc-data": SMC_SHA,
        },
        source_rows={
            "nepse-history-starter": {
                "open": "483", "high": "488", "low": "480",
                "close": "483.9", "volume": "49184", "source_csv_line": 935,
            },
            "nepse-smc-data": {
                "open": "483", "high": "488", "low": "480",
                "close": "486", "volume": "18817", "source_csv_line": 654,
            },
        },
    )
    base.update(kw)
    return HRLConflictRecord(**base)


def test_both_values_and_both_raw_source_rows_preserved():
    record = make_record()
    assert record.raw_low == 480.00
    assert record.project_designated_low == 483.90
    assert record.source_rows["nepse-history-starter"]["low"] == "480"
    assert record.source_rows["nepse-smc-data"]["low"] == "480"
    assert record.source_rows["nepse-history-starter"]["close"] == "483.9"
    assert record.source_rows["nepse-smc-data"]["close"] == "486"


def test_raw_geometry_valid():
    assert make_record().geometry_valid_for_raw() is True


def test_project_geometry_invalid():
    assert make_record().geometry_valid_for_project() is False


def test_default_quarantined_no_promotion():
    record = make_record()
    assert record.status == "QUARANTINED"
    assert record.canonical_promotion_allowed is False


def test_option_a_resolution_keeps_both_values_and_promotion_disabled():
    record = make_record(
        status="RESOLVED", chosen_option="A", decided_by="owner",
        decision_date="2026-11-28",
        justification="Adopt raw low; retain project value in provenance.",
    )
    assert record.status == "RESOLVED"
    assert record.raw_low == 480.00
    assert record.project_designated_low == 483.90
    assert record.canonical_promotion_allowed is False


def test_option_c_stays_quarantined():
    record = make_record(chosen_option="C")
    assert record.status == "QUARANTINED"
    assert record.chosen_option == "C"


def test_no_silent_replacement_in_serialized_record():
    data = make_record().to_dict()
    assert data["raw_low"] != data["project_designated_low"]
    assert "raw_low" in data and "project_designated_low" in data
    assert set(data["source_rows"]) == {"nepse-history-starter", "nepse-smc-data"}


@pytest.mark.parametrize("kwargs", [
    {"status": "RESOLVED", "chosen_option": "A"},
    {"status": "RESOLVED", "chosen_option": "C", "decided_by": "owner",
     "decision_date": "2026-11-28", "justification": "Keep conflict."},
    {"canonical_promotion_allowed": True},
    {"chosen_option": "B"},
])
def test_incomplete_or_unsafe_decisions_fail_closed(kwargs):
    with pytest.raises(ValueError):
        make_record(**kwargs)


def test_invalid_archive_hash_rejected():
    with pytest.raises(ValueError, match="SHA-256"):
        make_record(raw_archive_sha256="<sha>")


def test_only_hrl_identity_accepted():
    with pytest.raises(ValueError, match="symbol_id"):
        make_record(symbol_id="API")
