"""Contract-ID/date identity anomaly checks for floorsheet archive comparisons.

A contract number's numeric prefix is treated as a diagnostic only. It is not
assumed to be an authoritative trade date unless a source profile documents it.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from app.floorsheet_contract import FloorsheetContract


def _index(rows: Iterable[FloorsheetContract], label: str):
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"{label} source must contain parsed contracts")
    by_contract = defaultdict(list)
    for row in materialized:
        if not isinstance(row, FloorsheetContract):
            raise ValueError(f"{label} rows must be FloorsheetContract objects")
        by_contract[row.contract_id].append(row)
    return materialized, by_contract


def _prefix_date(contract_id: str):
    if len(contract_id) < 8 or not contract_id[:8].isdigit():
        return None
    raw = contract_id[:8]
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8])).isoformat()
    except ValueError:
        return None


def audit_contract_date_identity(
    left_rows: Iterable[FloorsheetContract],
    right_rows: Iterable[FloorsheetContract],
) -> dict:
    """Report date collisions, source disagreements and diagnostic ID prefixes."""
    left, left_by_id = _index(left_rows, "left")
    right, right_by_id = _index(right_rows, "right")

    def within_source(rows_by_id, label):
        findings = []
        for contract_id, records in sorted(rows_by_id.items()):
            dates = sorted({row.trade_date for row in records})
            if len(dates) > 1:
                findings.append({
                    "contract_id": contract_id,
                    "dates": dates,
                    "row_count": len(records),
                    "source": label,
                    "anomaly": "same_contract_id_multiple_trade_dates",
                })
        return findings

    left_dates = {key: sorted({r.trade_date for r in rows})
                  for key, rows in left_by_id.items()}
    right_dates = {key: sorted({r.trade_date for r in rows})
                   for key, rows in right_by_id.items()}
    cross_source = []
    for contract_id in sorted(set(left_dates) & set(right_dates)):
        ld, rd = left_dates[contract_id], right_dates[contract_id]
        if ld != rd:
            cross_source.append({
                "contract_id": contract_id,
                "left_dates": ld,
                "right_dates": rd,
                "anomaly": "cross_source_trade_date_disagreement",
            })

    prefix_findings = []
    for label, rows in (("left", left), ("right", right)):
        for row in rows:
            prefix = _prefix_date(row.contract_id)
            if prefix is not None and prefix != row.trade_date:
                prefix_findings.append({
                    "source": label,
                    "contract_id": row.contract_id,
                    "recorded_trade_date": row.trade_date,
                    "diagnostic_prefix_date": prefix,
                    "anomaly": "contract_id_prefix_date_disagrees_with_row_date",
                    "prefix_semantics_verified": False,
                })

    return {
        "audit_status": "review_only_identity_anomaly_report",
        "left_contract_rows": len(left),
        "right_contract_rows": len(right),
        "left_within_source_date_collisions": within_source(left_by_id, "left"),
        "right_within_source_date_collisions": within_source(right_by_id, "right"),
        "cross_source_date_disagreements": cross_source,
        "contract_prefix_date_findings": prefix_findings,
        "source_independence_verified": False,
        "trade_date_authority_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "diagnostics_only_no_automatic_date_correction",
    }
