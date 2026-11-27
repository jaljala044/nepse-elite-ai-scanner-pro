import unittest,tempfile,sqlite3,json
from app.atomic_portfolio_receipts import AtomicPortfolioReceipts

class IndividualLotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=tmp.name+"/ledger.db"
        self.store=AtomicPortfolioReceipts(self.path)
        self.store.initialize("P",1000,{"ABC":10},{"ABC":500},lots=[dict(lot_id="L",symbol="ABC",quantity=10,total_cost="500")])
        self.now="2025-01-09T18:00:00+05:45"
        self.ev=dict(status="verified",source_id="synthetic",available_at=self.now,action_id="A",symbol="ABC")
    def receipt(self,kind):
        e=dict(self.ev,action_type=kind,record_date="2025-01-05",due_date="2025-01-09",quantity=2)
        c=dict(self.ev,event_type="shares_credited",effective_date="2025-01-09",quantity=2)
        return e,c
    def post(self,e,c):
        return self.store.post(portfolio_id="P",entitlement=e,confirmation=c,assessment_time=self.now)
    def lots(self):
        with sqlite3.connect(self.path) as db:
            return json.loads(db.execute("SELECT lots FROM research_lots").fetchone()[0])
    def test_bonus(self):
        e,c=self.receipt("bonus"); e["lot_allocations"]={"L":2}
        self.post(e,c)
        self.assertEqual(self.lots()[0]["quantity"],12)
        self.assertEqual(self.lots()[0]["total_cost"],"500")
        self.assertFalse(self.post(e,c)["applied"])
    def test_rights(self):
        e,c=self.receipt("rights")
        e["payment_evidence"]=dict(self.ev,payment_date="2025-01-08",amount=200)
        with self.assertRaisesRegex(ValueError,"matching_rights_payment"): self.post(e,c)
        self.assertTrue(self.store.pay_rights(portfolio_id="P",entitlement=e,assessment_time=self.now))
        self.assertFalse(self.store.pay_rights(portfolio_id="P",entitlement=e,assessment_time=self.now))
        self.post(e,c)
        self.assertEqual(self.lots()[1]["total_cost"],"200")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT cash FROM research_portfolios").fetchone()[0],"800")
    def test_rollback(self):
        e,c=self.receipt("bonus"); e["lot_allocations"]={"L":2}
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_update BEFORE UPDATE ON research_portfolios BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.post(e,c)
        self.assertEqual(self.lots()[0]["quantity"],10)
