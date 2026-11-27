import unittest, tempfile, sqlite3
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
    def test_restart(self):
        self.post()
        self.store=AtomicPortfolioReceipts(self.path)
        self.assertFalse(self.post()["applied"])
