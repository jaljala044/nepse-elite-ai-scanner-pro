import unittest
from decimal import Decimal

from app.broker_ingestion import payload_hash
from app.floorsheet_broker_ingestion_adapter import (
    FloorsheetBrokerAdapterError, adapt_floorsheet_parties_to_broker_batch,
)


def party_rows(contracts=1, unresolved=None):
    rows=[]
    for i in range(contracts):
        contract=f"C{i+1}"
        for side, broker, code in (("buy","ENTITY-BUY","101"),("sell","ENTITY-SELL","202")):
            status="unmapped" if unresolved==(i,side) else "verified"
            rows.append({
                "source_id":"SRC-A","source_payload_sha256":f"{i+1:064x}",
                "source_row_number":i+2,"trade_date":"2026-11-25","contract_id":contract,
                "symbol":"CFCL","side":side,"source_broker_code":code,
                "broker_entity_id":None if status!="verified" else broker,
                "identity_status":status,"identity_evidence_ids":[] if status!="verified" else [f"ID-{broker}"],
                "quantity":"2","amount":"100",
            })
    return rows


def setup(rows, controls=None, security_registry=None, **kwargs):
    join={"input_contract_rows":len(rows)//2,"party_observation_rows":len(rows),
          "rows":rows,"counts_by_identity_status":{}}
    default={
        "source_controls":([{"source_id":"SRC-A","trade_date":"2026-11-25",
            "contract_count":len(rows)//2,"party_observation_count":len(rows),
            "gross_amount":str(Decimal("100")*(len(rows)//2)),
            "quantity":str(Decimal("2")*(len(rows)//2))}] if controls is None else controls),
        "security_registry":security_registry or [{"symbol":"CFCL","security_id":"SEC-CFCL",
            "status":"verified","effective_from":"2020-01-01","effective_to":None}],
        "verified_sessions":{"2026-11-25"},
        "verified_session_finality":{"2026-11-25":"2026-11-25T16:00:00+05:45"},
        "expected_source_ids":{"SRC-A"},"received_source_ids":{"SRC-A"},
        "available_at":"2026-11-26T09:00:00+05:45",
    }
    default.update(kwargs)
    return adapt_floorsheet_parties_to_broker_batch(join,**default)


class FloorsheetBrokerIngestionAdapterTests(unittest.TestCase):
    def test_p443_held_sessions_rejected_before_aggregation(self):
        for day in ("2024-08-14", "2024-08-18"):
            with self.subTest(day=day):
                rows = party_rows()
                for row in rows:
                    row["trade_date"] = day
                with self.assertRaisesRegex(FloorsheetBrokerAdapterError, "p443_session_quarantined"):
                    setup(rows)

    def test_p443_archive_hash_rejected_even_with_different_session(self):
        from app.floorsheet_broker_ingestion_adapter import P443_HELD_ARCHIVE_HASHES
        self.assertEqual(len(P443_HELD_ARCHIVE_HASHES), 4)
        for digest in P443_HELD_ARCHIVE_HASHES:
            for field in ("source_payload_sha256", "source_archive_sha256"):
                with self.subTest(digest=digest, field=field):
                    rows = party_rows()
                    rows[0][field] = digest.upper()
                    with self.assertRaisesRegex(FloorsheetBrokerAdapterError, "p443_archive_quarantined"):
                        setup(rows)

    def test_p443_invalid_trade_dates_rejected(self):
        for day in (None, "2026-02-30", "20261125", "2026-11-25T12:00:00"):
            with self.subTest(day=day):
                rows = party_rows()
                rows[0]["trade_date"] = day
                with self.assertRaisesRegex(FloorsheetBrokerAdapterError, "trade_date"):
                    setup(rows)

    def test_verified_pairs_produce_memory_eligible_batch(self):
        result=setup(party_rows())
        self.assertTrue(result["memory_eligible"], repr(result["report"]))
        self.assertEqual(result["derived_ingestion_rows"],2)
        self.assertEqual({r["broker_id"] for r in result["report"].accepted},
                         {"ENTITY-BUY","ENTITY-SELL"})

    def test_unmapped_identity_stays_in_denominator_and_blocks_when_below_threshold(self):
        result=setup(party_rows(unresolved=(0,"sell")))
        self.assertFalse(result["memory_eligible"])
        self.assertEqual(result["unresolved_party_rows"],1)
        self.assertEqual(result["report"].accepted,[])
        self.assertIn("identity_coverage_below_threshold",
                      [q.get("reason") for q in result["report"].quarantined if "reason" in q])

    def test_exactly_95_percent_identity_coverage_is_eligible(self):
        result=setup(party_rows(contracts=20,unresolved=(0,"sell")))
        self.assertTrue(result["memory_eligible"],repr(result["report"]))
        self.assertEqual(result["unresolved_party_rows"],1)

    def test_source_control_mismatch_blocks_promotion(self):
        controls=[{"source_id":"SRC-A","trade_date":"2026-11-25",
            "contract_count":99,"party_observation_count":40,"gross_amount":"2000","quantity":"40"}]
        result=setup(party_rows(20),controls=controls)
        self.assertFalse(result["memory_eligible"])

    def test_security_mapping_must_be_effective_dated_and_verified(self):
        registry=[{"symbol":"CFCL","security_id":"SEC-CFCL","status":"verified",
                   "effective_from":"2026-11-26","effective_to":None}]
        result=setup(party_rows(),security_registry=registry)
        self.assertFalse(result["memory_eligible"])
        self.assertTrue(result["security_mapping_failures"])

    def test_missing_session_finality_blocks_promotion(self):
        result=setup(party_rows(),verified_session_finality={})
        self.assertFalse(result["memory_eligible"])

    def test_incomplete_source_inventory_blocks_promotion(self):
        result=setup(party_rows(),received_source_ids=set())
        self.assertFalse(result["memory_eligible"])

    def test_bad_contract_party_pair_rejected(self):
        rows=party_rows()
        rows.pop()
        join={"input_contract_rows":1,"party_observation_rows":1,"rows":rows}
        with self.assertRaises(FloorsheetBrokerAdapterError):
            adapt_floorsheet_parties_to_broker_batch(join,source_controls=[],
                security_registry=[],verified_sessions=set(),verified_session_finality={},
                expected_source_ids={"SRC-A"},received_source_ids={"SRC-A"},
                available_at="2026-11-26T09:00:00+05:45")

    def test_empty_controls_fail_closed(self):
        result=setup(party_rows(),controls=[])
        self.assertFalse(result["memory_eligible"])

    def test_invalid_identity_coverage_threshold_rejected(self):
        with self.assertRaises(FloorsheetBrokerAdapterError):
            setup(party_rows(),identity_coverage_threshold=Decimal("0"))


if __name__=="__main__": unittest.main()
