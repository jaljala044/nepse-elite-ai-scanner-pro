import unittest
from app.corporate_action_portfolio_ledger import apply_corporate_actions_to_portfolio


class CorporateActionPortfolioLedgerTests(unittest.TestCase):
    def setUp(self):
        self.holdings = {"AAA": {"quantity": 100, "average_cost": 100}}
        self.base = {
            "status": "verified", "source_id": "cdsc-entitlement-001",
            "available_at": "2025-01-01T10:00:00+05:45", "symbol": "AAA",
        }
        self.cutoff = "2025-02-01T15:00:00+05:45"

    def action(self, action_id, action_type, **values):
        return dict(self.base, action_id=action_id, action_type=action_type, **values)

    def run_ledger(self, actions, cash=10000, as_of="2025-02-01"):
        return apply_corporate_actions_to_portfolio(
            holdings=self.holdings, cash=cash, actions=actions,
            as_of_date=as_of, evidence_cutoff=self.cutoff)

    def test_bonus_and_split_credit_shares_preserving_cost_basis(self):
        actions = [
            self.action("bonus-1", "bonus", entitlement_quantity=100, ratio=0.10,
                        listing_date="2025-01-10"),
            self.action("split-1", "split", entitlement_quantity=110, ratio=1,
                        listing_date="2025-01-20"),
        ]
        result = self.run_ledger(actions)
        self.assertEqual(result["holdings"]["AAA"]["quantity"], 220)
        self.assertAlmostEqual(result["holdings"]["AAA"]["cost_basis"], 10000)
        self.assertAlmostEqual(result["holdings"]["AAA"]["average_cost"], 10000 / 220)
        self.assertEqual(result["event_count"], 2)

    def test_dividend_credited_on_payment_date(self):
        action = self.action("dividend-1", "dividend", entitlement_quantity=100,
                             cash_per_share=5, payment_date="2025-01-15")
        result = self.run_ledger([action], cash=1000)
        self.assertEqual(result["cash"], 1500)
        self.assertEqual(result["holdings"]["AAA"]["quantity"], 100)
        self.assertEqual(result["events"][0]["event_type"], "dividend_cash_credited")

    def test_rights_subscription_debit_and_listing_credit(self):
        action = self.action("rights-1", "rights", entitlement_quantity=50,
                             subscribed_quantity=40, subscription_price=80,
                             subscription_payment_date="2025-01-10",
                             listing_date="2025-01-25")
        result = self.run_ledger([action], cash=5000)
        self.assertEqual(result["cash"], 1800)
        self.assertEqual(result["holdings"]["AAA"]["quantity"], 140)
        self.assertEqual(result["holdings"]["AAA"]["cost_basis"], 13200)
        self.assertEqual(result["event_count"], 2)

    def test_future_listing_not_credited_before_as_of(self):
        action = self.action("bonus-future", "bonus", entitlement_quantity=100,
                             ratio=0.20, listing_date="2025-03-01")
        result = self.run_ledger([action], as_of="2025-02-01")
        self.assertEqual(result["holdings"]["AAA"]["quantity"], 100)
        self.assertEqual(result["event_count"], 0)

    def test_unverified_and_lookahead_rejected(self):
        action = self.action("bonus-2", "bonus", entitlement_quantity=100,
                             ratio=0.1, listing_date="2025-01-10", status="unverified")
        with self.assertRaisesRegex(ValueError, "not_verified"):
            self.run_ledger([action])
        action = self.action("bonus-3", "bonus", entitlement_quantity=100,
                             ratio=0.1, listing_date="2025-01-10",
                             available_at="2025-02-02T10:00:00+05:45")
        with self.assertRaisesRegex(ValueError, "lookahead"):
            self.run_ledger([action])

    def test_entitlement_and_rights_subscription_cannot_exceed_verified_quantity(self):
        action = self.action("bonus-4", "bonus", entitlement_quantity=101,
                             ratio=0.1, listing_date="2025-01-10")
        with self.assertRaisesRegex(ValueError, "exceeds_reconciled"):
            self.run_ledger([action])
        action = self.action("rights-2", "rights", entitlement_quantity=10,
                             subscribed_quantity=11, subscription_price=80,
                             subscription_payment_date="2025-01-10", listing_date="2025-01-20")
        with self.assertRaisesRegex(ValueError, "exceeds_entitlement"):
            self.run_ledger([action])

    def test_insufficient_rights_cash_fails_closed(self):
        action = self.action("rights-3", "rights", entitlement_quantity=50,
                             subscribed_quantity=40, subscription_price=80,
                             subscription_payment_date="2025-01-10", listing_date="2025-01-20")
        with self.assertRaisesRegex(ValueError, "insufficient_cash"):
            self.run_ledger([action], cash=100)

    def test_duplicate_action_ids_rejected(self):
        action = self.action("duplicate", "dividend", entitlement_quantity=100,
                             cash_per_share=1, payment_date="2025-01-15")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.run_ledger([action, action])


    def test_malformed_calendar_date_is_rejected(self):
        action = self.action("bad-date", "bonus", entitlement_quantity=100,
                             ratio=0.1, listing_date="2025-01-10T00:00:00")
        with self.assertRaisesRegex(ValueError, "invalid_listing_date"):
            self.run_ledger([action])

if __name__ == "__main__":
    unittest.main()
