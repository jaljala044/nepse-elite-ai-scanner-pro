import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.daily_market_candidate_handoff import run_daily_candidate_handoff

class HandoffTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"bundles"
        self.source.mkdir()
        self.signatures=self.root/"signatures"
        self.signatures.mkdir()
        self.output=self.root/"candidates"
        self.registry=self.root/"trusted"/"registry.json"
        self.date="2026-11-27"
        self.cutoff="2026-11-27T17:00:00+05:45"
        self.key=Ed25519PrivateKey.generate()
        self.public=self.key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)

    def run_handoff(self, **changes):
        args=dict(session_date=self.date,decision_time=self.cutoff,
            trusted_registry_path=self.registry,signature_dir=self.signatures,
            public_key_pem=self.public)
        args.update(changes)
        return run_daily_candidate_handoff(self.source,self.output,**args)

    def write(self,**changes):
        bundle=dict(calendar={"sessions":[self.date]},decision_time=self.cutoff,
            universe={"symbols":["A"]},daily_rows=[],benchmark_rows=[],index_rows=[],
            expected_indices=["NEPSE"],stock_rows=[],expected_sector_members={},
            sector_membership={})
        bundle.update(changes)
        raw=json.dumps(bundle).encode()
        (self.source/(self.date+".json")).write_bytes(raw)
        (self.signatures/(self.date+".sig")).write_bytes(base64.b64encode(self.key.sign(raw)))

    def test_missing(self):
        self.assertEqual(self.run_handoff()["status"],"missing_reviewed_bundle")
        self.assertFalse(self.output.exists())

    def test_future(self):
        with self.assertRaisesRegex(ValueError,"future_session"):
            self.run_handoff(session_date="2026-11-28")

    def test_wrong_session(self):
        self.write(calendar={"sessions":["2026-11-26"]})
        with self.assertRaisesRegex(ValueError,"protected_bundle_session_mismatch"):
            self.run_handoff()

    def test_late_bundle(self):
        self.write(decision_time="2026-11-27T18:00:00+05:45")
        with self.assertRaisesRegex(ValueError,"protected_bundle_after_decision_cutoff"):
            self.run_handoff()

    def test_registry_overlap(self):
        with self.assertRaisesRegex(ValueError,"candidate_storage_overlaps_registry"):
            self.run_handoff(trusted_registry_path=self.output/"registry.json")

    def test_candidate_only(self):
        self.write()
        with patch("app.daily_market_candidate_handoff.generate_market_candidates",
            return_value=dict(as_of_session=self.date,manifest_path="m.json",manifest_sha256="a"*64)) as generate:
            result=self.run_handoff()
        generate.assert_called_once()
        self.assertTrue(result["signature_verified"])
        self.assertEqual(result["status"],"review_required")
        self.assertFalse(result["promotion_allowed"])
        self.assertFalse(result["signals_enabled"])
        self.assertFalse(self.registry.exists())

    def test_unsigned_bundle_rejected(self):
        self.write()
        (self.signatures/(self.date+".sig")).write_text("bad")
        with self.assertRaisesRegex(ValueError,"protected_bundle_signature_invalid"):
            self.run_handoff()

    def test_no_public_key_rejected(self):
        self.write()
        with self.assertRaisesRegex(ValueError,"protected_bundle_verification_required"):
            self.run_handoff(public_key_pem=None)
