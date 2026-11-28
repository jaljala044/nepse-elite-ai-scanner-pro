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

    def test_owner_scoped_portfolio_and_holding_round_trip(self):
        portfolio = store.create_portfolio("user-a", "Retirement")
        self.assertEqual(len(store.list_portfolios("user-a")), 1)
        self.assertEqual(store.list_portfolios("user-b"), [])
        holding = store.add_holding("user-a", portfolio["portfolio_id"], "cfcl",
                                    horizon="one_to_three_months",
                                    risk_preference="aggressive_growth")
        self.assertEqual(store.list_holdings("user-a", portfolio["portfolio_id"])[0]["symbol"], "CFCL")
        self.assertEqual(store.list_holdings("user-b", portfolio["portfolio_id"]), [])
        self.assertEqual(holding["horizon"], "one_to_three_months")

    def test_foreign_owner_cannot_rename_or_delete_portfolio(self):
        portfolio = store.create_portfolio("owner-a", "Private")
        pid = portfolio["portfolio_id"]
        self.assertFalse(store.rename_portfolio("owner-b", pid, "Stolen"))
        self.assertFalse(store.delete_portfolio("owner-b", pid))
        self.assertEqual(store.list_portfolios("owner-a")[0]["name"], "Private")

    def test_transaction_storage_and_accounting_validation(self):
        portfolio = store.create_portfolio("owner", "Main")
        holding = store.add_holding("owner", portfolio["portfolio_id"], "CFCL")
        pid, hid = portfolio["portfolio_id"], holding["holding_id"]
        store.add_transaction("owner", pid, hid, transaction_type="buy",
                              trade_date="2026-01-01", quantity=10,
                              unit_price="100", fees="10", transaction_id="buy-1")
        store.add_transaction("owner", pid, hid, transaction_type="sell",
                              trade_date="2026-01-03", quantity=4,
                              unit_price="120", fees="5", transaction_id="sell-1")
        rows = store.list_transactions("owner", pid, hid)
        self.assertEqual([r["transaction_id"] for r in rows], ["buy-1", "sell-1"])
        self.assertEqual(rows[0]["unit_price"], "100.00000000")
        with self.assertRaisesRegex(ValueError, "duplicate transaction_id"):
            store.add_transaction("owner", pid, hid, transaction_type="buy",
                                  trade_date="2026-01-04", quantity=1,
                                  unit_price="100", transaction_id="buy-1")

    def test_oversell_and_non_chronological_trade_fail_without_write(self):
        portfolio = store.create_portfolio("owner", "Main")
        holding = store.add_holding("owner", portfolio["portfolio_id"], "NABIL")
        pid, hid = portfolio["portfolio_id"], holding["holding_id"]
        store.add_transaction("owner", pid, hid, transaction_type="buy",
                              trade_date="2026-01-02", quantity=2, unit_price="100")
        with self.assertRaisesRegex(ValueError, "sell exceeds available shares"):
            store.add_transaction("owner", pid, hid, transaction_type="sell",
                                  trade_date="2026-01-03", quantity=3, unit_price="110")
        with self.assertRaisesRegex(ValueError, "chronological"):
            store.add_transaction("owner", pid, hid, transaction_type="buy",
                                  trade_date="2026-01-01", quantity=1, unit_price="90")
        self.assertEqual(len(store.list_transactions("owner", pid, hid)), 1)

    def test_invalid_horizon_risk_symbol_and_quantity_are_rejected(self):
        portfolio = store.create_portfolio("owner", "Main")
        with self.assertRaisesRegex(ValueError, "horizon"):
            store.add_holding("owner", portfolio["portfolio_id"], "CFCL", horizon="tomorrow")
        with self.assertRaisesRegex(ValueError, "risk preference"):
            store.add_holding("owner", portfolio["portfolio_id"], "CFCL", risk_preference="YOLO")
        with self.assertRaisesRegex(ValueError, "symbol"):
            store.add_holding("owner", portfolio["portfolio_id"], "../CFCL")
        holding = store.add_holding("owner", portfolio["portfolio_id"], "CFCL")
        with self.assertRaisesRegex(ValueError, "whole share"):
            store.add_transaction("owner", portfolio["portfolio_id"], holding["holding_id"],
                                  transaction_type="buy", trade_date="2026-01-01",
                                  quantity=1.5, unit_price="100")

    def test_portfolio_delete_cascades_only_within_owner_scope(self):
        a = store.create_portfolio("owner-a", "A")
        h = store.add_holding("owner-a", a["portfolio_id"], "CFCL")
        store.add_transaction("owner-a", a["portfolio_id"], h["holding_id"],
                              transaction_type="buy", trade_date="2026-01-01",
                              quantity=1, unit_price="100")
        b = store.create_portfolio("owner-b", "B")
        self.assertTrue(store.delete_portfolio("owner-a", a["portfolio_id"]))
        self.assertEqual(store.list_holdings("owner-a", a["portfolio_id"]), [])
        self.assertEqual(store.list_portfolios("owner-b")[0]["portfolio_id"], b["portfolio_id"])

    def test_empty_owner_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner_id"):
            store.list_portfolios(" ")


if __name__ == "__main__":
    unittest.main()
