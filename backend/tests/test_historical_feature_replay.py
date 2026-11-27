import unittest
from unittest.mock import patch
from app.historical_feature_replay import build_historical_feature_series

class HistoricalFeatureReplayTests(unittest.TestCase):
    def test_requires_ordered_decision_points(self):
        with self.assertRaisesRegex(ValueError,"strictly_chronological"):
            build_historical_feature_series(records=[{}],expected_symbols=["ABC"],
                evidence_manifests={},decision_points=[
                    {"decision_time":"2025-01-02T15:00:00+05:45","session_dates":["2025-01-02"]},
                    {"decision_time":"2025-01-01T15:00:00+05:45","session_dates":["2025-01-01"]}])
    def test_requires_canonical_sessions(self):
        with self.assertRaisesRegex(ValueError,"canonical_session_dates"):
            build_historical_feature_series(records=[{}],expected_symbols=["ABC"],
                evidence_manifests={},decision_points=[
                    {"decision_time":"2025-01-02T15:00:00+05:45","session_dates":[]}])
    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_missing_manifest_is_withheld_and_no_signal_claim(self, adapter, builder):
        builder.return_value={"decision_time":"2025-01-02T15:00:00+05:45",
            "component_feature_bundles":{},"input_contracts":{}}
        adapter.return_value={"symbols":{},"policy":"verified_manifest_required"}
        out=build_historical_feature_series(records=[{"record_type":"ohlcv"}],
            expected_symbols=["ABC"],evidence_manifests={},decision_points=[
                {"decision_time":"2025-01-02T15:00:00+05:45","session_dates":["2025-01-02"]}])
        self.assertEqual(out["status"],"built_with_gaps")
        self.assertEqual(len(out["withheld_decision_points"]),1)
        self.assertFalse(out["signals_generated"])
        builder.assert_called_once()
    @patch("app.historical_feature_replay.build_feature_snapshot")
    @patch("app.historical_feature_replay.adapt_feature_snapshot_to_strategy_evidence")
    def test_each_decision_point_rebuilds_as_of_snapshot(self, adapter, builder):
        builder.return_value={"decision_time":"2025-01-02T15:00:00+05:45",
            "component_feature_bundles":{},"input_contracts":{}}
        adapter.return_value={"symbols":{},"policy":"verified_manifest_required"}
        points=[
            {"decision_time":"2025-01-02T15:00:00+05:45","session_dates":["2025-01-02"]},
            {"decision_time":"2025-01-03T15:00:00+05:45","session_dates":["2025-01-02","2025-01-03"]}]
        manifests={k:{} for k in ["2025-01-02T09:15:00+00:00","2025-01-03T09:15:00+00:00"]}
        # Use canonical UTC keys emitted by the timestamp parser.
        manifests={"2025-01-02T09:15:00+00:00":{},"2025-01-03T09:15:00+00:00":{}}
        out=build_historical_feature_series(records=[{"record_type":"ohlcv"}],
            expected_symbols=["ABC"],evidence_manifests=manifests,decision_points=points)
        self.assertEqual(out["snapshot_count"],2)
        self.assertEqual(builder.call_count,2)

if __name__=="__main__": unittest.main()
