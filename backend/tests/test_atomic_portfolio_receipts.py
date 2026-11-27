import unittest, tempfile, sqlite3, json
from concurrent.futures import ThreadPoolExecutor
from app.atomic_portfolio_receipts import AtomicPortfolioReceipts

class AtomicReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=self.tmp.name+"/ledger.db"
        self.store=AtomicPortfolioReceipts(self.path)
        self.store.initialize("P",1000,{"ABC":10},{"ABC":500})
        self.now="2025-01-09T18:00:00+05:45"
        ev=dict(status="verified",source_id="synthetic",available_at=self.now,action_id="A",symbol="ABC")
        self.e=dict(ev,action_type="dividend",record_date="2025-01-05",due_date="2025-01-09",gross_amount=100)
        self.c=dict(ev,event_type="cash_received",effective_date="2025-01-09",net_amount=95)
    def post(self):
        return self.store.post(portfolio_id="P",entitlement=self.e,confirmation=self.c,assessment_time=self.now)
    def test_concurrent_duplicate(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.post(),range(2)))
        self.assertEqual(sum(r["applied"] for r in results),1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT cash FROM research_portfolios").fetchone()[0],"1095")
    def test_rollback(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_update BEFORE UPDATE ON research_portfolios BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.post()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM research_postings").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT cash FROM research_portfolios").fetchone()[0],"1000")
    def test_rights_credit_rolls_back_every_write_boundary(self):
        entitlement = dict(
            status="verified", source_id="synthetic", available_at=self.now,
            action_id="R", symbol="ABC", action_type="rights",
            record_date="2025-01-05", due_date="2025-01-09", quantity=2,
            payment_evidence=dict(status="verified", source_id="synthetic",
                available_at=self.now, action_id="R", symbol="ABC",
                payment_date="2025-01-06", amount=200),
        )
        confirmation = dict(status="verified", source_id="synthetic",
            available_at=self.now, action_id="R", symbol="ABC",
            event_type="shares_credited", effective_date="2025-01-09",
            quantity=2)
        for table, operation in (
            ("research_costs", "UPDATE"),
            ("research_lots", "UPDATE"),
            ("research_postings", "INSERT"),
            ("research_portfolios", "UPDATE"),
        ):
            with self.subTest(table=table), tempfile.TemporaryDirectory() as tmp:
                path = tmp + "/rights.db"
                store = AtomicPortfolioReceipts(path)
                store.initialize("P", 1000, {"ABC":10}, {"ABC":500},
                    lots=[{"lot_id":"L1","symbol":"ABC","quantity":10,"total_cost":"500"}])
                self.assertTrue(store.pay_rights(portfolio_id="P",
                    entitlement=entitlement, assessment_time=self.now))
                with sqlite3.connect(path) as db:
                    db.execute(f"CREATE TRIGGER fail_{table} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'injected'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    store.post(portfolio_id="P", entitlement=entitlement,
                        confirmation=confirmation, assessment_time=self.now)
                with sqlite3.connect(path) as db:
                    self.assertEqual(db.execute("SELECT cash FROM research_portfolios WHERE id='P'").fetchone()[0], "800")
                    self.assertEqual(json.loads(db.execute("SELECT shares FROM research_portfolios WHERE id='P'").fetchone()[0]), {"ABC":10})
                    self.assertEqual(json.loads(db.execute("SELECT costs FROM research_costs WHERE portfolio_id='P'").fetchone()[0]), {"ABC":"500"})
                    self.assertEqual(json.loads(db.execute("SELECT lots FROM research_lots WHERE portfolio_id='P'").fetchone()[0]),
                        [{"lot_id":"L1","symbol":"ABC","quantity":10,"total_cost":"500"}])
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM research_postings").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM research_rights").fetchone()[0], 1)

    def test_rights_payment_rolls_back_receipt_and_cash_together(self):
        entitlement = dict(
            status="verified", source_id="synthetic", available_at=self.now,
            action_id="R", symbol="ABC", action_type="rights",
            record_date="2025-01-05", due_date="2025-01-09", quantity=2,
            payment_evidence=dict(status="verified", source_id="synthetic",
                available_at=self.now, action_id="R", symbol="ABC",
                payment_date="2025-01-06", amount=200),
        )
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_rights_cash BEFORE UPDATE ON research_portfolios BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.pay_rights(portfolio_id="P", entitlement=entitlement, assessment_time=self.now)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT cash FROM research_portfolios WHERE id='P'").fetchone()[0], "1000")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM research_rights").fetchone()[0], 0)

    def test_restart(self):
        self.post()
        self.store=AtomicPortfolioReceipts(self.path)
        self.assertFalse(self.post()["applied"])
