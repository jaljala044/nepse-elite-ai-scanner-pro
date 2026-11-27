import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.corporate_receipt_journal import CorporateReceiptJournal

class ReceiptJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"receipts.sqlite"
        self.journal=CorporateReceiptJournal(self.path)
        now="2024-05-07T17:00:00+05:45"
        e=dict(status="verified",source_id="synthetic",available_at=now,action_id="D",symbol="AAA")
        self.args=dict(portfolio_id="P",assessment_time=now,
            entitlement=dict(e,action_type="dividend",record_date="2024-05-01",due_date="2024-05-06",gross_amount=10000),
            confirmation=dict(e,event_type="cash_received",effective_date="2024-05-06",net_amount=9500))
    def test_persistence(self):
        self.assertEqual(self.journal.record(**self.args)["new_cash_delta"],"9500")
        restarted=CorporateReceiptJournal(self.path)
        self.assertEqual(restarted.record(**self.args)["new_cash_delta"],"0")
        self.assertEqual(len(restarted.history("P")),1)
    def test_conflict(self):
        self.journal.record(**self.args)
        self.args["confirmation"]["net_amount"]=9000
        with self.assertRaisesRegex(ValueError,"conflicting_receipt_replay"): self.journal.record(**self.args)
    def test_portfolio_scope(self):
        self.journal.record(**self.args)
        self.args["portfolio_id"]="Q"
        self.assertEqual(self.journal.record(**self.args)["status"],"RECORDED")
        self.assertEqual(len(self.journal.history("P")),1)
    def test_concurrent_replay(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.journal.record(**self.args),range(8)))
        self.assertEqual(sum(r["status"]=="RECORDED" for r in results),1)
        self.assertEqual(len(self.journal.history("P")),1)
