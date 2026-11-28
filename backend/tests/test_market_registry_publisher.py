import base64
import json
import unittest
from hashlib import sha256
from unittest.mock import patch
from test_market_artifact_approval import ApprovalTests
from app.market_registry_publisher import publish_approved_registry


class PublisherTests(unittest.TestCase):
    def setUp(self):
        fixture = ApprovalTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.destination = fixture.root / "registry.json"
        self.registry = {
            name: dict(payload_path=entry["payload_path"],
                payload_sha256=entry["payload_sha256"], as_of_date="2026-11-27",
                available_at="2026-11-27T11:00:00Z")
            for name, entry in fixture.entries.items()
        }

    def publish(self, *, tamper=False, valid_admission=True, mismatch=False):
        f = self.fixture
        raw = json.dumps(self.registry).encode()
        approval = json.dumps(dict(f.approval,registry_sha256=sha256(raw).hexdigest())).encode()
        sig = base64.b64encode(f.key.sign(approval))
        if tamper:
            raw += b" "
        results = {name: dict(evidence_gate_passed=valid_admission,
            session_calendar_id=("other" if mismatch and name=="sector_rotation" else "calendar"))
            for name in self.registry}
        with patch("app.market_registry_publisher.TrustedArtifactStore.load",return_value=results):
            return publish_approved_registry(f.root,self.destination,raw,approval,sig,
                public_key_pem=f.public,expected_reviewer_id="independent-test",
                decision_time="2026-11-27T12:00:00Z")

    def test_publish_and_repeat(self):
        self.assertEqual(self.publish()["status"],"published_research_registry")
        original=self.destination.read_bytes()
        self.assertEqual(json.loads(original),self.registry)
        self.assertEqual(self.publish()["status"],"already_published")
        self.assertEqual(self.destination.read_bytes(),original)
        self.assertEqual(list(self.fixture.root.glob(".registry-*")),[])

    def test_registry_tampering(self):
        with self.assertRaisesRegex(ValueError,"approval_registry_hash_mismatch"):
            self.publish(tamper=True)
        self.assertFalse(self.destination.exists())

    def test_rejected_admission_preserves_registry(self):
        self.publish()
        original=self.destination.read_bytes()
        with self.assertRaisesRegex(ValueError,"registry_artifact_admission_failed"):
            self.publish(valid_admission=False)
        self.assertEqual(self.destination.read_bytes(),original)

    def test_calendar_mismatch(self):
        with self.assertRaisesRegex(ValueError,"registry_calendar_mismatch"):
            self.publish(mismatch=True)
        self.assertFalse(self.destination.exists())

    def test_rollback_rejected(self):
        future={k:dict(v,as_of_date="2026-11-28") for k,v in self.registry.items()}
        original=json.dumps(future).encode()
        self.destination.write_bytes(original)
        with self.assertRaisesRegex(ValueError,"registry_rollback_rejected"):
            self.publish()
        self.assertEqual(self.destination.read_bytes(),original)
