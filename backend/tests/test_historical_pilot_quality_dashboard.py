import unittest
from app.historical_pilot_quality_dashboard import build_historical_pilot_quality_dashboard


class QualityDashboardTests(unittest.TestCase):
    def args(self):
        return dict(
            cohort_symbols=["AAA"],
            security_master=[{"symbol":"AAA","security_id":"S1","effective_from":"2025-01-01"}],
            expected_sessions=[{"session_date":"2025-01-02","status":"confirmed_open","evidence_id":"CAL1"}],
            panel_report={"status":"PANEL_ASSEMBLED_FOR_BOUNDED_RESEARCH","panel_rows":[{"symbol":"AAA","session_date":"2025-01-02"}],"conflicts":[],"ingestion_errors":[],"insufficient_source_coverage":[]},
            reconciliation_report={"status":"SOURCE_EVIDENCE_RECONCILED","missing_capture_keys":[],"failed_capture_keys":[],"duplicate_capture_ids":[],"first_trade_report":{"all_cohort_first_trades_verified":True,"verified_count":1,"cohort_count":1,"unresolved_count":0}},
            replay_preflight={"status":"BOUNDED_PILOT_REPLAY_PREFLIGHT_READY","dataset_manifest":{"sha256":"a"*64}},
            corporate_action_status={"status":"validated_for_research","withheld_events":[],"rejected_events":[]},
        )

    def build(self, **changes):
        args = self.args()
        args.update(changes)
        return build_historical_pilot_quality_dashboard(**args)

    def test_clean_dashboard_is_review_only(self):
        out = self.build()
        self.assertEqual(out["status"], "QUALITY_REVIEW_READY")
        self.assertEqual(out["coverage_pct"], 100.0)
        self.assertFalse(out["backtest_admission_allowed"])

    def test_missing_bar_blocks_and_is_visible(self):
        args = self.args()
        args["panel_report"]["panel_rows"] = []
        out = self.build(**args)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["missing_symbol_sessions"], [{"symbol":"AAA","session_date":"2025-01-02"}])

    def test_corporate_action_exception_blocks(self):
        args = self.args()
        args["corporate_action_status"]["withheld_events"] = [{"event":"unresolved"}]
        self.assertEqual(self.build(**args)["status"], "BLOCKED")

    def test_missing_identity_cannot_shrink_denominator(self):
        args = self.args()
        args["security_master"] = []
        out = self.build(**args)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["identity_covered_symbols"], 0)
        self.assertIn("identity_coverage_incomplete_or_conflicted", out["blocking_reasons"])

    def test_duplicate_identity_rows_block(self):
        args = self.args()
        args["security_master"] = args["security_master"] * 2
        self.assertEqual(self.build(**args)["status"], "BLOCKED")

    def test_invalid_identity_dates_block(self):
        args = self.args()
        args["security_master"][0]["effective_from"] = "2025-1-1"
        self.assertEqual(self.build(**args)["status"], "BLOCKED")

    def test_empty_or_malformed_session_evidence_blocks(self):
        args = self.args()
        args["expected_sessions"] = [{"session_date":"bad-date","status":"confirmed_open","evidence_id":"CAL1"}]
        out = self.build(**args)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIn("expected_session_evidence_incomplete_or_invalid", out["blocking_reasons"])

    def test_duplicate_session_rows_block(self):
        args = self.args()
        args["expected_sessions"] = args["expected_sessions"] * 2
        self.assertEqual(self.build(**args)["status"], "BLOCKED")

    def test_malformed_and_duplicate_panel_rows_are_visible_and_block(self):
        args = self.args()
        args["panel_report"]["panel_rows"] += [
            {"symbol":"AAA","session_date":"2025-01-02"},
            {"symbol":"AAA","session_date":"not-a-date"},
            None,
        ]
        out = self.build(**args)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(len(out["duplicate_panel_rows"]), 1)
        self.assertCountEqual([item["reason"] for item in out["panel_row_errors"]],
                              ["panel_session_date_invalid", "panel_row_not_mapping",
                               "duplicate_panel_symbol_session"])
        self.assertIn("panel_rows_malformed_or_duplicated", out["blocking_reasons"])

    def test_empty_expected_denominator_blocks(self):
        args = self.args()
        args["expected_sessions"] = [{"session_date":"2025-01-02","status":"confirmed_closed","evidence_id":"CAL1"}]
        out = self.build(**args)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIsNone(out["coverage_pct"])
        self.assertIn("expected_symbol_session_denominator_empty", out["blocking_reasons"])

    def test_invalid_manifest_hash_blocks(self):
        args = self.args()
        args["replay_preflight"]["dataset_manifest"]["sha256"] = "not-a-hash"
        self.assertEqual(self.build(**args)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
