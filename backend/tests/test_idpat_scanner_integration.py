import unittest
from datetime import date, timedelta
import os
import tempfile
from pathlib import Path

from app.idpat_scanner_integration import build_idpat_scanner_bundle, persist_idpat_bundle, REQUIRED_GATES


def snapshot():
    start = date(2026, 9, 1)
    bars = []
    for i in range(40):
        base = 100 + (i % 5) * 0.2
        bars.append({
            "date": (start + timedelta(days=i)).isoformat(),
            "open": str(base - 0.1), "high": str(base + 0.5),
            "low": str(base - 0.5), "close": str(base + 0.1),
            "volume": "1000",
        })
    return {
        "symbol": "TEST",
        "price_volume": {
            "status": "verified", "source_id": "TEST_OHLCV",
            "coverage": "1", "available_at": "2026-11-26T15:00:00+05:45",
            "bars": bars,
        },
    }


def gates():
    return {name: {"status": "verified", "evidence_id": "EV-" + name,
                   "source_id": "SRC-" + name,
                   "available_at": "2026-11-26T15:30:00+05:45"}
            for name in REQUIRED_GATES}


def risk_inputs():
    return {"symbol": "TEST", "entry": "100", "stop": "95",
            "targets": {"T1": "110", "T2": "115"},
            "capital": "100000", "risk_pct": "1"}


class IDPATScannerIntegrationTests(unittest.TestCase):
    def build(self, gate_evidence=None, risk=None):
        return build_idpat_scanner_bundle(
            snapshot=snapshot(), as_of_date="2026-10-10",
            as_of_timestamp="2026-11-26T16:00:00+05:45",
            gate_evidence=gates() if gate_evidence is None else gate_evidence,
            risk_inputs=risk,
        )

    def test_missing_gates_fail_closed(self):
        result = self.build(gate_evidence={})
        self.assertEqual(result["status"], "gates_blocked")
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertEqual(len(result["record"]["blocked_gates"]), len(REQUIRED_GATES))
        self.assertEqual(result["record"]["risk_plan"]["status"], "withheld")

    def test_all_gates_enable_only_review_level_risk_plan(self):
        result = self.build(risk=risk_inputs())
        self.assertEqual(result["status"], "research_bundle_ready")
        self.assertEqual(result["record"]["risk_plan"]["status"], "risk_plan_candidate")
        self.assertEqual(result["record"]["risk_plan"]["action"], "REVIEW_ONLY")
        self.assertEqual(result["action"], "NO_TRADE")

    def test_late_gate_evidence_blocks_bundle(self):
        evidence = gates()
        evidence["sector"]["available_at"] = "2026-11-26T16:01:00+05:45"
        result = self.build(gate_evidence=evidence, risk=risk_inputs())
        self.assertEqual(result["status"], "gates_blocked")
        self.assertIn("sector:gate_evidence_after_decision_cutoff",
                      result["record"]["blocked_gates"])

    def test_snapshot_is_deterministic_and_not_persisted(self):
        first, second = self.build(), self.build()
        self.assertEqual(first["signal_id"], second["signal_id"])
        self.assertTrue(first["immutable_snapshot"])
        self.assertFalse(first["persisted"])
        self.assertEqual(first["record"]["classification"], "research_only_not_execution")

    def test_missing_risk_inputs_do_not_create_plan(self):
        result = self.build()
        self.assertEqual(result["record"]["risk_plan"]["reason"], "explicit_risk_inputs_required")

    def test_gate_without_source_identity_is_blocked(self):
        evidence = gates()
        evidence["broker"].pop("source_id")
        result = self.build(gate_evidence=evidence, risk=risk_inputs())
        self.assertIn("broker:gate_source_id_missing", result["record"]["blocked_gates"])

    def test_existing_append_only_signal_store_persists_no_trade_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ["NEPSE_API_DATABASE"] = str(Path(temp) / "idpat.duckdb")
            try:
                evidence = gates()
                bundle = self.build(risk=risk_inputs())
                first = persist_idpat_bundle(bundle, gate_evidence=evidence, horizon="swing")
                second = persist_idpat_bundle(bundle, gate_evidence=evidence, horizon="swing")
                self.assertEqual(first["status"], "stored")
                self.assertEqual(second["status"], "already_stored")
                self.assertEqual(first["action"], "NO TRADE")
                self.assertTrue(first["persisted"])
            finally:
                os.environ.pop("NEPSE_API_DATABASE", None)

    def test_all_horizons_remain_research_only(self):
        result = self.build()
        self.assertIsNone(result["record"]["overall_score"])
        self.assertIsNone(result["record"]["probability"])
        self.assertFalse(result["record"]["production_recommendations_enabled"])


if __name__ == "__main__":
    unittest.main()
