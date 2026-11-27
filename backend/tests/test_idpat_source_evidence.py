import unittest
from app.idpat_source_evidence import GATE_REQUIREMENTS, derive_idpat_gate_evidence


def reports():
    values = {}
    for gate, spec in GATE_REQUIREMENTS.items():
        row = {
            "report_status": "validated",
            "source_id": "SRC-" + gate,
            "evidence_id": "EV-" + gate,
            "available_at": "2026-11-27T12:00:00+05:45",
        }
        row.update(spec["fields"])
        row.update({key: str(minimum) for key, minimum in spec.get("ratios", {}).items()})
        values[gate] = row
    return values


class IDPATSourceEvidenceTests(unittest.TestCase):
    cutoff = "2026-11-27T13:00:00+05:45"

    def test_complete_validated_reports_derive_seven_gates(self):
        result = derive_idpat_gate_evidence(reports(), decision_time=self.cutoff)
        self.assertEqual(result["status"], "ready_for_research_review")
        self.assertEqual(len(result["gate_evidence"]), 7)
        self.assertFalse(result["production_enabled"])
        for gate in result["gate_evidence"]:
            self.assertEqual(result["gate_evidence"][gate]["status"], "verified")

    def test_missing_report_blocks_only_its_gate_and_bundle(self):
        data = reports()
        del data["broker"]
        result = derive_idpat_gate_evidence(data, decision_time=self.cutoff)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("broker:validated_report_missing", result["blocked_gates"])
        self.assertNotIn("broker", result["gate_evidence"])

    def test_late_report_is_rejected(self):
        data = reports()
        data["sector"]["available_at"] = "2026-11-27T13:01:00+05:45"
        result = derive_idpat_gate_evidence(data, decision_time=self.cutoff)
        self.assertIn("sector:report_available_after_decision_time", result["blocked_gates"])

    def test_unvalidated_report_is_rejected_even_with_all_fields(self):
        data = reports()
        data["market"]["report_status"] = "draft"
        result = derive_idpat_gate_evidence(data, decision_time=self.cutoff)
        self.assertIn("market:report_not_validated", result["blocked_gates"])

    def test_missing_source_or_evidence_id_is_rejected(self):
        for field in ("source_id", "evidence_id"):
            data = reports()
            data["broker"].pop(field)
            result = derive_idpat_gate_evidence(data, decision_time=self.cutoff)
            self.assertTrue(any(x.startswith("broker:") for x in result["blocked_gates"]))

    def test_thresholds_and_invalid_ratios_fail_closed(self):
        data = reports()
        data["sector"]["price_coverage_ratio"] = "0.9799"
        data["broker"]["verified_amount_coverage"] = "NaN"
        result = derive_idpat_gate_evidence(data, decision_time=self.cutoff)
        self.assertIn("sector:coverage_below_threshold_or_invalid:price_coverage_ratio", result["blocked_gates"])
        self.assertIn("broker:coverage_below_threshold_or_invalid:verified_amount_coverage", result["blocked_gates"])

    def test_naive_decision_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            derive_idpat_gate_evidence(reports(), decision_time="2026-11-27T13:00:00")


if __name__ == "__main__":
    unittest.main()
