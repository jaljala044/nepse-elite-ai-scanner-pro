import unittest
from dataclasses import replace
from decimal import Decimal
from app.floorsheet_contract import FloorsheetContract
from app.floorsheet_daily_summaries import summarize_daily_contracts

DAY = "2026-11-25"

def contract(i, symbol="AAA", buyer="01", seller="02", quantity="10", rate="100"):
    q, r = Decimal(quantity), Decimal(rate)
    return FloorsheetContract("fixture", "a"*64, i, DAY, str(i), symbol, buyer, seller, q, r, q*r)

class DailySummaryTests(unittest.TestCase):
    def summary(self, rows):
        return summarize_daily_contracts(rows, expected_date=DAY)

    def test_stock_totals(self):
        s = self.summary([contract(1), contract(2, quantity="20"), contract(3, symbol="BBB")])
        self.assertEqual(s["totals"], {"transactions":3,"quantity":"40","amount":"4000"})
        self.assertEqual(s["stock_rows"][0]["quantity"], "30")
        self.assertEqual(len(s["stock_rows"]), 2)

    def test_broker_buy_and_sell(self):
        s = self.summary([contract(1), contract(2,buyer="02",seller="01",quantity="3")])
        a,b = s["broker_rows"]
        self.assertEqual((a["buy_quantity"],a["sell_quantity"],a["net_quantity"]),("10","3","7"))
        self.assertEqual((b["net_quantity"],b["net_amount"]),("-7","-700"))

    def test_same_broker_both_sides(self):
        s = self.summary([contract(1,buyer="01",seller="01")])
        self.assertEqual(s["broker_rows"][0]["net_amount"],"0")
        self.assertEqual(s["totals"]["transactions"],1)
        self.assertEqual(s["broker_rows"][0]["buy_transactions"],1)
        self.assertEqual(s["broker_rows"][0]["sell_transactions"],1)

    def test_broker_symbol_isolation(self):
        s = self.summary([contract(1),contract(2,symbol="BBB",buyer="02",seller="01")])
        self.assertEqual(len(s["broker_symbol_rows"]),4)
        self.assertEqual(s["broker_rows"][0]["net_quantity"],"0")

    def test_duplicate_contract(self):
        row=contract(1)
        for other in (row,replace(row,quantity=Decimal(11),amount=Decimal(1100))):
            with self.subTest(other=other), self.assertRaises(ValueError):
                self.summary([row,other])

    def test_bad_amount(self):
        with self.assertRaises(ValueError):
            self.summary([replace(contract(1),amount=Decimal("999"))])

    def test_fractional_quantity(self):
        with self.assertRaises(ValueError):
            self.summary([contract(1,quantity="1.5")])

    def test_mixed_provenance(self):
        with self.assertRaises(ValueError):
            self.summary([contract(1),replace(contract(2),source_payload_sha256="b"*64)])

    def test_wrong_date(self):
        with self.assertRaises(ValueError):
            self.summary([replace(contract(1),trade_date="2026-11-26")])

    def test_empty_and_review_only(self):
        with self.assertRaises(ValueError):
            self.summary([])
        s=self.summary([contract(1)])
        self.assertFalse(s["canonical_promotion_allowed"])
        self.assertFalse(s["broker_identity_verified"])
        self.assertFalse(s["session_completeness_verified"])

if __name__ == "__main__":
    unittest.main()
