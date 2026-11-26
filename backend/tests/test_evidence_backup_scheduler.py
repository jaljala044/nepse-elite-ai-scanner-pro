import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.evidence_backup_scheduler import audit_backup_schedule, run_scheduled_backup


class EvidenceBackupSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.receipts = self.root / "receipts.jsonl"
        self.lock = self.root / "backup.lock"
        self.marker = self.root / "hooks.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, code):
        return [sys.executable, "-c", code]

    def config(self, *, backup_code=None, quiesce_code=None):
        backup_code = backup_code or "import json; print(json.dumps({'status':'backup_verified','verification':{'status':'verified'}}))"
        quiesce_code = quiesce_code or f"from pathlib import Path; Path({str(self.marker)!r}).open('a').write('Q')"
        resume_code = f"from pathlib import Path; Path({str(self.marker)!r}).open('a').write('R')"
        return {
            "quiesce_argv": self.command(quiesce_code),
            "backup_argv": self.command(backup_code),
            "resume_argv": self.command(resume_code),
            "command_timeout_seconds": 10,
        }

    def test_successful_run_records_verified_receipt_and_resume(self):
        result = run_scheduled_backup(
            config=self.config(), receipt_path=self.receipts,
            lock_path=self.lock, run_id="run-001",
        )
        self.assertEqual(result["status"], "backup_verified")
        self.assertEqual(self.marker.read_text(), "QR")
        audit = audit_backup_schedule(self.receipts, expected_interval_hours=1000)
        self.assertEqual(audit["ledger_status"], "verified")
        self.assertEqual(audit["latest_run_status"], "backup_verified")
        self.assertEqual(audit["status"], "healthy")
        self.assertFalse(audit["production_eligible"])

    def test_failed_backup_still_resumes_and_is_recorded(self):
        result = run_scheduled_backup(
            config=self.config(backup_code="import sys; print('{}'); sys.exit(4)"),
            receipt_path=self.receipts, lock_path=self.lock, run_id="run-failed",
        )
        self.assertEqual(result["status"], "backup_failed")
        self.assertEqual(self.marker.read_text(), "QR")
        audit = audit_backup_schedule(self.receipts, expected_interval_hours=1000)
        self.assertEqual(audit["ledger_status"], "verified")
        self.assertEqual(audit["status"], "attention_required")
        self.assertIn("latest_backup_run_failed", audit["issues"])

    def test_failed_run_does_not_break_receipt_chain_for_next_run(self):
        run_scheduled_backup(
            config=self.config(backup_code="import sys; sys.exit(2)"),
            receipt_path=self.receipts, lock_path=self.lock, run_id="run-1",
        )
        result = run_scheduled_backup(
            config=self.config(), receipt_path=self.receipts,
            lock_path=self.lock, run_id="run-2",
        )
        self.assertEqual(result["status"], "backup_verified")
        audit = audit_backup_schedule(self.receipts, expected_interval_hours=1000)
        self.assertEqual(audit["events_checked"], 2)
        self.assertEqual(audit["status"], "healthy")

    def test_overdue_backup_is_detected(self):
        now = datetime.now(timezone.utc)
        run_scheduled_backup(
            config=self.config(), receipt_path=self.receipts,
            lock_path=self.lock, run_id="run-old", now_utc=now - timedelta(days=3),
        )
        audit = audit_backup_schedule(
            self.receipts, now_utc=now,
            expected_interval_hours=24, grace_hours=2,
        )
        self.assertIn("scheduled_backup_overdue", audit["issues"])

    def test_receipt_tampering_is_detected(self):
        run_scheduled_backup(
            config=self.config(), receipt_path=self.receipts,
            lock_path=self.lock, run_id="run-001",
        )
        row = json.loads(self.receipts.read_text())
        row["status"] = "tampered_status"
        self.receipts.write_text(json.dumps(row) + "\n")
        audit = audit_backup_schedule(self.receipts)
        self.assertEqual(audit["ledger_status"], "invalid")
        self.assertTrue(any("invalid" in issue for issue in audit["issues"]))

    def test_relative_executable_rejected(self):
        config = self.config()
        config["backup_argv"] = ["python", "-c", "pass"]
        with self.assertRaisesRegex(ValueError, "absolute path"):
            run_scheduled_backup(
                config=config, receipt_path=self.receipts,
                lock_path=self.lock, run_id="bad-config",
            )

    def test_quiesce_failure_still_attempts_resume(self):
        result = run_scheduled_backup(
            config=self.config(quiesce_code="import sys; sys.exit(3)"),
            receipt_path=self.receipts, lock_path=self.lock, run_id="quiesce-failed",
        )
        self.assertEqual(result["status"], "backup_failed")
        self.assertEqual(self.marker.read_text(), "R")
        audit = audit_backup_schedule(self.receipts, expected_interval_hours=1000)
        self.assertEqual(audit["ledger_status"], "verified")


if __name__ == "__main__":
    unittest.main()
