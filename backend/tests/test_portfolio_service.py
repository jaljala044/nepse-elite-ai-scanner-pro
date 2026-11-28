import tempfile
import unittest
from datetime import datetime, timezone
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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

    def test_fractional_share_quantities_are_rejected(self):
        for quantity in ("0.5", "1.25", "10.0001"):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(ValueError, "whole share count"):
                    self.tx("BUY", quantity, "100", "0", "2026-01-01")
        self.assertEqual(service.portfolio_transactions(self.owner, self.portfolio["id"]), [])

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

    def test_trade_date_requires_canonical_iso_format(self):
        for invalid in ("20260102", "2026/01/02", "2026-02-30"):
            with self.subTest(trade_date=invalid):
                with self.assertRaisesRegex(ValueError, "trade_date must be YYYY-MM-DD"):
                    self.tx("BUY", "1", "100", "0", invalid)

    def test_concurrent_idempotent_replays_create_one_transaction(self):
        barrier = Barrier(2)

        def submit():
            barrier.wait()
            return self.tx("BUY", "2", "100", "0", "2026-01-01", "parallel-capture")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(lambda _: submit(), range(2)))

        self.assertEqual(first["id"], second["id"])
        transactions = service.portfolio_transactions(self.owner, self.portfolio["id"])
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["id"], first["id"])

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

    def test_owner_isolation_and_soft_delete_retains_transaction_ledger(self):
        self.tx("BUY", "2", "100", "0", "2026-01-01")
        portfolio_id = self.portfolio["id"]
        self.assertEqual(service.list_portfolios("user-b"), [])
        self.assertIsNone(service.portfolio_positions("user-b", portfolio_id))
        self.assertTrue(service.delete_portfolio(self.owner, portfolio_id))
        self.assertFalse(service.delete_portfolio(self.owner, portfolio_id))
        self.assertEqual(service.list_portfolios(self.owner), [])
        self.assertIsNone(service.get_portfolio(self.owner, portfolio_id))
        self.assertIsNone(service.portfolio_positions(self.owner, portfolio_id))
        self.assertIsNone(service.portfolio_transactions(self.owner, portfolio_id))
        self.assertIsNone(service.get_portfolio("user-b", portfolio_id))

        con = service._connect()
        try:
            portfolio = con.execute(
                "SELECT deleted_at FROM portfolios WHERE id=? AND owner=?",
                (portfolio_id, self.owner),
            ).fetchone()
            self.assertIsNotNone(portfolio["deleted_at"])
            self.assertEqual(
                con.execute(
                    "SELECT COUNT(*) FROM portfolio_transactions WHERE portfolio_id=?",
                    (portfolio_id,),
                ).fetchone()[0],
                1,
            )
        finally:
            con.close()


    def test_same_day_transactions_follow_ledger_insertion_order(self):
        fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        class FixedDateTime:
            @classmethod
            def now(cls, tz=None):
                return fixed_time

        # Deliberately reverse lexical UUID order: insertion order, not random
        # identifier ordering, must decide same-day ledger chronology.
        with patch.object(service, "datetime", FixedDateTime), patch.object(
            service, "uuid4",
            side_effect=[UUID("00000000-0000-0000-0000-0000000000ff"),
                         UUID("00000000-0000-0000-0000-000000000001")],
        ):
            self.tx("BUY", "5", "100", "0", "2026-01-01")
            self.tx("SELL", "2", "110", "0", "2026-01-01")

        position = service.portfolio_positions(self.owner, self.portfolio["id"])[0]
        self.assertEqual(position["quantity"], "3")
        transactions = service.portfolio_transactions(self.owner, self.portfolio["id"])
        self.assertEqual([row["side"] for row in transactions], ["BUY", "SELL"])

    def test_idempotency_keys_are_scoped_to_authenticated_owner(self):
        other_portfolio = service.create_portfolio("user-b", "Other")
        first = self.tx("BUY", "2", "100", "0", "2026-01-01", "same-key")
        second = service.add_transaction(
            "user-b", other_portfolio["id"], symbol="CFCL", side="BUY",
            quantity="3", price="90", fees="0", trade_date="2026-01-01",
            idempotency_key="same-key",
        )
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(service.portfolio_transactions(self.owner, self.portfolio["id"])), 1)
        self.assertEqual(len(service.portfolio_transactions("user-b", other_portfolio["id"])), 1)

    def test_non_finite_and_negative_transaction_values_are_rejected(self):
        for field, value in (("quantity", "NaN"), ("quantity", "Infinity"),
                             ("price", "-Infinity"), ("fees", "NaN"), ("fees", "-1")):
            kwargs = {"quantity": "1", "price": "100", "fees": "0"}
            kwargs[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    service.add_transaction(
                        self.owner, self.portfolio["id"], symbol="CFCL", side="BUY",
                        trade_date="2026-01-01", **kwargs,
                    )

    def test_failed_backdated_write_rolls_back_transaction_row(self):
        self.tx("BUY", "5", "100", "0", "2026-01-02")
        before = len(service.portfolio_transactions(self.owner, self.portfolio["id"]))
        with self.assertRaisesRegex(ValueError, "historical sells exceed buys"):
            self.tx("SELL", "2", "110", "0", "2026-01-01")
        after = service.portfolio_transactions(self.owner, self.portfolio["id"])
        self.assertEqual(len(after), before)
        self.assertEqual([row["side"] for row in after], ["BUY"])

    def test_invalid_values_and_symbols_rejected(self):
        with self.assertRaises(ValueError):
            self.tx("BUY", "0", "100", "0", "2026-01-01")
        with self.assertRaises(ValueError):
            service.add_transaction(self.owner, self.portfolio["id"], symbol="bad symbol",
                                    side="BUY", quantity=1, price=1, trade_date="2026-01-01")


if __name__ == "__main__":
    unittest.main()
