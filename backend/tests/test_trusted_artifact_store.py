import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.trusted_artifact_store import TrustedArtifactStore, build_trusted_market_snapshot
from app.market_intelligence_snapshot import REQUIRED_MODULES


class TrustedArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = b'{"metric": 12, "basis": "verified-close"}'
        (self.root / "index.json").write_bytes(self.payload)
        self.entry = {
            "source_id": "NEPSE_PRIMARY_EOD_01",
            "payload_path": "index.json",
            "payload_sha256": hashlib.sha256(self.payload).hexdigest(),
            "evidence_ids": ["eod:2026-11-27:index"],
            "as_of_date": "2026-11-27",
            "available_at": "2026-11-27T15:15:00+05:45",
            "status": "research_only",
            "coverage_ratio": 1.0,
            "source_validation_status": "verified",
            "finality_status": "final",
            "session_calendar_id": "NEPSE-CALENDAR-v1",
            "corporate_action_status": "verified",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def store(self, entry=None, module="index_intelligence"):
        return TrustedArtifactStore(self.root, {module: entry or self.entry})

    def test_admits_pinned_server_side_payload(self):
        result = self.store().load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertEqual(result["index_intelligence"]["data"]["metric"], 12)
        self.assertEqual(result["index_intelligence"]["source_ids"], ["NEPSE_PRIMARY_EOD_01"])

    def test_hash_mismatch_is_not_admitted(self):
        entry = dict(self.entry, payload_sha256="0" * 64)
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertNotIn("data", result["index_intelligence"])
        self.assertIn("payload_sha256_mismatch", result["index_intelligence"]["rejection_reason"])

    def test_future_availability_is_rejected(self):
        entry = dict(self.entry, available_at="2026-11-27T17:00:00+05:45")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("artifact_available_after_decision_time",
                      result["index_intelligence"]["rejection_reason"])

    def test_stale_artifact_is_rejected(self):
        entry = dict(self.entry, as_of_date="2026-11-01")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("artifact_stale", result["index_intelligence"]["rejection_reason"])

    def test_unverified_finality_is_rejected(self):
        entry = dict(self.entry, finality_status="provisional")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("source_finality_not_verified",
                      result["index_intelligence"]["rejection_reason"])

    def test_path_traversal_is_rejected(self):
        entry = dict(self.entry, payload_path="../outside.json")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("payload_path_unsafe", result["index_intelligence"]["rejection_reason"])

    def test_missing_modules_remain_unknown_in_snapshot(self):
        snapshot = build_trusted_market_snapshot(
            self.store(), decision_date="2026-11-27",
            decision_time="2026-11-27T16:00:00+05:45",
        )
        self.assertEqual(snapshot["status"], "partial_evidence")
        self.assertIsNone(snapshot["production_score"])
        self.assertFalse(snapshot["signals_enabled"])
        self.assertIn("market_health", snapshot["missing_modules"])


    def test_unverified_corporate_action_status_is_rejected(self):
        entry = dict(self.entry, corporate_action_status="unknown")
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("corporate_action_status_unverified",
                      result["index_intelligence"]["rejection_reason"])

    def test_sector_membership_must_be_effective_versioned_and_verified(self):
        entry = dict(self.entry, sector_membership_status="unverified",
                     sector_membership_version="sector-map-v1")
        result = self.store(entry, module="sector_rotation").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("sector_rotation",),
        )
        self.assertIn("sector_membership_version_unverified",
                      result["sector_rotation"]["rejection_reason"])

    def test_broker_code_identity_coverage_is_required(self):
        entry = dict(self.entry, broker_code_mapping_status="verified",
                     broker_identity_coverage_ratio=0.0)
        result = self.store(entry, module="broker_profiles").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("broker_profiles",),
        )
        self.assertIn("broker_identity_coverage_invalid",
                      result["broker_profiles"]["rejection_reason"])

    def test_broker_code_mapping_must_be_verified(self):
        entry = dict(self.entry, broker_code_mapping_status="unverified",
                     broker_identity_coverage_ratio=0.95)
        result = self.store(entry, module="broker_profiles").load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("broker_profiles",),
        )
        self.assertIn("broker_code_mapping_unverified",
                      result["broker_profiles"]["rejection_reason"])

    def test_duplicate_evidence_ids_rejected(self):
        entry = dict(self.entry, evidence_ids=["same", "same"])
        result = self.store(entry).load(
            decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
            required_modules=("index_intelligence",),
        )
        self.assertIn("evidence_ids_missing_or_duplicate",
                      result["index_intelligence"]["rejection_reason"])


    def test_daily_participation_requires_complete_verified_cohort(self):
        payload = json.dumps(dict(status="research_only", coverage=1,
                                  as_of_session="2026-11-27", signals_enabled=False,
                                  missing_symbols=[], counts={"advance":1,"decline":0,"unchanged":0},
                                  pressure=1, sentiment="positive",
                                  rankings={"gainers":[{"symbol":"A","value":"5"}],
                                            "losers":[], "volume":[{"symbol":"A","value":"10"}],
                                            "turnover":[{"symbol":"A","value":"100"}]})).encode()
        (self.root / "index.json").write_bytes(payload)
        entry = dict(self.entry, payload_sha256=hashlib.sha256(payload).hexdigest(),
                     equity_universe_status="verified", expected_symbols=["A"])
        store = self.store(entry, module="daily_market_participation")
        snapshot = build_trusted_market_snapshot(store, decision_date="2026-11-27",
                                                  decision_time="2026-11-27T16:00:00+05:45")
        self.assertIn("daily_market_participation", snapshot["admitted_modules"])
        self.assertFalse(snapshot["signals_enabled"])
        bad = json.loads(payload)
        bad["pressure"] = -1
        bad_payload = json.dumps(bad).encode()
        (self.root / "index.json").write_bytes(bad_payload)
        entry["payload_sha256"] = hashlib.sha256(bad_payload).hexdigest()
        result = store.load(decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
                            required_modules=("daily_market_participation",))
        self.assertEqual(result["daily_market_participation"]["rejection_reason"], "daily_participation_pressure_invalid")
        entry["coverage_ratio"] = 0.9
        result = store.load(decision_date="2026-11-27",
                            decision_time="2026-11-27T16:00:00+05:45",
                            required_modules=("daily_market_participation",))
        self.assertEqual(result["daily_market_participation"]["status"], "unavailable")

    def test_index_rotation_requires_complete_evidence(self):
        data = dict(status="research_only", as_of="2026-11-27", coverage_ratio=1,
                    missing_indices=[], benchmark="NEPSE", signals_enabled=False,
                    trade_actions_enabled=False, indices={"NEPSE": {"rotation_trail": [dict(date=f"2026-11-{d:02d}", relative_return_pct=0, momentum_change_pp=0, quadrant="leading") for d in range(22,28)]}})
        payload = json.dumps(data).encode()
        (self.root / "index.json").write_bytes(payload)
        entry = dict(self.entry, payload_sha256=hashlib.sha256(payload).hexdigest(), expected_indices=["NEPSE"])
        store = self.store(entry, module="index_rotation")
        snap = build_trusted_market_snapshot(store, decision_date="2026-11-27",
                                             decision_time="2026-11-27T16:00:00+05:45")
        self.assertIn("index_rotation", snap["admitted_modules"])
        self.assertFalse(snap["signals_enabled"])
        invalid = dict(data, indices={"NEPSE": {"rotation_trail": []}})
        raw = json.dumps(invalid).encode()
        (self.root / "index.json").write_bytes(raw)
        entry["payload_sha256"] = hashlib.sha256(raw).hexdigest()
        result = store.load(decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45", required_modules=("index_rotation",))
        self.assertEqual(result["index_rotation"]["rejection_reason"], "rotation_trail_invalid")
        entry["coverage_ratio"] = 0.5
        result = store.load(decision_date="2026-11-27", decision_time="2026-11-27T16:00:00+05:45",
                            required_modules=("index_rotation",))
        self.assertEqual(result["index_rotation"]["rejection_reason"], "index_rotation_not_complete")


    def test_combined_ten_module_alignment_and_fail_closed(self):
        registry = {}
        for module in REQUIRED_MODULES:
            registry[module] = dict(self.entry, evidence_ids=[module],
                sector_membership_status="verified", sector_membership_version="fixture-v1",
                broker_code_mapping_status="verified", broker_identity_coverage_ratio=1.0)
        sector_window = dict(status="observed", end_session="2026-11-27", observed_members=1,
            expected_members=1, missing_members=[], coverage_pct=100, median_return_pct=5,
            median_excess_return_pct=3, nepse_return_pct=2,
            constituents=[dict(symbol="A", return_pct=5, excess_return_pct=3)])
        sector_data = dict(status="observed", as_of_session="2026-11-27", signals_enabled=False,
            sectors={"BANK": {"windows": {p: sector_window for p in ("1W","1M","3M","6M")}}})
        raw_sector = json.dumps(sector_data).encode()
        (self.root / "sector.json").write_bytes(raw_sector)
        registry["sector_rotation"].update(payload_path="sector.json",
            payload_sha256=hashlib.sha256(raw_sector).hexdigest(), expected_sector_members={"BANK":["A"]})
        participation = dict(status="research_only", coverage=1, as_of_session="2026-11-27",
            signals_enabled=False, missing_symbols=[], counts=dict(advance=1, decline=0, unchanged=0),
            pressure=1, sentiment="positive", rankings=dict(gainers=[dict(symbol="A",value="5")],
            losers=[], volume=[dict(symbol="A",value="10")], turnover=[dict(symbol="A",value="100")]))
        rotation = dict(status="research_only", as_of="2026-11-27", coverage_ratio=1,
            missing_indices=[], benchmark="NEPSE", signals_enabled=False, trade_actions_enabled=False,
            indices={"NEPSE": {"rotation_trail": [dict(date=f"2026-11-{d:02d}",
            relative_return_pct=0, momentum_change_pp=0, quadrant="leading") for d in range(22,28)]}})
        for name, data, extra in [
            ("daily_market_participation", participation, dict(equity_universe_status="verified", expected_symbols=["A"])),
            ("index_rotation", rotation, dict(expected_indices=["NEPSE"]))]:
            raw = json.dumps(data).encode()
            filename = name + ".json"
            (self.root / filename).write_bytes(raw)
            registry[name] = dict(self.entry, payload_path=filename,
                payload_sha256=hashlib.sha256(raw).hexdigest(), evidence_ids=[name], **extra)
        store = TrustedArtifactStore(self.root, registry)
        def snapshot():
            return build_trusted_market_snapshot(store, decision_date="2026-11-27",
                decision_time="2026-11-27T16:00:00+05:45")
        result = snapshot()
        self.assertEqual(result["status"], "research_only")
        self.assertEqual(result["admitted_module_count"], 10)
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["trade_actions_enabled"])
        sector_window["constituents"].append(dict(symbol="A", return_pct=5, excess_return_pct=3))
        corrupt = json.dumps(sector_data).encode()
        (self.root / "sector.json").write_bytes(corrupt)
        registry["sector_rotation"]["payload_sha256"] = hashlib.sha256(corrupt).hexdigest()
        self.assertIn("sector_rotation", snapshot()["missing_modules"])
        (self.root / "sector.json").write_bytes(raw_sector)
        registry["sector_rotation"]["payload_sha256"] = hashlib.sha256(raw_sector).hexdigest()
        registry["index_rotation"]["session_calendar_id"] = "different-calendar"
        self.assertEqual(snapshot()["status"], "partial_evidence")
        registry["index_rotation"]["session_calendar_id"] = self.entry["session_calendar_id"]
        registry["daily_market_participation"]["payload_sha256"] = "0"*64
        result = snapshot()
        self.assertEqual(result["status"], "partial_evidence")
        self.assertIn("daily_market_participation", result["missing_modules"])
        self.assertIsNone(result["production_score"])


if __name__ == "__main__":
    unittest.main()
