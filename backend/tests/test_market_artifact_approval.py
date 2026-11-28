import base64
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.market_artifact_approval import verify_market_approval

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        entries = {}
        for module in ("daily_market_participation","index_rotation","sector_rotation"):
            data = {"signals_enabled":False,"module":module,
                    "as_of" if module=="index_rotation" else "as_of_session":"2026-11-27"}
            raw = json.dumps(data).encode()
            digest = sha256(raw).hexdigest()
            path = digest+".json"
            (self.root/path).write_bytes(raw)
            entries[module] = dict(payload_path=path,payload_sha256=digest,byte_count=len(raw),status="review_required")
        manifest = dict(schema_version=1,status="review_required",promotion_allowed=False,
            signals_enabled=False,input_bundle_sha256="a"*64,decision_time="2026-11-27T10:00:00Z",
            as_of_session="2026-11-27",artifacts=entries)
        raw = json.dumps(manifest).encode()
        digest = sha256(raw).hexdigest()
        (self.root/(digest+".manifest.json")).write_bytes(raw)
        self.approval = dict(schema_version=1,reviewer_id="independent-test",
            decision="approved_for_research",signals_enabled=False,approved_at="2026-11-27T11:00:00Z",
            manifest_path=digest+".manifest.json",manifest_sha256=digest,input_bundle_sha256="a"*64)
        self.entries = entries

    def verify(self, changes=None, tamper=False, wrong_key=False):
        raw = json.dumps(dict(self.approval,**(changes or {}))).encode()
        sig = base64.b64encode(self.key.sign(raw))
        if tamper:
            raw += b" "
        pub = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo) if wrong_key else self.public
        return verify_market_approval(self.root,raw,sig,public_key_pem=pub,
            expected_reviewer_id="independent-test",decision_time="2026-11-27T12:00:00Z")

    def test_valid(self):
        result=self.verify()
        self.assertEqual(result["status"],"signature_verified")
        self.assertFalse(result["registry_published"])

    def test_tampered_signature(self):
        with self.assertRaisesRegex(ValueError,"approval_signature_invalid"): self.verify(tamper=True)

    def test_wrong_key(self):
        with self.assertRaisesRegex(ValueError,"approval_signature_invalid"): self.verify(wrong_key=True)

    def test_wrong_reviewer(self):
        with self.assertRaisesRegex(ValueError,"approval_scope_invalid"): self.verify({"reviewer_id":"other"})

    def test_future_approval(self):
        with self.assertRaisesRegex(ValueError,"approval_after_cutoff"): self.verify({"approved_at":"2026-11-28T00:00:00Z"})

    def test_payload_tampering(self):
        (self.root/self.entries["sector_rotation"]["payload_path"]).write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError,"approved_payload_hash_mismatch"): self.verify()

    def test_manifest_tampering(self):
        (self.root/self.approval["manifest_path"]).write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError,"approval_manifest_hash_mismatch"): self.verify()
