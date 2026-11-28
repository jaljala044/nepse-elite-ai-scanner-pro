import json
import tempfile
import unittest
from pathlib import Path

from app.sector_evidence_registry import load_sector_evidence_registry, sign_registry_payload
from app.sector_membership_manifest import manifest_digest

KEY = "test-registry-key-with-at-least-32-characters"
DECISION = "2026-11-26T18:00:00+05:45"


def build_registry():
    digest = "a" * 64
    manifest = {
        "schema_version": 1, "source_id": "source-1",
        "source_payload_sha256": digest, "captured_at": "2026-11-26T10:00:00Z",
        "records": [
            {"record_id": "r1", "symbol": "AAA", "sector_code": "BANK",
             "effective_from": "2026-01-01", "effective_to": None,
             "source_id": "source-1", "source_payload_sha256": digest,
             "source_record_ref": "page:1"},
            {"record_id": "r2", "symbol": "BBB", "sector_code": "HYDRO",
             "effective_from": "2026-01-01", "effective_to": None,
             "source_id": "source-1", "source_payload_sha256": digest,
             "source_record_ref": "page:2"},
        ],
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    attestation = {
        "reviewer_id": "reviewer-01", "reviewed_at": "2026-11-26T11:00:00Z",
        "scope": "sector_membership_research", "decision": "approved_for_research",
    }
    attestation["signature_hmac_sha256"] = sign_registry_payload(attestation, KEY)
    registry = {
        "schema_version": 1, "generated_at": "2026-11-26T11:30:00Z",
        "allowed_sector_codes": ["BANK", "HYDRO"],
        "entries": [{
            "expected_symbols": ["AAA", "BBB"],
            "manifest": manifest, "reviewer_attestation": attestation,
        }],
    }
    registry["registry_signature_hmac_sha256"] = sign_registry_payload(registry, KEY)
    return registry


class SectorEvidenceRegistryTests(unittest.TestCase):
    def load(self, data, key=KEY, decision=DECISION):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_sector_evidence_registry(
                path, key, expected_symbols=["AAA", "BBB"], decision_time=decision,
            )

    def test_valid_registry_is_internally_attested_but_not_exchange_verified(self):
        result = self.load(build_registry())
        self.assertEqual(result["status"], "internally_attested_research_only")
        self.assertEqual(result["membership"], {"AAA": "BANK", "BBB": "HYDRO"})
        self.assertFalse(result["verified"])
        self.assertFalse(result["admission_allowed"])

    def test_missing_configuration_fails_closed(self):
        result = load_sector_evidence_registry(None, None, expected_symbols=["AAA"], decision_time=DECISION)
        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(result["verified"])

    def test_bad_registry_signature_rejected(self):
        data = build_registry()
        data["allowed_sector_codes"].append("FINANCE")
        self.assertEqual(self.load(data)["reason"], "registry_signature_invalid")

    def test_bad_reviewer_signature_rejected_even_if_registry_resigned(self):
        data = build_registry()
        data["entries"][0]["reviewer_attestation"]["reviewer_id"] = "forged"
        data["registry_signature_hmac_sha256"] = sign_registry_payload(data, KEY)
        self.assertEqual(self.load(data)["reason"], "entry_0_reviewer_signature_invalid")

    def test_incomplete_universe_coverage_withheld(self):
        data = build_registry()
        data["entries"][0]["expected_symbols"] = ["AAA"]
        data["registry_signature_hmac_sha256"] = sign_registry_payload(data, KEY)
        result = self.load(data)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["membership"], {})

    def test_registry_after_decision_time_rejected(self):
        data = build_registry()
        data["generated_at"] = "2026-11-27T00:00:00Z"
        data["registry_signature_hmac_sha256"] = sign_registry_payload(data, KEY)
        self.assertEqual(self.load(data)["reason"], "registry_generated_after_decision_time")

    def test_future_reviewer_attestation_rejected(self):
        data = build_registry()
        data["entries"][0]["reviewer_attestation"]["reviewed_at"] = "2026-11-27T00:00:00Z"
        data["entries"][0]["reviewer_attestation"]["signature_hmac_sha256"] = sign_registry_payload(
            {k: v for k, v in data["entries"][0]["reviewer_attestation"].items() if k != "signature_hmac_sha256"}, KEY
        )
        data["registry_signature_hmac_sha256"] = sign_registry_payload(data, KEY)
        self.assertEqual(self.load(data)["reason"], "entry_0_reviewer_attestation_invalid")

    def test_missing_or_short_key_does_not_load(self):
        self.assertEqual(self.load(build_registry(), "short")["reason"], "hmac_key_too_short")

    def test_missing_candidate_symbol_fails_closed(self):
        result = load_sector_evidence_registry(
            None, None, expected_symbols=["AAA", "BBB"], decision_time=DECISION,
        )
        self.assertEqual(result["coverage_pct"], 0.0)

    def test_registry_path_must_be_readable(self):
        result = load_sector_evidence_registry(
            "/path/that/does/not/exist", KEY, expected_symbols=["AAA"], decision_time=DECISION,
        )
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
