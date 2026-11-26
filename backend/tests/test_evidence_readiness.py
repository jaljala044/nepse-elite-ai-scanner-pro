import json
import tempfile
import unittest
from pathlib import Path

from app.evidence_readiness import build_evidence_readiness, _reviewer_keys
from app.source_trust_registry import SourcePolicy, build_source_registry
from app import main


class EvidenceReadinessTests(unittest.TestCase):
    def test_unconfigured_runtime_fails_closed_without_creating_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "missing.duckdb"
            ledger = Path(tmp) / "missing.jsonl"
            result = build_evidence_readiness({
                "NEPSE_EVIDENCE_DATABASE": str(db),
                "NEPSE_PROMOTION_LEDGER_PATH": str(ledger),
            })
            self.assertEqual(result["status"], "not_configured")
            self.assertFalse(result["source_registry_valid"])
            self.assertFalse(result["evidence_store_exists"])
            self.assertFalse(result["production_eligible"])
            self.assertIn("source_registry_path", result["missing_requirements"])
            self.assertFalse(db.exists())
            self.assertFalse(ledger.exists())
            self.assertNotIn("reviewer_keys", result)

    def test_malformed_registry_is_reported_as_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text("[]")
            result = build_evidence_readiness({
                "NEPSE_SOURCE_REGISTRY_PATH": str(registry),
                "NEPSE_SOURCE_REGISTRY_SHA256": "0" * 64,
                "NEPSE_REVIEWER_KEYS_JSON": json.dumps({"reviewer": "11" * 32}),
                "NEPSE_EVIDENCE_DATABASE": str(Path(tmp) / "missing.duckdb"),
                "NEPSE_PROMOTION_LEDGER_PATH": str(Path(tmp) / "missing.jsonl"),
            })
            self.assertEqual(result["status"], "blocked")
            self.assertIn("source_registry_invalid", result["blockers"])
            self.assertFalse(result["production_eligible"])

    def test_bad_reviewer_key_configuration_is_never_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_evidence_readiness({
                "NEPSE_REVIEWER_KEYS_JSON": "{not-json",
                "NEPSE_EVIDENCE_DATABASE": str(Path(tmp) / "missing.duckdb"),
                "NEPSE_PROMOTION_LEDGER_PATH": str(Path(tmp) / "missing.jsonl"),
            })
            self.assertEqual(result["status"], "blocked")
            self.assertIn("reviewer_key_configuration_invalid", result["blockers"])
            self.assertNotIn("{not-json", json.dumps(result))

    def test_valid_registry_without_promoted_records_is_not_production_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = SourcePolicy(
                source_id="primary-fixture", publisher_name="Primary fixture",
                trust_tier="exchange_primary", allowed_record_types=("ohlcv",),
                canonical_record_types=("ohlcv",), status="active",
                effective_from="2020-01-01", effective_to=None,
                reviewer="registry-reviewer", reviewed_at="2026-11-25T00:00:00Z",
                evidence_refs=("evidence://review",), rights_state="research_only",
            )
            registry = build_source_registry([policy])
            registry_path = Path(tmp) / "registry.json"
            registry_path.write_text(json.dumps(registry))
            database = Path(tmp) / "evidence.duckdb"
            # Empty evidence store is created by the actual ingestion store.
            from app.evidence_store import _connect
            con = _connect(database)
            con.close()
            ledger = Path(tmp) / "promotion.jsonl"
            ledger.write_text("")
            result = build_evidence_readiness({
                "NEPSE_SOURCE_REGISTRY_PATH": str(registry_path),
                "NEPSE_SOURCE_REGISTRY_SHA256": registry["registry_sha256"],
                "NEPSE_REVIEWER_KEYS_JSON": json.dumps({"reviewer-1": "22" * 32}),
                "NEPSE_EVIDENCE_DATABASE": str(database),
                "NEPSE_PROMOTION_LEDGER_PATH": str(ledger),
            })
            self.assertTrue(result["source_registry_valid"])
            self.assertEqual(result["status"], "no_promoted_records")
            self.assertEqual(result["active_canonical_source_policy_count"], 1)
            self.assertEqual(result["canonical_record_count"], 0)
            self.assertFalse(result["production_eligible"])
            self.assertIn("accepted_canonical_promotions", result["missing_requirements"])

    def test_api_readiness_route_returns_only_diagnostics(self):
        result = main.evidence_readiness()
        self.assertIn("status", result)
        self.assertIn("production_eligible", result)
        self.assertNotIn("reviewer_keys", result)
        self.assertNotIn("records", result)


class ReviewerKeyParsingTests(unittest.TestCase):
    def test_keys_require_at_least_32_bytes(self):
        with self.assertRaisesRegex(ValueError, "at least 32 bytes"):
            _reviewer_keys(json.dumps({"reviewer": "ab" * 16}))

    def test_keys_are_decoded_but_never_returned_by_readiness(self):
        keys = _reviewer_keys(json.dumps({"reviewer": "cd" * 32}))
        self.assertEqual(len(keys["reviewer"]), 32)


if __name__ == "__main__":
    unittest.main()
