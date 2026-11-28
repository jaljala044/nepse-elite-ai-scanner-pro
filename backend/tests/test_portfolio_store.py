import os
import tempfile
import unittest
from pathlib import Path

from app import portfolio_store as store


class PortfolioStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_PORTFOLIO_DATABASE"] = str(Path(self.tmp.name) / "portfolio.duckdb")

    def tearDown(self):
        os.environ.pop("NEPSE_PORTFOLIO_DATABASE", None)
        self.tmp.cleanup()

    def test_owner_scoped_portfolio_and_holding_crud(self):
        p = store.create_portfolio("user-a", "Long term")
        self.assertEqual(len(store.list_portfolios("user-a")), 1)
        self.assertEqual(store.list_portfolios("user-b"), [])
        self.assertIsNone(store.list_holdings("user-b", p["portfolio_id"]))
        h = store.create_holding("user-a", p["portfolio_id"], "cfcl",
                                 horizon="one_to_three_months", risk_preference="aggressive_growth")
        self.assertEqual(h["symbol"], "CFCL")
        self.assertEqual(len(store.list_holdings("user-a", p["portfolio_id"])), 1)
        self.assertFalse(store.rename_portfolio("user-b", p["portfolio_id"], "stolen"))
        self.assertTrue(store.rename_portfolio("user-a", p["portfolio_id"], "Retirement"))
        self.assertTrue(store.delete_portfolio("user-a", p["portfolio_id"]))
        self.assertEqual(store.list_portfolios("user-a"), [])

    def test_transaction_is_owner_scoped_and_decimal_safe(self):
        p = store.create_portfolio("user-a", "Main")
        h = store.create_holding("user-a", p["portfolio_id"], "CFCL")
        tx = store.add_transaction("user-a", p["portfolio_id"], h["holding_id"],
                                   transaction_id="tx-1", transaction_type="buy",
                                   trade_date="2026-01-01", quantity=2500,
                                   unit_price="593.125", fees="12.50")
        self.assertEqual(tx["unit_price"], "593.125")
        self.assertEqual(store.list_transactions("user-b", p["portfolio_id"], h["holding_id"]), None)
        self.assertEqual(store.list_transactions("user-a", p["portfolio_id"], h["holding_id"])[0]["fees"], "12.5")
        self.assertIsNone(store.add_transaction("user-b", p["portfolio_id"], h["holding_id"],
                          transaction_id="tx-2", transaction_type="buy", trade_date="2026-01-02",
                          quantity=1, unit_price="1"))

    def test_rejects_invalid_transactions_and_non_chronological_append(self):
        p = store.create_portfolio("owner", "Main")
        h = store.create_holding("owner", p["portfolio_id"], "CFCL")
        with self.assertRaisesRegex(ValueError, "whole share"):
            store.add_transaction("owner", p["portfolio_id"], h["holding_id"],
                                  transaction_id="bad", transaction_type="buy", trade_date="2026-01-01",
                                  quantity=1.5, unit_price="10")
        store.add_transaction("owner", p["portfolio_id"], h["holding_id"], transaction_id="one",
                              transaction_type="buy", trade_date="2026-01-02", quantity=1, unit_price="10")
        with self.assertRaisesRegex(ValueError, "chronological"):
            store.add_transaction("owner", p["portfolio_id"], h["holding_id"], transaction_id="two",
                                  transaction_type="buy", trade_date="2026-01-01", quantity=1, unit_price="10")

    def test_owner_id_is_mandatory_and_portfolio_delete_cascades(self):
        with self.assertRaisesRegex(ValueError, "owner_id"):
            store.list_portfolios("")
        p = store.create_portfolio("owner", "Main")
        h = store.create_holding("owner", p["portfolio_id"], "CFCL")
        store.add_transaction("owner", p["portfolio_id"], h["holding_id"], transaction_id="one",
                              transaction_type="buy", trade_date="2026-01-01", quantity=1, unit_price="10")
        store.delete_portfolio("owner", p["portfolio_id"])
        self.assertEqual(store.list_portfolios("owner"), [])


if __name__ == "__main__":
    unittest.main()
