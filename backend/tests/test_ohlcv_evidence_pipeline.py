import unittest
from datetime import date
from app.ohlcv_csv_adapter import OhlcvCsvMapping
from app.ohlcv_evidence_pipeline import run_ohlcv_evidence_pipeline
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
        return b"Ticker,Date,Open,High,Low,Close,Volume\nNABIL,2026-11-24,100,110,95,105,0\n"

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


if __name__ == "__main__":
    unittest.main()
