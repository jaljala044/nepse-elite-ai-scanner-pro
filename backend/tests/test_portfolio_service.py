import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import portfolio_service as service


class PortfolioServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {
            "NEPSE_PORTFOLIO_DB": str(Path(self.tmp.name) / "portfolio.sqlite3")
        })
        self.env.start()
        self.owner = "user-a"
        self.portfolio = service.create_portfolio(self.owner, "Core")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def tx(self, side, qty, price, fees, day, key=None):
        return service.add_transaction(
            self.owner, self.portfolio["id"], symbol="CFCL", side=side,
            quantity=qty, price=price, fees=fees, trade_date=day,
            idempotency_key=key,
        )

    def test_weighted_average_cost_and_realized_pnl(self):
        self.tx("BUY", "10", "100", "10", "2026-01-01")
        self.tx("BUY", "10", "120", "10", "2026-01-02")
        self.tx("SELL", "5", "130", "5", "2026-01-03")
        position = service.portfolio_positions(self.owner, self.portfolio["id"])[0]
        self.assertEqual(position["quantity"], "15")
        self.assertEqual(position["cost_basis"], "1665")
        self.assertEqual(position["average_cost"], "111")
        self.assertEqual(position["realized_pnl"], "90")
        self.assertIsNone(position["market_value"])
        self.assertEqual(position["valuation_status"], "price_not_supplied")

    def test_user_supplied_cfcl_acceptance_fixture(self):
        self.tx("BUY", "2500", "593", "0", "2026-01-01")
        position = service.portfolio_positions(self.owner, self.portfolio["id"])[0]
        self.assertEqual(position["cost_basis"], "1482500")
        self.assertEqual(position["average_cost"], "593")
        reference_price = 561
        self.assertEqual(2500 * reference_price - 1482500, -80000)
        self.assertAlmostEqual((-80000 / 1482500) * 100, -5.39629, places=4)

    def test_oversell_is_rejected(self):
        self.tx("BUY", "5", "100", "0", "2026-01-01")
        with self.assertRaisesRegex(ValueError, "exceeds available"):
            self.tx("SELL", "6", "110", "0", "2026-01-02")

    def test_backdated_sell_cannot_precede_acquisition(self):
        self.tx("BUY", "5", "100", "0", "2026-01-02")
        with self.assertRaisesRegex(ValueError, "historical sells exceed buys"):
            self.tx("SELL", "2", "110", "0", "2026-01-01")
        position = service.portfolio_positions(self.owner, self.portfolio["id"])[0]
        self.assertEqual(position["quantity"], "5")

    def test_idempotent_replay_and_conflict(self):
        first = self.tx("BUY", "2", "100", "0", "2026-01-01", "capture-1")
        replay = self.tx("BUY", "2", "100", "0", "2026-01-01", "capture-1")
        self.assertEqual(first["id"], replay["id"])
        with self.assertRaisesRegex(ValueError, "different transaction"):
            self.tx("BUY", "3", "100", "0", "2026-01-01", "capture-1")

    def test_database_and_parent_directory_permissions_are_private(self):
        db_path = Path(self.tmp.name) / "portfolio.sqlite3"
        self.assertEqual(db_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(db_path.parent.stat().st_mode & 0o777, 0o700)

    def test_owner_isolation_and_delete_cascade(self):
        self.tx("BUY", "2", "100", "0", "2026-01-01")
        self.assertEqual(service.list_portfolios("user-b"), [])
        self.assertIsNone(service.portfolio_positions("user-b", self.portfolio["id"]))
        self.assertTrue(service.delete_portfolio(self.owner, self.portfolio["id"]))
        self.assertEqual(service.list_portfolios(self.owner), [])

    def test_invalid_values_and_symbols_rejected(self):
        with self.assertRaises(ValueError):
            self.tx("BUY", "0", "100", "0", "2026-01-01")
        with self.assertRaises(ValueError):
            service.add_transaction(self.owner, self.portfolio["id"], symbol="bad symbol",
                                    side="BUY", quantity=1, price=1, trade_date="2026-01-01")


if __name__ == "__main__":
    unittest.main()
