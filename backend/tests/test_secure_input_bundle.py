import base64
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.secure_input_bundle import verify_protected_input_bundle

class ProtectedBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.bundle_path=self.root/"2026-11-27.json"
        self.signature_path=self.root/"2026-11-27.sig"
        self.key=Ed25519PrivateKey.generate()
        self.public=self.key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
        self.bundle=dict(decision_time="2026-11-27T16:00:00+05:45",
            calendar={"sessions":["2026-11-27"]},universe={"symbols":["A"]},
            daily_rows=[],benchmark_rows=[],index_rows=[],expected_indices=["NEPSE"],
            stock_rows=[],expected_sector_members={},sector_membership={})
        self.write()

    def write(self, bundle=None):
        raw=json.dumps(bundle or self.bundle,sort_keys=True).encode()
        self.bundle_path.write_bytes(raw)
        self.signature_path.write_bytes(base64.b64encode(self.key.sign(raw)))

    def verify(self, **changes):
        return verify_protected_input_bundle(self.bundle_path,self.signature_path,
            public_key_pem=self.public,expected_session="2026-11-27",
            decision_time="2026-11-27T17:00:00+05:45",**changes)

    def test_valid_signed_bundle(self):
        result=self.verify()
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["source_authorization_attested"])
        self.assertFalse(result["promotion_allowed"])

    def test_tampered_bundle(self):
        self.bundle_path.write_bytes(self.bundle_path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError,"protected_bundle_signature_invalid"): self.verify()

    def test_wrong_key(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
        with self.assertRaisesRegex(ValueError,"protected_bundle_signature_invalid"):
            verify_protected_input_bundle(self.bundle_path,self.signature_path,
                public_key_pem=other,expected_session="2026-11-27",
                decision_time="2026-11-27T17:00:00+05:45")

    def test_incomplete_schema(self):
        self.write({"decision_time":self.bundle["decision_time"],"calendar":self.bundle["calendar"]})
        with self.assertRaisesRegex(ValueError,"protected_bundle_schema_incomplete"): self.verify()

    def test_session_mismatch(self):
        altered=dict(self.bundle,calendar={"sessions":["2026-11-26"]})
        self.write(altered)
        with self.assertRaisesRegex(ValueError,"protected_bundle_session_mismatch"): self.verify()

    def test_late_bundle(self):
        altered=dict(self.bundle,decision_time="2026-11-27T18:00:00+05:45")
        self.write(altered)
        with self.assertRaisesRegex(ValueError,"protected_bundle_after_decision_cutoff"): self.verify()

    def test_missing_signature(self):
        self.signature_path.unlink()
        with self.assertRaisesRegex(ValueError,"protected_bundle_or_signature_missing"): self.verify()

    def test_signature_symlink_rejected(self):
        self.signature_path.unlink()
        self.signature_path.symlink_to(self.bundle_path)
        with self.assertRaisesRegex(ValueError,"protected_bundle_or_signature_missing"): self.verify()

    def test_duplicate_json_keys_rejected_after_valid_signature(self):
        raw=b'{"decision_time":"2026-11-27T16:00:00+05:45","decision_time":"2026-11-27T16:00:00+05:45"}'
        self.bundle_path.write_bytes(raw)
        self.signature_path.write_bytes(base64.b64encode(self.key.sign(raw)))
        with self.assertRaisesRegex(ValueError,"protected_bundle_duplicate_json_key"):
            self.verify()

    def test_non_finite_json_number_rejected_after_valid_signature(self):
        raw=json.dumps(dict(self.bundle,extra=float("nan"))).encode()
        self.bundle_path.write_bytes(raw)
        self.signature_path.write_bytes(base64.b64encode(self.key.sign(raw)))
        with self.assertRaisesRegex(ValueError,"protected_bundle_non_finite_json_number"):
            self.verify()

    def test_future_session_uses_nepal_local_date(self):
        # UTC date has rolled over, but Kathmandu is still on the prior date.
        result=verify_protected_input_bundle(self.bundle_path,self.signature_path,
            public_key_pem=self.public,expected_session="2026-11-27",
            decision_time="2026-11-26T19:00:00Z")
        self.assertTrue(result["signature_verified"])
