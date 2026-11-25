"""End-to-end floorsheet CSV -> contract audit -> broker identity -> aggregation."""
from __future__ import annotations

from app.floorsheet_csv_adapter import CsvFloorsheetMapping, parse_floorsheet_csv
from app.floorsheet_contract import reconcile_floorsheet_rows
from app.floorsheet_broker_join import resolve_contract_brokers
from app.broker_aggregation import aggregate_broker_observations


def run_floorsheet_pipeline(payload: bytes, *, source_id: str,
                            mapping: CsvFloorsheetMapping, broker_links: list) -> dict:
    """Run explicit source mapping and retain rejected/duplicate rows in audit outputs.

    Only unique contracts without gross-amount exceptions contribute to broker
    aggregates. Other rows remain in the result with their reason and lineage.
    """
    parsed = parse_floorsheet_csv(payload, source_id=source_id, mapping=mapping)
    reconciled = reconcile_floorsheet_rows(parsed["rows"])
    eligible = [contract for contract, audit in zip(parsed["rows"], reconciled["rows"])
                if audit["duplicate_disposition"] == "unique"
                and not audit["amount_reconciliation_exception"]]
    joined = resolve_contract_brokers(eligible, broker_links, source_id=source_id)
    aggregates = aggregate_broker_observations(joined["rows"])
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
        "promotion_allowed": False,
        "source_specific_mapping_verified": parsed["source_specific_mapping_verified"],
        "policy": "audit_all_rows_aggregate_unique_clean_contracts_only",
    }
