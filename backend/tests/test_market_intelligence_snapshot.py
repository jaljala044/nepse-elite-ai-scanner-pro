import unittest

from app.market_intelligence_snapshot import (
    REQUIRED_MODULES,
    build_market_intelligence_snapshot,
)


def artifact(name="fixture", *, status="research_only", as_of="2026-11-26",
             available_at="2026-11-26T15:00:00+05:45", coverage=1.0):
    return {
        "status": status,
        "as_of_date": as_of,
        "available_at": available_at,
        "source_ids": [f"source-{name}"],
        "evidence_ids": [f"evidence-{name}"],
        "coverage_ratio": coverage,
        "source_validation_status": "verified",
        "finality_status": "final",
        "evidence_gate_passed": True,
        "data": {"fixture": True},
    }


class MarketIntelligenceSnapshotTests(unittest.TestCase):
    def test_complete_point_in_time_snapshot_is_research_only(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertEqual(result["status"], "research_only")
        self.assertEqual(result["admitted_module_count"], len(REQUIRED_MODULES))
        self.assertEqual(result["coverage_ratio"], 1.0)
        self.assertIsNone(result["production_score"])
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["trade_actions_enabled"])
        self.assertEqual(result["recommendation"], "NOT_EVALUATED")

    def test_missing_modules_remain_unknown_not_neutral(self):
        result = build_market_intelligence_snapshot(
            {}, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["admitted_module_count"], 0)
        self.assertEqual(set(result["missing_modules"]), set(REQUIRED_MODULES))
        self.assertTrue(all(item["data"] is None for item in result["modules"].values()))

    def test_future_available_artifact_is_withheld(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["broker_profiles"] = artifact(
            "late", available_at="2026-11-26T15:31:00+05:45"
        )
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        item = result["modules"]["broker_profiles"]
        self.assertFalse(item["admitted"])
        self.assertIn("artifact_available_after_decision_time", item["reasons"])
        self.assertEqual(item["source_ids"], [])

    def test_unverified_or_incomplete_source_is_not_admitted(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["sector_rotation"]["source_validation_status"] = "unverified"
        artifacts["relative_strength"]["coverage_ratio"] = None
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertFalse(result["modules"]["sector_rotation"]["admitted"])
        self.assertFalse(result["modules"]["relative_strength"]["admitted"])
        self.assertEqual(result["status"], "partial_evidence")

    def test_duplicate_lineage_ids_rejected(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["market_health"]["evidence_ids"] = ["same", "same"]
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertFalse(result["modules"]["market_health"]["admitted"])
        self.assertIn("evidence_ids_missing_or_invalid",
                      result["modules"]["market_health"]["reasons"])

    def test_decision_timestamp_must_be_timezone_aware(self):
        with self.assertRaisesRegex(ValueError, "decision_time_must_be_timezone_aware"):
            build_market_intelligence_snapshot(
                {}, decision_date="2026-11-26", decision_time="2026-11-26T15:30:00"
            )

    def test_future_as_of_date_is_rejected(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["wyckoff"] = artifact("future", as_of="2026-11-27")
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertFalse(result["modules"]["wyckoff"]["admitted"])
        self.assertIn("artifact_as_of_after_decision_date",
                      result["modules"]["wyckoff"]["reasons"])

    def test_invalid_coverage_and_unrecognized_status_are_rejected(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["index_intelligence"]["coverage_ratio"] = 1.5
        artifacts["market_structure"]["status"] = "BUY"
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertFalse(result["modules"]["index_intelligence"]["admitted"])
        self.assertFalse(result["modules"]["market_structure"]["admitted"])

    def test_zero_coverage_is_not_admitted(self):
        artifacts = {name: artifact(name) for name in REQUIRED_MODULES}
        artifacts["broker_profiles"]["coverage_ratio"] = 0
        result = build_market_intelligence_snapshot(
            artifacts, decision_date="2026-11-26",
            decision_time="2026-11-26T15:30:00+05:45",
        )
        self.assertFalse(result["modules"]["broker_profiles"]["admitted"])
        self.assertIn("coverage_ratio_missing_or_invalid",
                      result["modules"]["broker_profiles"]["reasons"])

    def test_required_module_list_must_be_unique(self):
        with self.assertRaisesRegex(ValueError, "required_modules_must_be_unique"):
            build_market_intelligence_snapshot(
                {}, decision_date="2026-11-26",
                decision_time="2026-11-26T15:30:00+05:45",
                required_modules=("market_health", "market_health"),
            )


if __name__ == "__main__":
    unittest.main()
