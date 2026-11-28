import unittest
from decimal import Decimal

from app.portfolio_accounting import calculate_position


class PortfolioAccountingTests(unittest.TestCase):
    def test_weighted_average_cost_includes_purchase_fees(self):
        result = calculate_position([
            {"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 10, "unit_price": "100", "fees": "10"},
            {"id": "b2", "type": "buy", "trade_date": "2026-01-02", "quantity": 10, "unit_price": "120", "fees": "10"},
        ])
        self.assertEqual(result["share_quantity"], Decimal("20"))
        self.assertEqual(result["remaining_cost_basis"], Decimal("2220"))
        self.assertEqual(result["average_cost_per_share"], Decimal("111"))

    def test_partial_sale_realized_pnl_reduces_weighted_cost_basis(self):
        result = calculate_position([
            {"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 20, "unit_price": "100", "fees": "20"},
            {"id": "s1", "type": "sell", "trade_date": "2026-01-03", "quantity": 5, "unit_price": "120", "fees": "5"},
        ])
        self.assertEqual(result["share_quantity"], Decimal("15"))
        self.assertEqual(result["remaining_cost_basis"], Decimal("1515"))
        self.assertEqual(result["realized_pnl"], Decimal("90"))

    def test_fully_closed_position_resets_remaining_basis(self):
        result = calculate_position([
            {"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 10, "unit_price": "100"},
            {"id": "s1", "type": "sell", "trade_date": "2026-01-02", "quantity": 10, "unit_price": "110"},
        ])
        self.assertEqual(result["share_quantity"], Decimal("0"))
        self.assertEqual(result["remaining_cost_basis"], Decimal("0"))
        self.assertEqual(result["realized_pnl"], Decimal("100"))

    def test_verified_mark_calculates_unrealized_pnl(self):
        result = calculate_position(
            [{"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 10, "unit_price": "100", "fees": "10"}],
            market_mark={"price": "110", "as_of": "2026-01-02", "verified": True, "source_ref": "price:ABC:2026-01-02"},
        )
        self.assertEqual(result["market_value"], Decimal("1100"))
        self.assertEqual(result["unrealized_pnl"], Decimal("90"))
        self.assertEqual(result["market_mark_status"], "VERIFIED_MARK")

    def test_unverified_or_stale_mark_returns_unknown_not_zero(self):
        tx = [{"id": "b1", "type": "buy", "trade_date": "2026-01-02", "quantity": 10, "unit_price": "100"}]
        unverified = calculate_position(tx, market_mark={"price": "120", "as_of": "2026-01-03", "verified": False, "source_ref": "x"})
        stale = calculate_position(tx, market_mark={"price": "120", "as_of": "2026-01-01", "verified": True, "source_ref": "x"})
        self.assertIsNone(unverified["market_value"])
        self.assertEqual(unverified["market_mark_status"], "UNKNOWN_UNVERIFIED_MARK")
        self.assertIsNone(stale["unrealized_pnl"])
        self.assertEqual(stale["market_mark_status"], "UNKNOWN_STALE_MARK")

    def test_oversell_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sell exceeds available shares"):
            calculate_position([
                {"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 2, "unit_price": "100"},
                {"id": "s1", "type": "sell", "trade_date": "2026-01-02", "quantity": 3, "unit_price": "110"},
            ])

    def test_out_of_order_transactions_and_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "chronological"):
            calculate_position([
                {"id": "b1", "type": "buy", "trade_date": "2026-01-02", "quantity": 2, "unit_price": "100"},
                {"id": "s1", "type": "sell", "trade_date": "2026-01-01", "quantity": 1, "unit_price": "110"},
            ])
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            calculate_position([
                {"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 2, "unit_price": "100"},
                {"id": "b1", "type": "buy", "trade_date": "2026-01-02", "quantity": 1, "unit_price": "110"},
            ])

    def test_non_integer_quantity_and_negative_fees_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "whole share"):
            calculate_position([{"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": "1.5", "unit_price": "100"}])
        with self.assertRaisesRegex(ValueError, "non-negative"):
            calculate_position([{"id": "b1", "type": "buy", "trade_date": "2026-01-01", "quantity": 1, "unit_price": "100", "fees": "-1"}])


if __name__ == "__main__":
    unittest.main()
