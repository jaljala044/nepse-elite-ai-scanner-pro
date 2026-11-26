import unittest
from app.corporate_action_ledger import run_corporate_action_portfolio_ledger


class CorporateActionPortfolioLedgerTests(unittest.TestCase):
    def setUp(self):
        self.days = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
        self.prices = {"AAA": [{"date": day, "close": close} for day, close in
                               zip(self.days, [100, 100, 50, 50, 50])]}
        self.cutoff = "2025-01-05T15:00:00+05:45"

    def action(self, **kwargs):
        return {"symbol": "AAA", "status": "verified", "source_id": "src-" + kwargs["action_type"],
                "available_at": "2025-01-01T09:00:00+05:45",
                "ex_date": "2025-01-02", **kwargs}

    def run_ledger(self, actions, **overrides):
        args = {"initial_cash": 1000,
                "initial_holdings": [{"symbol": "AAA", "quantity": 10, "total_cost": 800}],
                "corporate_actions": actions, "price_rows_by_symbol": self.prices,
                "as_of_date": "2025-01-05", "evidence_cutoff": self.cutoff}
        args.update(overrides)
        return run_corporate_action_portfolio_ledger(**args)

    def test_bonus_shares_only_become_available_on_listing_date(self):
        result = self.run_ledger([self.action(action_type="bonus", ratio=1,
                                               record_date="2025-01-02", listing_date="2025-01-04")])
        bonus = next(x for x in result["event_log"] if x["type"] == "bonus_shares_listed")
        self.assertEqual(bonus["credited_quantity"], 10)
        self.assertEqual(result["ending_holdings"][0]["quantity"], 20)
        self.assertEqual(result["ending_holdings"][0]["total_cost"], 800)

    def test_dividend_credited_on_payment_date_using_record_date_quantity(self):
        result = self.run_ledger([self.action(action_type="dividend", cash_per_share=5,
                                               record_date="2025-01-02", payment_date="2025-01-04")])
        credit = next(x for x in result["event_log"] if x["type"] == "dividend_cash_credited")
        self.assertEqual(credit["eligible_quantity"], 10)
        self.assertEqual(credit["cash_credit"], 50)
        self.assertEqual(result["ending_cash"], 1050)

    def test_rights_subscription_debits_cash_and_capitalizes_cost_on_listing(self):
        action = self.action(action_type="rights", ratio=0.5, subscription_price=20,
                             record_date="2025-01-02", subscription_date="2025-01-03",
                             listing_date="2025-01-05", subscribe=True)
        result = self.run_ledger([action])
        self.assertEqual(result["ending_cash"], 900)
        self.assertEqual(result["ending_holdings"][0]["quantity"], 15)
        self.assertEqual(result["ending_holdings"][0]["total_cost"], 900)

    def test_rights_cash_shortfall_fails_closed(self):
        action = self.action(action_type="rights", ratio=2, subscription_price=100,
                             record_date="2025-01-02", subscription_date="2025-01-03",
                             listing_date="2025-01-05", subscribe=True)
        with self.assertRaisesRegex(ValueError, "cash_insufficient"):
            self.run_ledger([action], initial_cash=10)

    def test_split_changes_quantity_without_changing_total_cost(self):
        action = self.action(action_type="split", ratio=1, effective_date="2025-01-03")
        result = self.run_ledger([action])
        self.assertEqual(result["ending_holdings"][0]["quantity"], 20)
        self.assertEqual(result["ending_holdings"][0]["total_cost"], 800)

    def test_future_available_action_rejected_as_lookahead(self):
        action = self.action(action_type="bonus", ratio=1, record_date="2025-01-02",
                             listing_date="2025-01-04",
                             available_at="2025-01-06T10:00:00+05:45")
        with self.assertRaisesRegex(ValueError, "lookahead"):
            self.run_ledger([action])

    def test_missing_mark_on_held_symbol_fails_closed(self):
        prices = {"AAA": [{"date": "2025-01-01", "close": 100},
                          {"date": "2025-01-03", "close": 50}]}
        with self.assertRaisesRegex(ValueError, "holding_mark_missing"):
            self.run_ledger([], price_rows_by_symbol=prices)


if __name__ == "__main__":
    unittest.main()
