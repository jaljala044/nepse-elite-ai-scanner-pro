import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import issue5_quarantine as q
from app.historical_segment_eligibility import evaluate_archive_historical_segment, evaluate_historical_segment


class ArchiveGuardIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.day = "2025-01-01"
        self.row = dict(repository="owner/archive", commit_sha="a"*40, source_file="ABC.csv",
                        source_file_sha256="b"*64, target_csv_row=2, target_date=self.day,
                        symbol="ABC", session_date=self.day, security_id="123",
                        adjustment_basis="raw", rights_status="approved", evidence_sha256="c"*64,
                        available_at="2025-01-01T15:00:00+05:45", open="100", high="105",
                        low="95", close="102", volume="100")
        self.segment = dict(symbol="ABC", security_id="123", identity_verified=True,
                            effective_from=self.day, boundary_reviewed=True, suspension_overlap=False,
                            merger_or_successor_boundary=False, adjustment_basis="raw",
                            minimum_warmup_sessions=0)

    def guard(self, carry):
        path = Path(self.tmp.name) / "overlay.csv"
        fields = [
            "repository","commit_sha","source_file","source_file_sha256","target_csv_row",
            "target_date","symbol","confirmed_carry_forward","explicit_closure_review",
            "eligible_trading_candle","canonical_training_allowed"]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(dict(self.row, confirmed_carry_forward=str(carry),
                                 explicit_closure_review=str(not carry),
                                 eligible_trading_candle="False", canonical_training_allowed="False"))
        with patch.object(q, "EXPECTED_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()), patch.object(q, "EXPECTED_COUNT", 1):
            return q.Quarantine(path)

    def evaluate(self, row, guard=None, archive=True):
        fn = evaluate_archive_historical_segment if archive else evaluate_historical_segment
        return fn(segment=self.segment, expected_sessions=[self.day],
                  session_statuses={self.day:"traded"}, records=[row], required_sessions=1,
                  available_warmup_sessions=0, decision_cutoff="2025-01-02T00:00:00+05:45",
                  archive_guard=guard)

    def assert_blocked(self, result, reason):
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])
        self.assertFalse(result["production_promotion_allowed"])
        self.assertEqual(result["verified_traded_session_count"], 0)
        self.assertIn(reason + ":" + self.day, result["reasons"])

    def test_confirmed_exclusion_blocks(self):
        self.assert_blocked(self.evaluate(self.row, self.guard(True)),
                            "archive_quarantine:excluded_confirmed_carry_forward")

    def test_closure_hold_blocks(self):
        self.assert_blocked(self.evaluate(self.row, self.guard(False)),
                            "archive_quarantine:hold_explicit_closure_review")

    def test_no_guard_blocks_archive_and_legacy_route_with_locator(self):
        for archive in (True,False):
            self.assert_blocked(self.evaluate(self.row, archive=archive), "archive_quarantine_guard_missing")

    def test_missing_locator_and_conflict_block(self):
        guard = self.guard(True)
        missing = dict(self.row)
        del missing["source_file"]
        self.assert_blocked(self.evaluate(missing,guard), "archive_quarantine:hold_missing_provenance")
        self.assert_blocked(self.evaluate(dict(self.row,source_file_sha256="d"*64),guard),
                            "archive_quarantine:hold_provenance_conflict")

    def test_target_date_binding(self):
        self.assert_blocked(self.evaluate(dict(self.row,target_date="2025-01-02"),self.guard(True)),
                            "archive_quarantine_date_binding_missing_or_mismatch")

    def test_unlisted_row_still_requires_existing_gates(self):
        result = self.evaluate(dict(self.row,target_csv_row=3,rights_status="unknown"),self.guard(True))
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertIn("source_rights_not_approved:"+self.day,result["reasons"])
        self.assertFalse(result["production_promotion_allowed"])
