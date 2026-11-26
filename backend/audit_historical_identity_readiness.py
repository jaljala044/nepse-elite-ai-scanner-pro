"""P4.25 evidence-coverage audit for historical security identity and corporate actions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

SECONDARY_START_STATUSES = {
    "verified_secondary_notice",
    "verified_secondary_first_trade_archive_match",
}
ALLOWED_START_STATUSES = SECONDARY_START_STATUSES | {"verified_primary_notice", "unverified"}


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def unique_by_symbol(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        symbol = row.get("symbol", "").strip().upper()
        if not symbol or symbol in result:
            raise ValueError(f"{label}: blank or duplicate symbol {symbol!r}")
        result[symbol] = row
    return result


def audit_historical_identity_readiness(
    lifecycle_path: Path, events_path: Path, identity_path: Path,
    crosswalk_path: Path, snapshot_path: Path, history_dir: Path,
    corporate_actions_path: Path | None = None,
) -> dict:
    snapshot_rows = read_csv(snapshot_path, {"symbol", "security_id", "security_name", "active_status", "snapshot_date"})
    crosswalk_rows = read_csv(crosswalk_path, {"symbol", "security_id", "security_name", "snapshot_date", "active_status", "crosswalk_status"})
    lifecycle_rows = read_csv(lifecycle_path, {
        "security_id", "symbol", "instrument_type", "valid_from", "valid_to",
        "target_in_scope", "valid_from_evidence_status", "valid_from_evidence_uri",
        "valid_from_evidence_note",
    })
    snapshot = unique_by_symbol(snapshot_rows, "security snapshot")
    crosswalk = unique_by_symbol(crosswalk_rows, "equity crosswalk")
    lifecycle = unique_by_symbol(lifecycle_rows, "lifecycle input")
    if len(crosswalk) != 281 or len(lifecycle) != 281:
        raise ValueError("expected exactly 281 current equity crosswalk/lifecycle rows")
    if {row["snapshot_date"] for row in snapshot_rows} != {"2026-11-25"}:
        raise ValueError("unexpected current security snapshot date")

    for symbol, cross in crosswalk.items():
        sec, life = snapshot.get(symbol), lifecycle.get(symbol)
        if sec is None or life is None:
            raise ValueError(f"{symbol}: current snapshot or lifecycle row missing")
        if (cross["snapshot_date"] != "2026-11-25" or cross["active_status"] != "A"
                or cross["crosswalk_status"] != "snapshot_id_match_active_status_A"
                or cross["security_id"] != sec["security_id"]
                or cross["security_name"] != sec["security_name"]
                or sec["active_status"] != "A"):
            raise ValueError(f"{symbol}: current crosswalk/snapshot mismatch")
        if life["security_id"] != cross["security_id"] or life["instrument_type"] != "equity" or life["target_in_scope"].lower() != "true":
            raise ValueError(f"{symbol}: lifecycle/current crosswalk mismatch")
        status = life["valid_from_evidence_status"]
        if status not in ALLOWED_START_STATUSES:
            raise ValueError(f"{symbol}: unsupported lifecycle evidence status {status!r}")
        if life["valid_from"]:
            date.fromisoformat(life["valid_from"])
            if status == "unverified" or not life["valid_from_evidence_uri"] or not life["valid_from_evidence_note"]:
                raise ValueError(f"{symbol}: dated start lacks evidence provenance")
        elif status != "unverified" or life["valid_from_evidence_uri"]:
            raise ValueError(f"{symbol}: undated start must remain unverified")

    start_status = Counter(row["valid_from_evidence_status"] for row in lifecycle_rows)
    dated = [row for row in lifecycle_rows if row["valid_from"]]
    primary_starts = [row for row in dated if row["valid_from_evidence_status"] == "verified_primary_notice"]
    secondary_starts = [row for row in dated if row["valid_from_evidence_status"] in SECONDARY_START_STATUSES]

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity_records = identity.get("records")
    if not isinstance(identity_records, list):
        raise ValueError("historical identity evidence records missing")
    stable_ids = sum(row.get("stable_id") not in (None, "") for row in identity_records)
    verified_dates = sum(row.get("effective_date_verified") is True for row in identity_records)
    recovery = identity.get("security_id_recovery", {})
    predecessor = recovery.get("historical_predecessor_ids", {})
    promotion = recovery.get("promotion", {})
    if predecessor.get("status") != "unresolved":
        raise ValueError("predecessor IDs must remain unresolved without dated evidence")
    promotion_keys = ("stable_ids_assigned", "predecessor_ids_assigned", "history_splicing_authorized",
                      "canonical_universe_promotion_authorized", "training_promotion_authorized")
    if any(promotion.get(key) is not False for key in promotion_keys):
        raise ValueError("historical identity promotion flags must remain false")
    provider = recovery.get("provider_lead", {})
    if provider.get("public_retrieval_status") != "not_acquired" or provider.get("response_body_sha256") is not None:
        raise ValueError("provider schema lead must not be treated as acquired identity data")

    events = read_csv(events_path, {
        "event_id", "security_id", "symbol", "event_type", "event_date",
        "evidence_tier", "source_url", "source_label", "review_status", "notes",
    })
    event_tiers, event_types = Counter(), Counter()
    for row in events:
        date.fromisoformat(row["event_date"])
        event_tiers[row["evidence_tier"]] += 1
        event_types[row["event_type"]] += 1
        sec = snapshot.get(row["symbol"].upper())
        if sec is None or sec["security_id"] != row["security_id"]:
            raise ValueError(f"{row['symbol']}: lifecycle event ID is not the current snapshot ID")
        parsed = urlparse(row["source_url"])
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError(f"{row['symbol']}: invalid event source URL")

    benh = lifecycle.get("BENH")
    if benh is None:
        raise ValueError("BENH lifecycle row missing")
    benh_file = history_dir / "symbols" / "BENH" / "response-01.bin"
    manifest = history_dir / "SHA256SUMS"
    if not benh_file.is_file() or not manifest.is_file():
        raise ValueError("pinned BENH history response or manifest missing")
    manifest_hash = next((line.split()[0] for line in manifest.read_text().splitlines()
                          if line.strip().endswith("symbols/BENH/response-01.bin")), None)
    benh_hash = hashlib.sha256(benh_file.read_bytes()).hexdigest()
    if not manifest_hash or manifest_hash != benh_hash:
        raise ValueError("BENH raw response SHA-256 differs from pinned manifest")
    payload = json.loads(benh_file.read_text(encoding="utf-8"))
    history_rows = payload.get("content") if isinstance(payload, dict) else payload
    by_day = {str(row.get("businessDate", ""))[:10]: row for row in history_rows}
    zero, first_trade = by_day.get("2026-10-14"), by_day.get("2026-10-15")
    if zero is None or first_trade is None:
        raise ValueError("BENH 14/15-Oct official history rows missing")
    if (str(zero.get("totalTrades")), str(zero.get("totalTradedQuantity")), str(zero.get("totalTradedValue"))) != ("0", "0", "0"):
        raise ValueError("BENH 14-Oct must remain explicit zero activity")
    if (str(first_trade.get("totalTrades")), str(first_trade.get("totalTradedQuantity")), str(first_trade.get("totalTradedValue"))) != ("9", "90", "26634"):
        raise ValueError("BENH 15-Oct first positive row changed")
    if benh["valid_from"] != "2026-10-15" or benh["valid_from_evidence_status"] != "verified_secondary_first_trade_archive_match":
        raise ValueError("BENH lifecycle first-trade context changed; review before classification")

    ca_present = corporate_actions_path is not None and corporate_actions_path.is_file()
    ca_count = 0
    if ca_present:
        ca_count = len(read_csv(corporate_actions_path, {"action_id", "security_id", "action_type", "ex_date", "source_tier", "status", "evidence_id"}))

    return {
        "schema_version": "1.0",
        "audit_status": "historical_identity_readiness_review_only",
        "current_snapshot_date": "2026-11-25",
        "crosswalk_date": "2026-11-26",
        "current_equity_count": len(crosswalk),
        "current_snapshot_id_matches": len(crosswalk),
        "lifecycle_start_evidence": {
            "row_count": len(lifecycle_rows),
            "dated_start_count": len(dated),
            "primary_start_evidence_count": len(primary_starts),
            "secondary_start_evidence_count": len(secondary_starts),
            "undated_start_count": len(lifecycle_rows) - len(dated),
            "status_counts": dict(sorted(start_status.items())),
            "sha256": hashlib.sha256(lifecycle_path.read_bytes()).hexdigest(),
        },
        "historical_identity_evidence": {
            "record_count": len(identity_records),
            "identity_or_event_supported_count": identity.get("summary", {}).get("identity_or_event_supported"),
            "probable_alias_only_count": identity.get("summary", {}).get("probable_alias_only"),
            "stable_id_present_count": stable_ids,
            "effective_date_verified_count": verified_dates,
            "predecessor_id_status": predecessor.get("status"),
            "unresolved_predecessor_symbols": predecessor.get("symbols", []),
            "provider_lead_status": provider.get("public_retrieval_status"),
            "successor_snapshot_scope": recovery.get("successor_snapshot", {}).get("scope"),
        },
        "typed_security_lifecycle_events": {
            "event_count": len(events),
            "evidence_tier_counts": dict(sorted(event_tiers.items())),
            "event_type_counts": dict(sorted(event_types.items())),
            "primary_notice_count": event_tiers.get("primary_nepse_notice", 0),
            "raw_event_source_bytes_archived_count": 0,
            "historical_security_ids_verified": False,
            "first_executed_trade_dates_verified_by_event_ledger": False,
        },
        "BENH_first_trade_reconciliation": {
            "raw_file": "symbols/BENH/response-01.bin",
            "response_sha256": benh_hash,
            "response_row_count": len(history_rows),
            "2026-10-14": {"trades": "0", "shares": "0", "turnover": "0", "status": "EXPLICIT_ZERO_ACTIVITY"},
            "2026-10-15": {"trades": "9", "shares": "90", "turnover": "26634", "status": "FIRST_POSITIVE_ACTIVITY_ROW"},
            "lifecycle_valid_from": benh["valid_from"],
            "lifecycle_evidence_status": benh["valid_from_evidence_status"],
            "lifecycle_date_is_secondary": True,
            "contract_level_floorsheet_verified": False,
        },
        "corporate_action_evidence": {
            "evidence_file_supplied": ca_present,
            "record_count": ca_count,
            "adjustment_admission_allowed": False,
            "reason": "no dated primary corporate-action evidence dataset supplied to this audit" if not ca_present else "records require independent validation",
        },
        "runtime_gates": {
            "security_resolution_requires_primary_nepse_or_cdsc_evidence": True,
            "stable_id_and_effective_date_both_required": True,
            "secondary_lifecycle_dates_are_context_only": True,
            "corporate_action_adjustment_requires_primary_source_factor_and_independent_review": True,
            "raw_ohlcv_adjustment_applied": False,
        },
        "historical_identity_admission_allowed": False,
        "historical_join_admission_allowed": False,
        "corporate_action_adjustment_admission_allowed": False,
        "canonical_universe_promotion_allowed": False,
        "training_promotion_allowed": False,
        "policy": "current_snapshot_and_secondary_lifecycle_evidence_are_context_only_no_historical_id_or_adjustment_without_primary_effective_date_and_stable_id_proof",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--identity-evidence", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--history-window-dir", type=Path, required=True)
    parser.add_argument("--corporate-actions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_historical_identity_readiness(
        args.lifecycle, args.events, args.identity_evidence,
        args.crosswalk, args.snapshot, args.history_window_dir,
        args.corporate_actions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "current_equity_count": report["current_equity_count"],
        "lifecycle_start_evidence": report["lifecycle_start_evidence"],
        "historical_identity_evidence": report["historical_identity_evidence"],
        "typed_security_lifecycle_events": report["typed_security_lifecycle_events"],
        "BENH_first_trade_reconciliation": report["BENH_first_trade_reconciliation"],
        "corporate_action_evidence": report["corporate_action_evidence"],
        "historical_join_admission_allowed": False,
        "corporate_action_adjustment_admission_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
