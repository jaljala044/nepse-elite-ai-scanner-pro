import unittest
from datetime import datetime, timezone

from app.sector_membership_manifest import (
    audit_sector_membership_manifest,
    manifest_digest,
)

DIGEST = "a" * 64
CUTOFF = "2026-11-26T18:00:00+05:45"


def fixture():
    manifest = {
        "schema_version": 1,
        "source_id": "candidate-source-v1",
        "source_payload_sha256": DIGEST,
        "captured_at": "2026-11-26T10:00:00Z",
        "records": [
            {"record_id": "r1", "symbol": "AAA", "sector_code": "BANK",
             "effective_from": "2026-01-01", "effective_to": None,
             "source_id": "candidate-source-v1", "source_payload_sha256": DIGEST,
             "source_record_ref": "page:1"},
            {"record_id": "r2", "symbol": "BBB", "sector_code": "HYDRO",
             "effective_from": "2026-01-01", "effective_to": None,
             "source_id": "candidate-source-v1", "source_payload_sha256": DIGEST,
             "source_record_ref": "page:2"},
        ],
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return manifest


class SectorMembershipManifestTests(unittest.TestCase):
    def audit(self, manifest=None, **kwargs):
        return audit_sector_membership_manifest(
            manifest or fixture(), expected_symbols=["AAA", "BBB"],
            allowed_sector_codes={"BANK", "HYDRO"}, decision_time=CUTOFF, **kwargs
        )

    def test_nepal_local_cutoff_date_controls_effective_membership(self):
        manifest = fixture()
        manifest["records"][0]["effective_from"] = "2026-11-27"
        manifest["records"][1]["effective_from"] = "2026-11-27"
        manifest["manifest_sha256"] = manifest_digest(manifest)
        # 2026-11-27 00:15 in Nepal is still 2026-11-26 in UTC.
        result = audit_sector_membership_manifest(
            manifest, expected_symbols=["AAA", "BBB"],
            allowed_sector_codes={"BANK", "HYDRO"},
            decision_time="2026-11-27T00:15:00+05:45",
        )
        self.assertEqual(result["as_of_date"], "2026-11-27")
        self.assertEqual(result["status"], "review_ready")

    def test_invalid_expected_symbol_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected_symbols_must_be_unique_nonempty"):
            audit_sector_membership_manifest(
                fixture(), expected_symbols=[None], allowed_sector_codes={"BANK"},
                decision_time=CUTOFF,
            )

    def test_valid_manifest_is_review_ready_not_verified(self):
        result = self.audit()
        self.assertEqual(result["status"], "review_ready")
        self.assertEqual(result["coverage_pct"], 100)
        self.assertFalse(result["verified"])
        self.assertFalse(result["admission_allowed"])

    def test_manifest_digest_tampering_rejected(self):
        manifest = fixture()
        manifest["records"][0]["sector_code"] = "HYDRO"
        with self.assertRaisesRegex(ValueError, "manifest_sha256_mismatch"):
            self.audit(manifest)

    def test_missing_symbol_withholds_full_coverage(self):
        manifest = fixture()
        manifest["records"].pop()
        manifest["manifest_sha256"] = manifest_digest(manifest)
        result = self.audit(manifest, minimum_coverage=1.0)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["missing_symbols"], ["BBB"])

    def test_future_capture_rejected(self):
        manifest = fixture()
        manifest["captured_at"] = "2026-11-27T00:00:00Z"
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "captured_after_decision_time"):
            self.audit(manifest)

    def test_unknown_sector_rejected(self):
        manifest = fixture()
        manifest["records"][0]["sector_code"] = "UNKNOWN"
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "invalid_identity"):
            self.audit(manifest)

    def test_overlapping_intervals_rejected(self):
        manifest = fixture()
        extra = dict(manifest["records"][0])
        extra.update(record_id="r3", effective_from="2026-06-01")
        manifest["records"].append(extra)
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "overlapping_effective_intervals"):
            self.audit(manifest)

    def test_adjacent_non_overlapping_intervals_allowed(self):
        manifest = fixture()
        first = manifest["records"][0]
        first["effective_to"] = "2026-06-30"
        second = dict(first, record_id="r3", sector_code="HYDRO",
                      effective_from="2026-07-01", effective_to=None)
        manifest["records"].append(second)
        manifest["manifest_sha256"] = manifest_digest(manifest)
        result = self.audit(manifest)
        self.assertEqual(result["membership"]["AAA"], "HYDRO")

    def test_record_digest_must_match_manifest(self):
        manifest = fixture()
        manifest["records"][0]["source_payload_sha256"] = "b" * 64
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "payload_digest_mismatch"):
            self.audit(manifest)

    def test_missing_record_reference_rejected(self):
        manifest = fixture()
        manifest["records"][0]["source_record_ref"] = ""
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "source_record_ref_required"):
            self.audit(manifest)

    def test_invalid_effective_interval_rejected(self):
        manifest = fixture()
        manifest["records"][0]["effective_to"] = "2025-12-31"
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaisesRegex(ValueError, "effective_interval_reversed"):
            self.audit(manifest)


if __name__ == "__main__":
    unittest.main()
