import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
from app.corporate_receipt_balances import ReceiptBalanceLedger

class ReceiptBalanceTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"balances.sqlite"
        self.ledger=ReceiptBalanceLedger(self.path)
        now="2024-05-07T17:00:00+05:45"
        e=dict(status="verified",source_id="synthetic",available_at=now,action_id="D",symbol="AAA")
        self.args=dict(portfolio_id="P",assessment_time=now,
            entitlement=dict(e,action_type="dividend",record_date="2024-05-01",due_date="2024-05-06",gross_amount=10000),
            confirmation=dict(e,event_type="cash_received",effective_date="2024-05-06",net_amount=9500))
    def test_restart_and_duplicate(self):
        self.ledger.apply(**self.args)
        other=ReceiptBalanceLedger(self.path)
        self.assertEqual(other.apply(**self.args)["status"],"ALREADY_RECORDED")
        self.assertEqual(other.balances("P"),{"cash:NPR":"9500"})
    def test_rollback(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_credit BEFORE INSERT ON receipt_balance_totals BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.ledger.apply(**self.args)
        self.assertEqual(self.ledger.balances("P"),{})
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipt_balance_events").fetchone()[0],0)
            db.execute("DROP TRIGGER fail_credit")
        self.assertEqual(self.ledger.apply(**self.args)["status"],"RECORDED")
    def test_concurrent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.ledger.apply(**self.args),range(8)))
        self.assertEqual(sum(r["status"]=="RECORDED" for r in results),1)
        self.assertEqual(self.ledger.balances("P"),{"cash:NPR":"9500"})
    def test_conflict(self):
        self.ledger.apply(**self.args)
        self.args["confirmation"]["net_amount"]=9000
        with self.assertRaisesRegex(ValueError,"conflicting_receipt_replay"): self.ledger.apply(**self.args)
        self.assertEqual(self.ledger.balances("P"),{"cash:NPR":"9500"})
