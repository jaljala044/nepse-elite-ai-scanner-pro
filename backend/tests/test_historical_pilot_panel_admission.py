from __future__ import annotations

import unittest

from app.historical_pilot_panel_admission import audit_historical_pilot_panel_admission


class HistoricalPilotPanelAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.symbols = {"GMLI"}
        self.floor = {
            "status": "validated_with_unresolved_first_trade_evidence",
            "errors": [],
            "rows": [{
                "symbol": "GMLI", "security_id": "9246",
                "reported_first_trade_date": "2025-02-09",
                "official_floorsheet_status": "verified_contract_match",
            }],
        }
        self.identity = {"GMLI": {
            "status": "verified", "security_id": "9246", "source_id": "NEPSE_ID",
            "evidence_id": "ID-9246", "valid_from": "2025-02-09", "valid_to": "",
        }}
        self.calendar = {"GMLI": {
            "status": "verified_complete", "source_id": "NEPSE_CALENDAR",
            "raw_sha256": "b" * 64, "expected_sessions": 220,
            "observed_sessions": 220, "missing_sessions": 0,
            "verified_open_dates": ["2025-02-09"],
        }}
        self.ohlcv = {"GMLI": {
            "status": "verified_clean", "source_id": "NEPSE_OHLCV",
            "session_count": 220, "anomaly_count": 0, "raw_sha256": "a" * 64,
        }}
        self.actions = {"GMLI": {
            "status": "reconciled", "source_ids": ["NEPSE_CA", "CDSC_CA"],
            "evidence_sha256s": ["c" * 64, "d" * 64], "unresolved_event_count": 0,
        }}

    def audit(self):
        return audit_historical_pilot_panel_admission(
            expected_symbols=self.symbols, first_trade_report=self.floor,
            identity_by_symbol=self.identity, calendar_by_symbol=self.calendar,
            ohlcv_by_symbol=self.ohlcv, corporate_actions_by_symbol=self.actions,
        )

    def test_all_explicit_gates_pass_for_research_panel_only(self):
        report = self.audit()
        self.assertEqual(report["status"], "ready_for_research_panel")
        self.assertEqual(report["admitted_symbols"], ["GMLI"])
        self.assertTrue(report["symbols"][0]["horizon_eligibility"]["investment"])
        self.assertFalse(report["canonical_promotion_allowed"])
        self.assertFalse(report["production_enabled"])

    def test_missing_evidence_blocks_instead_of_neutral(self):
        report = audit_historical_pilot_panel_admission(
            expected_symbols=self.symbols, first_trade_report=self.floor,
            identity_by_symbol={}, calendar_by_symbol={}, ohlcv_by_symbol={},
            corporate_actions_by_symbol={},
        )
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["admitted_symbol_count"], 0)
        self.assertEqual(len(report["symbols"][0]["blockers"]), 4)

    def test_incomplete_calendar_and_ohlcv_anomalies_block(self):
        self.calendar["GMLI"]["missing_sessions"] = 1
        self.ohlcv["GMLI"]["anomaly_count"] = 2
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        blockers = report["symbols"][0]["blockers"]
        self.assertIn("calendar_session_coverage_incomplete", blockers)
        self.assertIn("ohlcv_anomalies_unresolved", blockers)

    def test_unreconciled_corporate_actions_block(self):
        self.actions["GMLI"] = {
            "status": "reconciled", "source_ids": ["NEPSE_CA"],
            "evidence_sha256s": ["c" * 64], "unresolved_event_count": 1,
        }
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        self.assertIn("corporate_action_independent_evidence_or_resolution_incomplete", report["symbols"][0]["blockers"])

    def test_horizon_warmup_is_separate_from_panel_admission(self):
        self.ohlcv["GMLI"]["session_count"] = 80
        report = self.audit()
        self.assertEqual(report["status"], "ready_for_research_panel")
        horizons = report["symbols"][0]["horizon_eligibility"]
        self.assertTrue(horizons["t_plus_2"])
        self.assertTrue(horizons["swing"])
        self.assertTrue(horizons["positional"])
        self.assertFalse(horizons["investment"])

    def test_security_id_mismatch_blocks_panel_admission(self):
        self.identity["GMLI"]["security_id"] = "9999"
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        self.assertIn("effective_dated_security_identity_mismatch", report["symbols"][0]["blockers"])

    def test_first_trade_date_must_be_verified_open_session(self):
        self.calendar["GMLI"]["verified_open_dates"] = []
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        self.assertIn("first_trade_date_not_verified_open_session", report["symbols"][0]["blockers"])

    def test_first_trade_report_errors_block_every_symbol(self):
        self.floor["errors"] = ["bad source record"]
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        self.assertIn("first_trade_report_contains_validation_errors", report["errors"])


if __name__ == "__main__":
    unittest.main()
