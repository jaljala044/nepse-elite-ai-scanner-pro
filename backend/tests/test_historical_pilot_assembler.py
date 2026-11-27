import unittest

from app.historical_pilot_assembler import assemble_lifecycle_pilot_panel
from app.historical_pilot_ingest import calculate_pilot_row_sha256


class LifecyclePilotAssemblerTests(unittest.TestCase):
    def row(self, publisher="PUB-1", close=11, source=None):
        row = {
            "symbol": "AAA", "session_date": "2025-01-02",
            "open": 10.0, "high": 12.0, "low": 9.0, "close": float(close),
            "volume": 100, "available_at": "2025-01-02T16:00:00+05:45",
            "source_id": source or "SRC-" + publisher,
            "publisher_id": publisher, "capture_id": "CAP-" + publisher + (source or ""),
            "payload_id": "PAGE-" + publisher + (source or ""),
            "page_number": 1, "source_row_number": 2,
            "raw_sha256": "a" * 64, "capture_manifest_sha256": "c" * 64,
        }
        row["row_sha256"] = calculate_pilot_row_sha256(row)
        return row

    def report(self, rows):
        first = rows[0]
        return {
            "status": "INGESTED", "all_rows_accepted": True, "rows": rows,
            "source_id": first["source_id"], "publisher_id": first["publisher_id"],
            "capture_id": first["capture_id"],
            "capture_manifest_sha256": first["capture_manifest_sha256"],
        }

    def base(self, reports=None, sessions=None):
        return dict(
            cohort_symbols=["AAA"],
            security_master=[{"symbol": "AAA", "security_id": "SEC-1", "effective_from": "2025-01-01"}],
            expected_sessions=sessions if sessions is not None else [{
                "session_date": "2025-01-02", "status": "confirmed_open",
                "evidence_id": "CAL-1", "available_at": "2025-01-02T15:00:00+05:45",
            }],
            ingestion_reports=reports if reports is not None else [self.report([self.row()])],
            corporate_action_status={"status": "validated_for_research", "withheld_events": [], "rejected_events": []},
            decision_cutoff="2025-01-03T00:00:00+05:45",
        )

    def test_assembles_bounded_panel_and_retains_each_source_locator(self):
        result = assemble_lifecycle_pilot_panel(**self.base())
        self.assertEqual(result["status"], "PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH")
        self.assertEqual(result["panel_row_count"], 1)
        self.assertEqual(len(result["panel_rows"][0]["source_records"]), 1)
        self.assertFalse(result["publisher_ids_are_independence_proof"])
        self.assertFalse(result["backtest_admission_allowed"])

    def test_cross_source_conflict_quarantined(self):
        reports = [
            self.report([self.row("PUB-1", 11)]),
            self.report([self.row("PUB-2", 12)]),
        ]
        result = assemble_lifecycle_pilot_panel(**self.base(reports=reports))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["conflicts"][0]["reason"], "cross_source_ohlcv_conflict")

    def test_missing_expected_session_bar_blocks(self):
        args = self.base()
        args["ingestion_reports"] = []
        result = assemble_lifecycle_pilot_panel(**args)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["readiness_report"]["missing_symbol_sessions"]), 1)

    def test_distinct_publisher_threshold_does_not_treat_source_ids_as_independent(self):
        reports = [
            self.report([self.row("PUB-1", 11, "SRC-A")]),
            self.report([self.row("PUB-1", 11, "SRC-B")]),
        ]
        result = assemble_lifecycle_pilot_panel(
            **self.base(reports=reports), minimum_independent_sources=2,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["insufficient_source_coverage"][0]["required_distinct_publishers"], 2)

    def test_row_fingerprint_tampering_blocks(self):
        row = self.row()
        row["close"] = 11.5
        result = assemble_lifecycle_pilot_panel(**self.base(reports=[self.report([row])]))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("fingerprint" in item["reason"] for item in result["ingestion_errors"]))

    def test_ingestion_report_context_mismatch_blocks(self):
        row = self.row()
        report = self.report([row])
        report["publisher_id"] = "OTHER"
        result = assemble_lifecycle_pilot_panel(**self.base(reports=[report]))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("publisher_id" in item["reason"] for item in result["ingestion_errors"]))

    def test_nonfinite_bar_blocks_before_assembly(self):
        row = self.row()
        row["open"] = float("nan")
        result = assemble_lifecycle_pilot_panel(**self.base(reports=[self.report([row])]))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["ingestion_errors"])


if __name__ == "__main__":
    unittest.main()
