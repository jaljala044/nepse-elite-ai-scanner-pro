import hashlib
import json
import unittest

from app.nepse_registry_schema_profiler import profile_registry_json


class NepseRegistrySchemaProfilerTests(unittest.TestCase):
    def test_profiles_nested_object_arrays_without_assigning_field_semantics(self):
        raw = json.dumps({
            "data": {
                "rows": [
                    {"securityId": 12, "symbol": "ABC", "active": True},
                    {"securityId": 13, "symbol": "XYZ", "active": None},
                ]
            }
        }).encode()
        result = profile_registry_json(raw)
        self.assertEqual(result["payload_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["payload_byte_count"], len(raw))
        candidate = next(
            item for item in result["object_array_candidates"]
            if item["path"] == "$.data.rows"
        )
        self.assertEqual(candidate["array_length"], 2)
        fields = {item["name"]: item for item in candidate["fields"]}
        self.assertEqual(fields["securityId"]["observed_types"], ["integer"])
        self.assertEqual(fields["active"]["observed_types"], ["boolean", "null"])
        self.assertFalse(result["field_semantics_assigned"])
        self.assertFalse(result["security_identity_verified"])
        self.assertFalse(result["membership_admission_allowed"])

    def test_reports_non_object_array_items_instead_of_silently_dropping_them(self):
        result = profile_registry_json(b'{"items":[{"id":1},null,4]}')
        item = result["object_array_candidates"][0]
        self.assertEqual(item["object_row_count"], 1)
        self.assertEqual(item["non_object_item_count"], 2)
        self.assertEqual(item["array_length"], 3)

    def test_handles_top_level_array(self):
        result = profile_registry_json(b'[{"code":"A"},{"code":"B"}]')
        self.assertEqual(result["json_root_type"], "array")
        self.assertEqual(result["object_array_candidates"][0]["path"], "$")

    def test_scalar_array_is_not_misreported_as_object_record_array(self):
        result = profile_registry_json(b'{"symbols":["ABC","XYZ"]}')
        self.assertEqual(result["object_array_candidates"], [])

    def test_rejects_empty_or_non_bytes_payload(self):
        for raw in (b"", "{}", None):
            with self.subTest(raw=raw), self.assertRaisesRegex(
                ValueError, "raw_payload_must_be_nonempty_bytes"
            ):
                profile_registry_json(raw)

    def test_rejects_invalid_json_and_scalar_root(self):
        with self.assertRaisesRegex(ValueError, "not_valid_json"):
            profile_registry_json(b"{")
        with self.assertRaisesRegex(ValueError, "root_must_be_object_or_array"):
            profile_registry_json(b'"just text"')

    def test_enforces_payload_depth_and_node_bounds(self):
        with self.assertRaisesRegex(ValueError, "exceeds_max_payload_bytes"):
            profile_registry_json(b'{"a":1}', max_payload_bytes=2)
        with self.assertRaisesRegex(ValueError, "max_depth"):
            profile_registry_json(b'{}', max_depth=33)
        with self.assertRaisesRegex(ValueError, "max_nodes"):
            profile_registry_json(b'{}', max_nodes=0)
        result = profile_registry_json(b'{"a":{"b":{"c":1}}}', max_depth=1)
        self.assertTrue(result["truncated"])

    def test_records_node_limit_truncation(self):
        result = profile_registry_json(b'{"items":[{"id":1},{"id":2}]}', max_nodes=2)
        self.assertTrue(result["truncated"])

    def test_rejects_boolean_integer_limit_values(self):
        with self.assertRaisesRegex(ValueError, "max_payload_bytes"):
            profile_registry_json(b'{}', max_payload_bytes=True)
        with self.assertRaisesRegex(ValueError, "max_nodes"):
            profile_registry_json(b'{}', max_nodes=True)


if __name__ == "__main__":
    unittest.main()
