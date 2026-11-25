import unittest
from datetime import date
from app.floorsheet_csv_adapter import CsvFloorsheetMapping
from app.floorsheet_broker_join import resolve_contract_brokers
from app.broker_identity import BrokerIdentityLink
from app.floorsheet_pipeline import run_floorsheet_pipeline


MAPPING = CsvFloorsheetMapping({
    "trade_date": "Date", "contract_id": "S.N.", "symbol": "Symbol",
    "buyer_broker_code": "Buyer", "seller_broker_code": "Seller",
    "quantity": "Qty", "rate": "Rate", "amount": "Amount",
})
LINKS = [
    BrokerIdentityLink("fixture", "11", "BROKER-11", "verified", "E11",
                       valid_from=date(2020, 1, 1)),
    BrokerIdentityLink("fixture", "22", "BROKER-22", "verified", "E22",
                       valid_from=date(2020, 1, 1)),
]


class FloorsheetPipelineTests(unittest.TestCase):
    def test_end_to_end_exact_broker_aggregation(self):
        payload = (
            "Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
            "2026-11-24,1,NABIL,11,22,2,100,200\n"
            "2026-11-24,2,NABIL,11,22,3,100,300\n"
        ).encode()
        result = run_floorsheet_pipeline(payload, source_id="fixture",
                                         mapping=MAPPING, broker_links=LINKS)
        self.assertEqual(result["eligible_contract_count"], 2)
        self.assertEqual(result["broker_aggregates"]["input_party_observation_rows"], 4)
        buy = next(x for x in result["broker_aggregates"]["aggregates"]
                   if x["side"] == "buy")
        self.assertEqual(buy["amount"], "500")
        self.assertEqual(buy["quantity"], "5")

    def test_duplicate_contract_rows_are_retained_but_not_aggregated(self):
        line = "2026-11-24,1,NABIL,11,22,2,100,200"
        payload = ("Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n" +
                   line + "\n" + line + "\n").encode()
        result = run_floorsheet_pipeline(payload, source_id="fixture",
                                         mapping=MAPPING, broker_links=LINKS)
        self.assertEqual(result["contract_reconciliation"]["counts"]["exact_duplicate"], 2)
        self.assertEqual(result["eligible_contract_count"], 0)
        self.assertEqual(result["contract_reconciliation"]["rows_discarded"], 0)

    def test_unmapped_broker_parties_remain_in_aggregate_coverage(self):
        payload = ("Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
                   "2026-11-24,1,NABIL,99,22,2,100,200\n").encode()
        result = run_floorsheet_pipeline(payload, source_id="fixture",
                                         mapping=MAPPING, broker_links=LINKS)
        coverage = result["broker_aggregates"]["coverage"]
        buy = next(x for x in coverage if x["side"] == "buy")
        self.assertEqual(buy["unresolved_observation_count"], 1)
        self.assertEqual(buy["verified_observation_count"], 0)

    def test_amount_exception_is_retained_but_excluded_from_aggregate(self):
        payload = ("Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
                   "2026-11-24,1,NABIL,11,22,2,100,250\n").encode()
        result = run_floorsheet_pipeline(payload, source_id="fixture",
                                         mapping=MAPPING, broker_links=LINKS)
        self.assertEqual(result["contract_reconciliation"]["counts"]["amount_reconciliation_exception"], 1)
        self.assertEqual(result["eligible_contract_count"], 0)

    def test_parser_rejections_are_reported(self):
        payload = ("Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
                   "2026-11-24,1,NABIL,11,22,bad,100,200\n").encode()
        result = run_floorsheet_pipeline(payload, source_id="fixture",
                                         mapping=MAPPING, broker_links=LINKS)
        self.assertEqual(len(result["rejected_rows"]), 1)
        self.assertEqual(result["rejected_rows"][0]["raw_source_row"]["Qty"], "bad")
        self.assertEqual(result["rejected_rows"][0]["source_row_number"], 2)
        self.assertEqual(result["eligible_contract_count"], 0)


    def test_urek_profile_preserves_unmapped_broker_codes_and_reconciles_controls(self):
        from app.floorsheet_source_profiles import (
            UREK_PINNED_REVISION,
            urek_floorsheet_mapping,
        )

        source_id = (
            "urekmazino69/Nepse-floorsheet-and-indices@"
            + UREK_PINNED_REVISION
            + "/floorsheet/2026-08-26.csv"
        )
        payload = (
            "contract_no,calculation_date,time,stock_symbol,sector,buyer,seller,"
            "quantity,rate,amount,id\n"
            "00001,2026-08-26,,NABIL,Commercial Banks,11,42,10,100,1000,101\n"
            "00002,2026-08-26,,NABIL,Commercial Banks,12,42,5,110,550,102\n"
        ).encode("utf-8")
        result = run_floorsheet_pipeline(
            payload,
            source_id=source_id,
            mapping=urek_floorsheet_mapping(),
            broker_links=[],
            source_controls=[{
                "source_id": source_id,
                "trade_date": "2026-08-26",
                "contract_count": 2,
                "gross_amount": "1550",
                "party_observation_count": 4,
            }],
        )
        self.assertEqual(result["eligible_contract_count"], 2)
        self.assertEqual(result["source_control_reconciliation"]["status"], "passed")
        self.assertEqual(
            result["source_control_reconciliation"]["results"][0]["observed_gross_amount"],
            "1550",
        )
        aggregates = result["broker_aggregates"]["aggregates"]
        buyers = [row for row in aggregates if row["side"] == "buy"]
        sellers = [row for row in aggregates if row["side"] == "sell"]
        self.assertEqual({row["source_broker_code"] for row in buyers}, {"11", "12"})
        self.assertEqual(len(buyers), 2)
        self.assertEqual(len(sellers), 1)
        self.assertEqual(sellers[0]["source_broker_code"], "42")
        self.assertEqual(sellers[0]["contract_count"], 2)
        self.assertTrue(all(row["broker_entity_id"] is None for row in aggregates))

    def test_verified_broker_entity_merges_multiple_source_codes(self):
        from app.floorsheet_source_profiles import urek_floorsheet_mapping

        payload = (
            "contract_no,calculation_date,time,stock_symbol,sector,buyer,seller,"
            "quantity,rate,amount,id\n"
            "00001,2026-08-26,,NABIL,Commercial Banks,11,42,10,100,1000,101\n"
            "00002,2026-08-26,,NABIL,Commercial Banks,12,42,5,110,550,102\n"
        ).encode("utf-8")
        links = [
            BrokerIdentityLink("urek", "11", "BROKER-11", "verified", "review-11",
                               valid_from=date(2020, 1, 1)),
            BrokerIdentityLink("urek", "12", "BROKER-11", "verified", "review-12",
                               valid_from=date(2020, 1, 1)),
        ]
        result = run_floorsheet_pipeline(
            payload, source_id="urek", mapping=urek_floorsheet_mapping(),
            broker_links=links,
        )
        buyers = [
            row for row in result["broker_aggregates"]["aggregates"]
            if row["side"] == "buy"
        ]
        self.assertEqual(len(buyers), 1)
        self.assertEqual(buyers[0]["broker_entity_id"], "BROKER-11")
        self.assertEqual(buyers[0]["source_broker_codes"], ["11", "12"])
        self.assertEqual(buyers[0]["amount"], "1550")

    def test_external_control_total_mismatch_is_exposed_without_repair(self):
        source = "fixture"
        payload = (
            "Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
            "2026-11-24,1,NABIL,11,22,2,100,200\n"
        ).encode("utf-8")
        result = run_floorsheet_pipeline(
            payload, source_id=source, mapping=MAPPING, broker_links=LINKS,
            source_controls=[{
                "source_id": source,
                "trade_date": "2026-11-24",
                "contract_count": 1,
                "gross_amount": "250",
                "party_observation_count": 2,
            }],
        )
        self.assertEqual(result["source_control_reconciliation"]["status"], "failed")
        self.assertIn(
            "gross_amount",
            result["source_control_reconciliation"]["results"][0]["differences"],
        )
        self.assertEqual(result["eligible_contract_count"], 1)

    def test_missing_independent_controls_are_not_claimed_as_passed(self):
        payload = (
            "Date,S.N.,Symbol,Buyer,Seller,Qty,Rate,Amount\n"
            "2026-11-24,1,NABIL,11,22,2,100,200\n"
        ).encode("utf-8")
        result = run_floorsheet_pipeline(
            payload, source_id="fixture", mapping=MAPPING, broker_links=LINKS
        )
        self.assertEqual(
            result["source_control_reconciliation"]["status"], "not_run"
        )



if __name__ == "__main__":
    unittest.main()
