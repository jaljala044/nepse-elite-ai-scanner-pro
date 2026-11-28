import tempfile
import unittest
from pathlib import Path

from app.source_quality_review import load_source_quality_review_registry, sign_review_attestation, sign_review_registry
from app.source_data_quality_store import (
    persist_source_data_quality_batch,
    replay_source_data_quality,
    source_data_quality_readiness,
)

HASH = "a" * 64
CAPTURED = "2026-11-28T10:00:00Z"
RECEIVED = "2026-11-28T10:05:00Z"
DECISION = "2026-11-28T12:00:00Z"
KEY = "unit-test-review-key-with-at-least-32-characters"


def sample_bundle():
    return {
        "calendar_sessions": [{
            "date": "2026-11-27", "status": "confirmed_open",
            "review_status": "reviewed", "reviewer_id": "reviewer-1",
            "source_id": "calendar-source", "source_payload_sha256": HASH,
            "available_at": "2026-11-27T08:00:00Z",
        }],
        "capture_policies": [{
            "source_id": "sharesansar", "dataset": "ohlcv",
            "expected_sessions": ["2026-11-27"], "max_age_hours": 48,
            "review_status": "reviewed", "reviewer_id": "reviewer-1",
        }],
        "captures": [{
            "source_id": "sharesansar", "dataset": "ohlcv",
            "session_date": "2026-11-27",
            "captured_at": "2026-11-27T10:00:00Z",
            "available_at": "2026-11-27T10:05:00Z",
            "payload_sha256": HASH,
        }],
        "observations": [
            {"dataset": "ohlcv", "symbol": "NABIL", "session_date": "2026-11-27",
             "source_id": "sharesansar", "value": 500},
            {"dataset": "ohlcv", "symbol": "NABIL", "session_date": "2026-11-27",
             "source_id": "chukul", "value": 500},
        ],
        "correction_records": [{
            "record_id": "record-1", "available_at": "2026-11-27T10:00:00Z",
            "value": 500,
        }],
    }


class SourceDataQualityStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "evidence.duckdb"
        self.raw = self.root / "raw"

    def tearDown(self):
        self.tmp.cleanup()

    def persist(self, bundle=None, batch="quality-batch-1"):
        return persist_source_data_quality_batch(
            bundle or sample_bundle(), batch_id=batch,
            captured_at=CAPTURED, received_at=RECEIVED,
            storage_root=self.raw, database_path=self.db,
        )

    def test_persists_review_required_typed_evidence(self):
        result = self.persist()
        self.assertEqual(result["evidence_count"], 6)
        self.assertEqual(result["source_validation_status"], "review_required")
        self.assertFalse(result["production_admission_allowed"])

    def test_exact_retry_is_idempotent(self):
        first, second = self.persist(), self.persist()
        self.assertEqual(first["fetch_id"], second["fetch_id"])
        self.assertEqual(second["idempotent"], True)

    def test_changed_payload_for_same_batch_is_rejected(self):
        self.persist()
        changed = sample_bundle()
        changed["observations"][0]["value"] = 501
        with self.assertRaisesRegex(ValueError, "different immutable"):
            self.persist(changed)

    def test_duplicate_evidence_identity_across_batches_is_rejected(self):
        bundle = sample_bundle()
        bundle["calendar_sessions"][0]["evidence_id"] = "calendar-row-1"
        self.persist(bundle)
        with self.assertRaisesRegex(ValueError, "evidence_id_already_persisted"):
            self.persist(bundle, batch="quality-batch-2")

    def test_duplicate_identity_inside_batch_is_rejected(self):
        bundle = sample_bundle()
        bundle["calendar_sessions"][0]["evidence_id"] = "same"
        bundle["captures"][0]["evidence_id"] = "same"
        with self.assertRaisesRegex(ValueError, "duplicate_evidence_id"):
            self.persist(bundle)

    def test_historical_replay_excludes_future_available_evidence(self):
        rows = [{
            "available_at": "2026-11-29T00:00:00Z",
            "evidence_kind": "calendar_session",
            "evidence": sample_bundle()["calendar_sessions"][0],
        }]
        result = replay_source_data_quality(rows, decision_time=DECISION)
        self.assertEqual(result["selected_evidence_count"], 0)
        self.assertEqual(result["excluded_future_or_invalid_count"], 1)
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_replay_keeps_disagreement_without_canonical_value(self):
        self.persist()
        from app.source_data_quality_store import load_source_data_quality_evidence
        loaded = load_source_data_quality_evidence(database_path=self.db)
        replay = replay_source_data_quality(loaded["rows"], decision_time=DECISION)
        self.assertEqual(replay["cross_source_reconciliation"]["conflict_count"], 0)
        self.assertIsNone(replay["cross_source_reconciliation"]["results"][0]["canonical_value"])
        self.assertFalse(replay["canonical_promotion_allowed"])

    def test_conflicting_sources_remain_conflicting(self):
        bundle = sample_bundle()
        bundle["observations"][1]["value"] = 501
        self.persist(bundle)
        from app.source_data_quality_store import load_source_data_quality_evidence
        loaded = load_source_data_quality_evidence(database_path=self.db)
        replay = replay_source_data_quality(loaded["rows"], decision_time=DECISION)
        self.assertEqual(replay["cross_source_reconciliation"]["conflict_count"], 1)
        self.assertEqual(replay["data_quality_report"]["data_quality"], "LOW")

    def test_single_source_observation_cannot_claim_high_data_quality(self):
        bundle = sample_bundle()
        bundle["observations"] = bundle["observations"][:1]
        self.persist(bundle)
        from app.source_data_quality_store import load_source_data_quality_evidence
        loaded = load_source_data_quality_evidence(database_path=self.db)
        replay = replay_source_data_quality(loaded["rows"], decision_time=DECISION)
        self.assertEqual(replay["data_quality_report"]["data_quality"], "LOW")
        self.assertIn("cross_source_corroboration_incomplete",
                      replay["data_quality_report"]["reasons"])

    def test_missing_database_is_not_created(self):
        absent = self.root / "missing.duckdb"
        result = source_data_quality_readiness(database_path=absent, decision_time=DECISION)
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(absent.exists())
        self.assertFalse(result["production_admission_allowed"])

    def test_signed_calendar_and_policy_reviews_enable_diagnostic_quality(self):
        bundle = sample_bundle()
        for scope, field in (("calendar_session", "calendar_sessions"),
                             ("capture_policy", "capture_policies")):
            for item in bundle[field]:
                item["review_attestation"] = sign_review_attestation(
                    item, reviewer_id="reviewer-1", scope=scope,
                    reviewed_at="2026-11-28T10:00:00Z", key=KEY,
                )
        self.persist(bundle)
        registry = sign_review_registry({
            "schema_version": 1,
            "generated_at": "2026-11-28T10:00:00Z",
            "reviewers": [{
                "reviewer_id": "reviewer-1",
                "allowed_scopes": ["calendar_session", "capture_policy"],
                "status": "approved",
            }],
        }, KEY)
        registry_path = self.root / "review-registry.json"
        import json
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        result = source_data_quality_readiness(
            database_path=self.db, decision_time=DECISION,
            review_registry_path=registry_path, hmac_key=KEY,
        )
        self.assertEqual(result["review_registry_status"], "review_registry_loaded")
        self.assertEqual(result["data_quality"], "HIGH")
        self.assertEqual(result["replay"]["review_attestation"]["calendar_reviewed_count"], 1)
        self.assertFalse(result["production_admission_allowed"])

    def test_ready_store_remains_diagnostic_only(self):
        self.persist()
        result = source_data_quality_readiness(database_path=self.db, decision_time=DECISION)
        self.assertEqual(result["status"], "assessed")
        self.assertEqual(result["data_quality"], "LOW")
        self.assertEqual(result["review_registry_status"], "not_configured")
        self.assertFalse(result["production_admission_allowed"])
        self.assertFalse(result["recommendation_override"])


if __name__ == "__main__":
    unittest.main()
