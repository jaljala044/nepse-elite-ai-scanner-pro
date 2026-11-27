from __future__ import annotations

import unittest

from app.historical_pilot_panel_admission import audit_historical_pilot_panel_admission


class HistoricalPilotPanelAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.symbols = {"GMLI"}
        self.floor = {"rows": [{"symbol": "GMLI", "official_floorsheet_status": "verified_contract_match"}]}
        self.identity = {"GMLI": {"status": "verified", "security_id": "9246"}}
        self.calendar = {"GMLI": {"status": "verified_complete", "expected_sessions": 220, "observed_sessions": 220, "missing_sessions": 0}}
        self.ohlcv = {"GMLI": {"status": "verified_clean", "session_count": 220, "anomaly_count": 0, "raw_sha256": "a" * 64}}
        self.actions = {"GMLI": {"status": "reconciled", "independent_source_count": 2, "unresolved_event_count": 0}}

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
        self.actions["GMLI"] = {"status": "reconciled", "independent_source_count": 1, "unresolved_event_count": 1}
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


if __name__ == "__main__":
    unittest.main()
