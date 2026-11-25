import unittest
from datetime import date
from decimal import Decimal
from app.audit_bundle import build_audit_bundle, canonical_json_bytes


class AuditBundleTests(unittest.TestCase):
    def test_bundle_hash_is_deterministic_across_dictionary_order(self):
        a = build_audit_bundle({"source": {"b": 2, "a": 1}, "counts": [1, 2]})
        b = build_audit_bundle({"counts": [1, 2], "source": {"a": 1, "b": 2}})
        self.assertEqual(a["manifest"]["manifest_sha256"], b["manifest"]["manifest_sha256"])

    def test_decimal_and_date_are_serialized_exactly(self):
        raw = canonical_json_bytes({"amount": Decimal("10.050"), "date": date(2026, 11, 25)})
        self.assertEqual(raw, b'{"amount":"10.050","date":"2026-11-25"}')

    def test_artifact_hash_matches_embedded_content(self):
        import hashlib
        result = build_audit_bundle({"one": {"x": 1}})
        entry = result["artifacts"]["one"]
        self.assertEqual(entry["sha256"], hashlib.sha256(entry["content_utf8"].encode()).hexdigest())

    def test_non_finite_float_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"bad": float("nan")})

    def test_unsupported_object_rejected(self):
        with self.assertRaisesRegex(TypeError, "unsupported audit bundle value"):
            canonical_json_bytes({"bad": object()})

    def test_empty_bundle_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_audit_bundle({})


if __name__ == "__main__":
    unittest.main()
