"""End-to-end floorsheet CSV -> contract audit -> broker identity -> aggregation."""
from __future__ import annotations

from app.floorsheet_csv_adapter import CsvFloorsheetMapping, parse_floorsheet_csv
from app.floorsheet_contract import reconcile_floorsheet_rows
from app.floorsheet_broker_join import resolve_contract_brokers
from app.broker_aggregation import (
    aggregate_broker_observations,
    reconcile_source_control_totals,
)


def run_floorsheet_pipeline(payload: bytes, *, source_id: str,
                            mapping: CsvFloorsheetMapping, broker_links: list,
                            source_controls: list[dict] | None = None) -> dict:
    """Run explicit source mapping and retain rejected/duplicate rows in audit outputs.

    Only unique contracts without gross-amount exceptions contribute to broker
    aggregates. Other rows remain in the result with their reason and lineage.
    """
    if source_controls is not None and (not isinstance(source_controls, list) or not source_controls):
        raise ValueError("source_controls must be a non-empty list when supplied")
    parsed = parse_floorsheet_csv(payload, source_id=source_id, mapping=mapping)
    reconciled = reconcile_floorsheet_rows(parsed["rows"])
    eligible = [contract for contract, audit in zip(parsed["rows"], reconciled["rows"])
                if audit["duplicate_disposition"] == "unique"
                and not audit["amount_reconciliation_exception"]]
    joined = resolve_contract_brokers(eligible, broker_links, source_id=source_id)
    aggregates = aggregate_broker_observations(joined["rows"])
    if source_controls is None:
        control_reconciliation = {
            "status": "not_run",
            "reason": "independent_source_controls_not_supplied",
            "passed_source_dates": 0,
            "failed_source_dates": 0,
            "results": [],
        }
    else:
        # Reconcile controls against all parseable source contracts, including
        # duplicates and amount exceptions; never compare source totals to the
        # filtered subset used for feature aggregation.
        all_contract_parties = resolve_contract_brokers(
            parsed["rows"], broker_links, source_id=source_id
        )
        control_reconciliation = reconcile_source_control_totals(
            all_contract_parties["rows"], source_controls
        )
        control_reconciliation["status"] = (
            "passed" if control_reconciliation["failed_source_dates"] == 0 else "failed"
        )
    return {
        "source_id": source_id,
        "source_payload_sha256": parsed["source_payload_sha256"],
        "input_data_rows": parsed["input_data_rows"],
        "parsed_contract_rows": parsed["parsed_rows"],
        "rejected_rows": parsed["errors"],
        "contract_reconciliation": reconciled,
        "eligible_contract_count": len(eligible),
        "broker_resolution": {
            key: value for key, value in joined.items() if key != "rows"
        },
        "broker_aggregates": aggregates,
        "source_control_reconciliation": control_reconciliation,
        "promotion_allowed": False,
        "source_specific_mapping_verified": parsed["source_specific_mapping_verified"],
        "policy": "audit_all_rows_aggregate_unique_clean_contracts_only",
    }
