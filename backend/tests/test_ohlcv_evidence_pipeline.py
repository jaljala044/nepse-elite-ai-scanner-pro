import unittest
from datetime import date
import csv
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import issue5_quarantine as q
from app.ohlcv_csv_adapter import OhlcvCsvMapping
from app.ohlcv_evidence_pipeline import (
    run_archive_ohlcv_evidence_pipeline,
    run_ohlcv_evidence_pipeline,
)
from app.session_evidence import SessionEvidence


MAPPING = OhlcvCsvMapping({
    "symbol": "Ticker", "session_date": "Date", "open": "Open",
    "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
})
MANIFEST = [{
    "security_id": "SEC-NABIL", "symbol": "NABIL", "status": "active",
    "valid_from": "2020-01-01", "valid_to": None,
}]
SESSION = [SessionEvidence(date(2026, 11, 24), "confirmed_trading_session",
                           "NEPSE", "exchange", "SESSION-1", "2026-11-24T10:00:00Z")]


class OhlcvEvidencePipelineTests(unittest.TestCase):
    def payload(self):
        return b"Ticker,Date,Open,High,Low,Close,Volume\nNABIL,2026-11-24,100,110,95,105,100\n"

    def run_pipeline(self, **kwargs):
        defaults = dict(instrument_lifecycle=MANIFEST, session_evidence=SESSION,
                        decision_time="2026-11-25T00:00:00Z",
                        availability_by_key={"NABIL|2026-11-24": "2026-11-24T15:00:00Z"})
        defaults.update(kwargs)
        return run_ohlcv_evidence_pipeline(self.payload(), source_id="fixture",
                                           mapping=MAPPING, **defaults)

    def test_all_evidence_present_row_is_eligible_for_review_only(self):
        result = self.run_pipeline()
        self.assertEqual(result["counts"]["eligible_for_review"], 1)
        self.assertEqual(result["rows"][0]["security_id"], "SEC-NABIL")
        self.assertFalse(result["promotion_allowed"])

    def test_known_archive_sources_cannot_use_generic_ingestion(self):
        for source in ("jaljala_history_starter", "jaljala_smc_data",
                       "jaljala044/nepse-history-starter", "jaljala044/nepse-smc-data"):
            with self.subTest(source=source):
                result = run_ohlcv_evidence_pipeline(
                    self.payload(), source_id=source, mapping=MAPPING,
                    instrument_lifecycle=MANIFEST, session_evidence=SESSION,
                    decision_time="2026-11-25T00:00:00Z",
                    availability_by_key={"NABIL|2026-11-24": "2026-11-24T15:00:00Z"})
                self.assertEqual(result["counts"]["eligible_for_review"], 0)
                self.assertEqual(result["counts"]["quarantined"], 1)
                self.assertIn("archive_guarded_ingestion_required",
                              result["rows"][0]["quarantine_reasons"])
                self.assertFalse(result["promotion_allowed"])


    def test_missing_availability_quarantines_for_point_in_time(self):
        result = self.run_pipeline(availability_by_key={})
        self.assertEqual(result["counts"]["quarantined"], 1)
        self.assertIn("source_available_at_unknown", result["rows"][0]["quarantine_reasons"])

    def test_missing_session_evidence_quarantines(self):
        result = self.run_pipeline(session_evidence=[])
        self.assertIn("exchange_session_not_primary_evidence_verified",
                      result["rows"][0]["quarantine_reasons"])

    def test_ambiguous_symbol_lifecycle_quarantines(self):
        result = self.run_pipeline(instrument_lifecycle=MANIFEST + MANIFEST)
        self.assertIn("security_identity_missing_or_ambiguous",
                      result["rows"][0]["quarantine_reasons"])

    def test_future_source_availability_quarantines(self):
        result = self.run_pipeline(availability_by_key={
            "NABIL|2026-11-24": "2026-11-26T00:00:00Z"})
        self.assertIn("row_not_available_at_decision_time",
                      result["rows"][0]["quarantine_reasons"])

    def test_missing_security_master_id_quarantines(self):
        manifest = [{"symbol": "NABIL", "status": "active",
                     "valid_from": "2020-01-01", "valid_to": None}]
        result = self.run_pipeline(instrument_lifecycle=manifest)
        self.assertIn("security_master_id_missing", result["rows"][0]["quarantine_reasons"])

    def test_parser_rejections_are_preserved_and_row_count_reconciles(self):
        payload = (b"Ticker,Date,Open,High,Low,Close,Volume\n"
                   b"NABIL,2026-11-24,100,110,95,105,0\n"
                   b"NABIL,not-a-date,100,110,95,105,0\n")
        result = run_ohlcv_evidence_pipeline(
            payload, source_id="fixture", mapping=MAPPING,
            instrument_lifecycle=MANIFEST, session_evidence=SESSION,
            decision_time="2026-11-25T00:00:00Z",
            availability_by_key={"NABIL|2026-11-24": "2026-11-24T15:00:00Z"})
        self.assertEqual(len(result["rejected_rows"]), 1)
        self.assertTrue(result["row_conservation_passed"])
        self.assertEqual(result["input_rows"], result["parsed_rows"] + len(result["rejected_rows"]))


class Issue5ArchiveEvidencePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.payload = (b"Ticker,Date,Open,High,Low,Close,Volume\n"
                        b"NABIL,2026-11-24,100,110,95,105,100\n")
        self.file_sha = hashlib.sha256(self.payload).hexdigest()
        self.source = {
            "repository": "jaljala044/nepse-history-starter",
            "commit_sha": "a" * 40,
            "source_file": "03_stock_charts_ohlcv/NABIL OHLCV.csv",
            "source_file_sha256": self.file_sha,
        }
        self.availability = {"NABIL|2026-11-24": "2026-11-24T15:00:00Z"}

    def guard(self, *, line=2, carry=True):
        path = Path(self.tmp.name) / "overlay.csv"
        fields = [
            "repository", "commit_sha", "source_file", "source_file_sha256",
            "target_csv_row", "target_date", "symbol", "confirmed_carry_forward",
            "explicit_closure_review", "eligible_trading_candle", "canonical_training_allowed",
        ]
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                **self.source, "target_csv_row": line, "target_date": "2026-11-24",
                "symbol": "NABIL", "confirmed_carry_forward": str(carry),
                "explicit_closure_review": str(not carry),
                "eligible_trading_candle": "False", "canonical_training_allowed": "False",
            })
        with patch.object(q, "EXPECTED_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()), \
             patch.object(q, "EXPECTED_COUNT", 1):
            return q.Quarantine(path)

    def run_archive(self, *, guard=None, source=None, **overrides):
        source = dict(self.source if source is None else source)
        args = dict(
            payload=self.payload, source_id="jaljala_history_starter", mapping=MAPPING,
            instrument_lifecycle=MANIFEST, session_evidence=SESSION,
            decision_time="2026-11-25T00:00:00Z", availability_by_key=self.availability,
            archive_guard=guard, **source,
        )
        args.update(overrides)
        return run_archive_ohlcv_evidence_pipeline(**args)

    def test_archive_carry_forward_overlay_entry_is_quarantined(self):
        result = self.run_archive(guard=self.guard(carry=True))
        row = result["rows"][0]
        self.assertEqual(row["row_status"], "quarantined")
        self.assertIn("archive_quarantine:excluded_confirmed_carry_forward",
                      row["quarantine_reasons"])
        self.assertEqual(result["archive_quarantine"]["overlay_record_count"], 1)
        self.assertFalse(result["promotion_allowed"])

    def test_explicit_closure_review_entry_is_held(self):
        result = self.run_archive(guard=self.guard(carry=False))
        self.assertIn("archive_quarantine:hold_explicit_closure_review",
                      result["rows"][0]["quarantine_reasons"])

    def test_missing_guard_fails_closed(self):
        result = self.run_archive()
        self.assertIn("archive_quarantine_guard_missing",
                      result["rows"][0]["quarantine_reasons"])
        self.assertFalse(result["archive_quarantine"]["guard_applied"])

    def test_raw_file_hash_mismatch_fails_closed(self):
        result = self.run_archive(
            guard=self.guard(),
            source={**self.source, "source_file_sha256": "b" * 64},
        )
        self.assertIn("archive_source_file_hash_mismatch",
                      result["rows"][0]["quarantine_reasons"])

    def test_bad_archive_locator_fails_closed(self):
        result = self.run_archive(
            guard=self.guard(),
            source={**self.source, "commit_sha": "main"},
        )
        self.assertIn("archive_source_provenance_invalid",
                      result["rows"][0]["quarantine_reasons"])

    def test_overlay_absence_does_not_skip_existing_gates(self):
        result = self.run_archive(
            guard=self.guard(line=999), availability_by_key={},
        )
        row = result["rows"][0]
        self.assertEqual(row["archive_quarantine_disposition"],
                         "not_in_overlay_requires_other_gates")
        self.assertIn("source_available_at_unknown", row["quarantine_reasons"])
        self.assertEqual(row["row_status"], "quarantined")
        self.assertFalse(result["promotion_allowed"])

    def test_archive_locator_is_bound_to_exact_csv_row(self):
        result = self.run_archive(guard=self.guard(line=999))
        row = result["rows"][0]
        self.assertEqual(row["repository"], self.source["repository"])
        self.assertEqual(row["commit_sha"], self.source["commit_sha"])
        self.assertEqual(row["source_file"], self.source["source_file"])
        self.assertEqual(row["source_file_sha256"], self.file_sha)
        self.assertEqual(row["target_csv_row"], 2)
        self.assertEqual(row["target_date"], "2026-11-24")
        self.assertEqual(row["row_status"], "eligible_for_review")
        self.assertFalse(result["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
