import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from app.corporate_receipt_journal import CorporateReceiptJournal
from app.corporate_receipt_balances import ReceiptBalanceLedger

class ReceiptMigrationTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.source=Path(tmp.name)/"legacy.sqlite"
        self.target=Path(tmp.name)/"target.sqlite"
        self.journal=CorporateReceiptJournal(self.source)
        self.ledger=ReceiptBalanceLedger(self.target)
        self.now="2024-05-07T17:00:00+05:45"
    def receipt(self,aid="D",amount=9500):
        e=dict(status="verified",source_id="synthetic",available_at=self.now,action_id=aid,symbol="AAA")
        return dict(portfolio_id="P",assessment_time=self.now,
            entitlement=dict(e,action_type="dividend",record_date="2024-05-01",due_date="2024-05-06",gross_amount=10000),
            confirmation=dict(e,event_type="cash_received",effective_date="2024-05-06",net_amount=amount))
    def migrate(self):
        return self.ledger.migrate_legacy(self.source,self.now,source_frozen=True)
    def test_repeat_and_reconcile(self):
        self.journal.record(**self.receipt())
        self.assertEqual(self.migrate()["imported"],1)
        self.assertEqual(self.migrate()["skipped"],1)
        self.assertEqual(self.ledger.balances("P"),{"cash:NPR":"9500"})
        self.assertTrue(self.ledger.reconcile("P",self.now)["reconciled"])
        self.assertEqual(self.ledger.apply(**self.receipt())["status"],"ALREADY_RECORDED")
    def test_conflict(self):
        self.journal.record(**self.receipt())
        self.ledger.apply(**self.receipt(amount=9000))
        with self.assertRaisesRegex(ValueError,"conflicting_legacy_receipt"): self.migrate()
        self.assertEqual(self.ledger.balances("P"),{"cash:NPR":"9000"})
    def test_corruption_rolls_back(self):
        self.journal.record(**self.receipt("A"))
        self.journal.record(**self.receipt("B"))
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE corporate_receipts SET payload_hash='bad' WHERE action_id='B'")
        with self.assertRaisesRegex(ValueError,"invalid_legacy_receipt"): self.migrate()
        self.assertEqual(self.ledger.balances("P"),{})
        self.assertEqual(self.ledger.reconcile("P",self.now)["event_count"],0)
    def test_unfrozen(self):
        with self.assertRaisesRegex(ValueError,"legacy_writer_must_be_retired"):
            self.ledger.migrate_legacy(self.source,self.now)
    def test_projection_corruption(self):
        self.journal.record(**self.receipt())
        self.migrate()
        with sqlite3.connect(self.target) as db:
            db.execute("UPDATE receipt_balance_totals SET amount='9999'")
        result=self.ledger.reconcile("P",self.now)
        self.assertFalse(result["reconciled"])
        self.assertEqual(result["differences"]["cash:NPR"]["expected"],"9500")
