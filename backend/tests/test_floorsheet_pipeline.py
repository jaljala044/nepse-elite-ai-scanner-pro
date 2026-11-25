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


if __name__ == "__main__":
    unittest.main()
