import unittest
from unittest.mock import patch
from app.historical_feature_replay import build_historical_feature_series


def point(day="2025-01-02", time="15:00:00+05:45", sessions=None):
    return {"decision_time": f"{day}T{time}", "session_dates": sessions or [day]}


def manifests_for(*days):
    return {f"{day}T09:15:00+00:00": {"manifest_id": f"M-{day}", "status": "validated"} for day in days}


class HistoricalFeatureReplayTests(unittest.TestCase):
    def test_requires_ordered_decision_points(self):
        with self.assertRaisesRegex(ValueError, "strictly_chronological"):
            build_historical_feature_series(records=[{}], expected_symbols=["ABC"],
                evidence_manifests={}, decision_points=[
                    point("2025-01-02"), point("2025-01-01")])

    def test_requires_canonical_and_possible_sessions(self):
        for day in ("20250102", "2025-02-30", "2025-1-2"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "canonical"):
                build_historical_feature_series(records=[{}], expected_symbols=["ABC"],
                    evidence_manifests={}, decision_points=[point("2025-03-01", sessions=[day])])

    def test_future_session_after_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "future_session_after_decision_cutoff"):
            build_historical_feature_series(records=[{}], expected_symbols=["ABC"],
                evidence_manifests={}, decision_points=[
                    point("2025-01-02", sessions=["2025-01-02", "2025-01-03"])])

    def test_duplicate_expected_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected_symbols_must_be_unique"):
            build_historical_feature_series(records=[{}], expected_symbols=["AAA", "aaa"],
                evidence_manifests={}, decision_points=[point()])

    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_missing_and_empty_manifest_are_withheld_without_adapter(self, adapter, builder):
        for manifest in ({}, None):
            manifests = {"2025-01-02T09:15:00+00:00": manifest} if manifest is not None else {}
            out = build_historical_feature_series(records=[{"record_type":"ohlcv"}],
                expected_symbols=["ABC"], evidence_manifests=manifests,
                decision_points=[point()])
            self.assertEqual(out["status"], "built_with_gaps")
            self.assertEqual(len(out["withheld_decision_points"]), 1)
            row = out["snapshots"][0]["feature_series"]["ABC"]["trend_momentum"]["qualification_by_horizon"]["swing"]
            self.assertEqual(row["status"], "withheld")
            self.assertEqual(row["action"], "NO_TRADE")
            self.assertIsNone(row["score"])
        builder.assert_not_called()
        adapter.assert_not_called()

    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_each_decision_point_rebuilds_as_of_snapshot(self, adapter, builder):
        builder.return_value = {"decision_time":"2025-01-02T09:15:00+00:00","component_feature_bundles":{},"input_contracts":{}}
        adapter.return_value = {"symbols":{},"policy":"verified_manifest_required"}
        points = [point("2025-01-02"), point("2025-01-03", sessions=["2025-01-02","2025-01-03"])]
        manifests = manifests_for("2025-01-02", "2025-01-03")
        out = build_historical_feature_series(records=[{"record_type":"ohlcv"}],
            expected_symbols=["ABC"], evidence_manifests=manifests, decision_points=points)
        self.assertEqual(out["snapshot_count"], 2)
        self.assertEqual(builder.call_count, 2)
        self.assertEqual(adapter.call_count, 2)
        self.assertIsNone(builder.call_args.kwargs["sector_membership"])

    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_future_sector_membership_is_withheld_for_that_decision(self, adapter, builder):
        builder.return_value = {"decision_time":"2025-01-02T09:15:00+00:00","input_contracts":{}}
        adapter.return_value = {"symbols":{},"policy":"verified_manifest_required"}
        session = "2025-01-02"
        membership = {"AAA":{"status":"verified","as_of_status":"verified","sector_code":"Hydro",
            "effective_from":"2024-01-01","effective_to":None,"source_id":"SRC",
            "source_payload_sha256":"a"*64,"available_at":"2025-01-03T10:00:00+05:45"}}
        out = build_historical_feature_series(records=[{}], expected_symbols=["AAA"],
            evidence_manifests=manifests_for(session), decision_points=[point(session)],
            sector_membership={"AAA":{"sector_code":"Hydro"}}, expected_sector_members={"Hydro":["AAA"]},
            sector_membership_by_session={session:membership},
            expected_sector_members_by_session={session:{"Hydro":["AAA"]}})
        self.assertEqual(out["snapshots"][0]["sector_membership_status"], "withheld")
        self.assertEqual(builder.call_args.kwargs["sector_membership"], None)

    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_point_in_time_sector_membership_passes_only_with_valid_evidence(self, adapter, builder):
        builder.return_value = {"decision_time":"2025-01-02T09:15:00+00:00","input_contracts":{}}
        adapter.return_value = {"symbols":{},"policy":"verified_manifest_required"}
        session = "2025-01-02"
        membership = {"AAA":{"status":"verified","as_of_status":"verified","sector_code":"Hydro",
            "effective_from":"2024-01-01","effective_to":None,"source_id":"SRC",
            "source_payload_sha256":"a"*64,"available_at":"2025-01-02T10:00:00+05:45"}}
        build_historical_feature_series(records=[{}], expected_symbols=["AAA"],
            evidence_manifests=manifests_for(session), decision_points=[point(session)],
            sector_membership_by_session={session:membership},
            expected_sector_members_by_session={session:{"Hydro":["AAA"]}})
        self.assertEqual(builder.call_args.kwargs["sector_membership"], membership)
        self.assertEqual(builder.call_args.kwargs["expected_sector_members"], {"Hydro":["AAA"]})


if __name__ == "__main__":
    unittest.main()
