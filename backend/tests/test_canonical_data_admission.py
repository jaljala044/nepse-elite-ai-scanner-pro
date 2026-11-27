import hashlib
import tempfile
import unittest
from pathlib import Path

from app.canonical_data_admission import capture_raw_artifact, validate_and_admit_ohlcv_csv

CUTOFF = "2026-11-27T16:00:00+05:45"
CSV_HEADER = "symbol,security_id,session_date,open,high,low,close,volume,turnover,available_at\n"


class CanonicalDataAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = (CSV_HEADER +
                    "ABC,SEC-1,2026-11-26,100,110,95,108,1000,108000,2026-11-26T16:00:00+05:45\n").encode()
        self.manifest = capture_raw_artifact(
            self.raw, source_id="SRC-1", source_uri="https://example.invalid/eod.csv",
            publisher="test fixture", captured_at="2026-11-26T16:05:00+05:45",
            published_at="2026-11-26T16:00:00+05:45", rights_status="approved",
            source_validation_status="verified", finality_status="final",
            output_root=self.root)
        self.path = self.root / self.manifest["raw_path"]
        self.universe = {"ABC": "SEC-1"}
        self.calendar = {"2026-11-26": "confirmed_trading_session"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_fixture_is_research_admitted_only(self):
        result = validate_and_admit_ohlcv_csv(
            raw_path=self.path, manifest=self.manifest, expected_symbols=self.universe,
            verified_session_status=self.calendar, decision_cutoff=CUTOFF,
            adjustment_basis="raw", minimum_coverage=0.98)
        self.assertTrue(result["admission_allowed"])
        self.assertFalse(result["production_promotion_allowed"])
        self.assertEqual(result["valid_row_count"], 1)

    def test_hash_mismatch_blocks(self):
        changed = dict(self.manifest, raw_sha256="0" * 64)
        result = validate_and_admit_ohlcv_csv(
            raw_path=self.path, manifest=changed, expected_symbols=self.universe,
            verified_session_status=self.calendar, decision_cutoff=CUTOFF,
            adjustment_basis="raw")
        self.assertIn("raw_sha256_mismatch", result["reasons"])

    def test_unapproved_rights_and_unverified_source_block(self):
        changed = dict(self.manifest, rights_status="unknown", source_validation_status="candidate")
        result = validate_and_admit_ohlcv_csv(
            raw_path=self.path, manifest=changed, expected_symbols=self.universe,
            verified_session_status=self.calendar, decision_cutoff=CUTOFF,
            adjustment_basis="raw")
        self.assertIn("source_rights_not_approved", result["reasons"])
        self.assertIn("source_not_independently_validated", result["reasons"])

    def test_duplicate_and_invalid_ohlc_rows_quarantined(self):
        raw = self.raw + b"ABC,SEC-1,2026-11-26,100,90,95,108,1000,108000,2026-11-26T16:00:00+05:45\n"
        path = self.root / "bad.csv"
        path.write_bytes(raw)
        changed = dict(self.manifest, raw_sha256=hashlib.sha256(raw).hexdigest(), raw_byte_count=len(raw))
        result = validate_and_admit_ohlcv_csv(
            raw_path=path, manifest=changed, expected_symbols=self.universe,
            verified_session_status=self.calendar, decision_cutoff=CUTOFF,
            adjustment_basis="raw")
        self.assertFalse(result["admission_allowed"])
        self.assertEqual(result["quarantined_row_count"], 1)
        self.assertIn("duplicate_symbol_session", result["rows"][1]["reasons"])

    def test_future_available_rows_are_quarantined(self):
        raw = (CSV_HEADER +
               "ABC,SEC-1,2026-11-26,100,110,95,108,1000,108000,2026-11-27T17:00:00+05:45\n").encode()
        path = self.root / "future.csv"
        path.write_bytes(raw)
        changed = dict(self.manifest, raw_sha256=hashlib.sha256(raw).hexdigest(), raw_byte_count=len(raw))
        result = validate_and_admit_ohlcv_csv(
            raw_path=path, manifest=changed, expected_symbols=self.universe,
            verified_session_status=self.calendar, decision_cutoff=CUTOFF,
            adjustment_basis="raw")
        self.assertIn("row_available_after_decision_cutoff", result["rows"][0]["reasons"])

    def test_unknown_calendar_or_security_does_not_promote(self):
        result = validate_and_admit_ohlcv_csv(
            raw_path=self.path, manifest=self.manifest, expected_symbols={},
            verified_session_status={"2026-11-26": "unverified"},
            decision_cutoff=CUTOFF, adjustment_basis="raw")
        self.assertFalse(result["admission_allowed"])
        self.assertTrue(result["reasons"])

    def test_content_addressed_capture_is_idempotent(self):
        again = capture_raw_artifact(
            self.raw, source_id="SRC-1", source_uri="https://example.invalid/eod.csv",
            publisher="test fixture", captured_at="2026-11-26T16:05:00+05:45",
            published_at="2026-11-26T16:00:00+05:45", rights_status="approved",
            source_validation_status="verified", finality_status="final",
            output_root=self.root)
        self.assertEqual(again["raw_sha256"], self.manifest["raw_sha256"])
        self.assertEqual(self.path.read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
