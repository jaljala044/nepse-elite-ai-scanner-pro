import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.trusted_artifact_store import TrustedArtifactStore
from app.trusted_broker_dashboard import build_trusted_broker_dashboard


def profile(window):
    sessions = {"daily": 1, "weekly": 5, "monthly": 21, "yearly": 252}[window]
    return {
        "broker_id": "B17", "security_id": "SEC-CFCL", "window": window,
        "status": "descriptive_only", "coverage_ratio": "0.98",
        "requested_sessions": sessions, "expected_sessions": sessions,
        "complete_source_sessions": sessions,
        "buy_amount": "100", "sell_amount": "20", "net_amount": "80",
        "gross_amount": "120", "buy_quantity": "10", "sell_quantity": "2",
        "net_quantity": "8", "positive_net_sessions": 3,
        "negative_net_sessions": 1, "zero_activity_sessions": 1,
        "positive_net_session_ratio": "0.6", "negative_net_session_ratio": "0.2",
        "broker_participation_ratio": "0.25",
        "daily": [{"session_date": "2026-11-26", "net_amount": "80"}],
        "directional_summary": "net_buy_dominant",
    }


def rolling_profiles():
    return {
        "as_of_date": "2026-11-26",
        "as_of_timestamp": "2026-11-26T11:00:00+05:45",
        "profiles": [profile(x) for x in ("daily", "weekly", "monthly", "yearly")],
        "excluded_observation_rows": 0,
        "verified_exchange_sessions": 252,
        "complete_source_sessions": 250,
    }


class TrustedBrokerDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = {}
        modules = {
            "market_health": {"readiness": "research_only"},
            "index_intelligence": {"status": "research_only"},
            "sector_rotation": {"status": "research_only"},
            "broker_profiles": {"rolling_profiles": rolling_profiles(), "candidates": []},
            "broker_sector_rotation": {"sector_rotation_by_window": {}},
        }
        for module, payload in modules.items():
            raw = json.dumps(payload, sort_keys=True).encode("utf-8")
            filename = module + ".json"
            (self.root / filename).write_bytes(raw)
            entry = {
                "source_id": "source-" + module,
                "payload_path": filename,
                "payload_sha256": hashlib.sha256(raw).hexdigest(),
                "evidence_ids": ["evidence-" + module],
                "as_of_date": "2026-11-26",
                "available_at": "2026-11-26T10:00:00+05:45",
                "status": "research_only",
                "coverage_ratio": 0.98,
                "finality_status": "final",
                "source_validation_status": "verified",
                "session_calendar_id": "nepse-calendar-v1",
            }
            if module in {"market_health", "index_intelligence", "sector_rotation"}:
                entry["corporate_action_status"] = "confirmed_none"
            if module in {"sector_rotation", "broker_sector_rotation"}:
                entry["sector_membership_status"] = "verified"
                entry["sector_membership_version"] = "sector-map-v1"
            if module in {"broker_profiles", "broker_sector_rotation"}:
                entry["broker_code_mapping_status"] = "verified"
                entry["broker_identity_coverage_ratio"] = 0.98
            self.registry[module] = entry
        self.store = TrustedArtifactStore(self.root, self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def test_dashboard_uses_only_hash_pinned_server_artifacts(self):
        result = build_trusted_broker_dashboard(
            self.store, decision_date="2026-11-26",
            decision_time="2026-11-26T12:00:00+05:45",
        )
        self.assertEqual(result["status"], "descriptive_only")
        self.assertEqual(result["dashboard"]["status"], "descriptive_only")
        self.assertEqual(set(result["trusted_inputs"]), {
            "market_health", "index_intelligence", "sector_rotation",
            "broker_profiles", "broker_sector_rotation",
        })
        self.assertFalse(result["production_recommendations_enabled"])
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(result["trade_actions_enabled"])

    def test_missing_trusted_module_withholds_entire_dashboard(self):
        registry = dict(self.registry)
        registry.pop("broker_sector_rotation")
        result = build_trusted_broker_dashboard(
            TrustedArtifactStore(self.root, registry),
            decision_date="2026-11-26",
            decision_time="2026-11-26T12:00:00+05:45",
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["dashboard"])
        self.assertIn("broker_sector_rotation", result["missing_modules"])
        self.assertFalse(result["signals_enabled"])

    def test_deployment_loader_uses_server_registry_environment(self):
        import os
        from unittest.mock import patch
        from app.trusted_broker_dashboard import load_deployment_broker_dashboard

        registry_path = self.root / "registry.json"
        registry_path.write_text(json.dumps(self.registry), encoding="utf-8")
        settings = {
            "NEPSE_TRUSTED_ARTIFACT_ROOT": str(self.root),
            "NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH": str(registry_path),
            "NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS": "7",
        }
        with patch.dict(os.environ, settings, clear=True):
            result = load_deployment_broker_dashboard(
                decision_date="2026-11-26",
                decision_time="2026-11-26T12:00:00+05:45",
            )
        self.assertEqual(result["status"], "descriptive_only")
        self.assertEqual(len(result["trusted_inputs"]), 5)

    def test_deployment_registry_must_resolve_inside_private_artifact_root(self):
        import os
        from unittest.mock import patch
        from app.trusted_artifact_store import TrustedArtifactError
        from app.trusted_broker_dashboard import load_deployment_broker_dashboard

        with tempfile.TemporaryDirectory() as outside:
            outside_registry = Path(outside) / "registry.json"
            outside_registry.write_text(json.dumps(self.registry), encoding="utf-8")
            settings = {
                "NEPSE_TRUSTED_ARTIFACT_ROOT": str(self.root),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH": str(outside_registry),
                "NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS": "7",
            }
            with patch.dict(os.environ, settings, clear=True):
                with self.assertRaisesRegex(
                    TrustedArtifactError,
                    "trusted_broker_registry_path_escapes_store",
                ):
                    load_deployment_broker_dashboard(
                        decision_date="2026-11-26",
                        decision_time="2026-11-26T12:00:00+05:45",
                    )

    def test_registry_symlink_cannot_escape_private_artifact_root(self):
        import os
        from unittest.mock import patch
        from app.trusted_artifact_store import TrustedArtifactError
        from app.trusted_broker_dashboard import load_deployment_broker_dashboard

        with tempfile.TemporaryDirectory() as outside:
            outside_registry = Path(outside) / "registry.json"
            outside_registry.write_text(json.dumps(self.registry), encoding="utf-8")
            link = self.root / "registry-link.json"
            try:
                link.symlink_to(outside_registry)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            settings = {
                "NEPSE_TRUSTED_ARTIFACT_ROOT": str(self.root),
                "NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH": str(link),
                "NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS": "7",
            }
            with patch.dict(os.environ, settings, clear=True):
                with self.assertRaisesRegex(
                    TrustedArtifactError,
                    "trusted_broker_registry_path_escapes_store",
                ):
                    load_deployment_broker_dashboard(
                        decision_date="2026-11-26",
                        decision_time="2026-11-26T12:00:00+05:45",
                    )

    def test_payload_hash_mismatch_withholds_dashboard(self):
        entry = dict(self.registry["broker_profiles"], payload_sha256="0" * 64)
        registry = dict(self.registry, broker_profiles=entry)
        result = build_trusted_broker_dashboard(
            TrustedArtifactStore(self.root, registry),
            decision_date="2026-11-26",
            decision_time="2026-11-26T12:00:00+05:45",
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("broker_profiles", result["missing_modules"])

    def test_as_of_dates_must_match_for_cross_module_join(self):
        from app.trusted_artifact_store import TrustedArtifactError

        entry = dict(self.registry["index_intelligence"], as_of_date="2026-11-25")
        registry = dict(self.registry, index_intelligence=entry)
        with self.assertRaisesRegex(TrustedArtifactError, "trusted_artifacts_as_of_date_mismatch"):
            build_trusted_broker_dashboard(
                TrustedArtifactStore(self.root, registry),
                decision_date="2026-11-26",
                decision_time="2026-11-26T12:00:00+05:45",
            )

    def test_session_calendar_identity_must_match(self):
        from app.trusted_artifact_store import TrustedArtifactError

        entry = dict(self.registry["sector_rotation"], session_calendar_id="other-calendar")
        registry = dict(self.registry, sector_rotation=entry)
        with self.assertRaisesRegex(TrustedArtifactError, "trusted_artifacts_session_calendar_mismatch"):
            build_trusted_broker_dashboard(
                TrustedArtifactStore(self.root, registry),
                decision_date="2026-11-26",
                decision_time="2026-11-26T12:00:00+05:45",
            )

    def test_late_broker_artifact_is_withheld(self):
        entry = dict(self.registry["broker_profiles"],
                     available_at="2026-11-26T12:01:00+05:45")
        registry = dict(self.registry, broker_profiles=entry)
        result = build_trusted_broker_dashboard(
            TrustedArtifactStore(self.root, registry),
            decision_date="2026-11-26",
            decision_time="2026-11-26T12:00:00+05:45",
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("broker_profiles", result["missing_modules"])


if __name__ == "__main__":
    unittest.main()
