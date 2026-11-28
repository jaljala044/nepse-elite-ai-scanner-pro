from __future__ import annotations

import json
import unittest
from pathlib import Path


SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "hrl_conflict_record.schema.json"


class HRLConflictJSONSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_uses_current_json_schema_draft(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_identity_and_no_promotion_are_fixed(self):
        props = self.schema["properties"]
        self.assertEqual(props["symbol_id"], {"const": "HRL"})
        self.assertEqual(props["canonical_promotion_allowed"], {"const": False})

    def test_both_source_hashes_and_rows_are_required(self):
        props = self.schema["properties"]
        expected = {"nepse-history-starter", "nepse-smc-data"}
        self.assertEqual(set(props["source_archive_sha256"]["required"]), expected)
        self.assertEqual(set(props["source_rows"]["required"]), expected)

    def test_raw_and_project_values_remain_separate(self):
        required = set(self.schema["required"])
        self.assertIn("raw_low", required)
        self.assertIn("project_designated_low", required)
        self.assertNotEqual("raw_low", "project_designated_low")

    def test_quarantined_and_resolved_rules_are_declared(self):
        branches = self.schema["allOf"]
        self.assertEqual(len(branches), 2)
        serialized = json.dumps(branches, sort_keys=True)
        self.assertIn("QUARANTINED", serialized)
        self.assertIn("RESOLVED", serialized)
        self.assertIn('"A"', serialized)
        self.assertIn('"B"', serialized)
        self.assertIn('"C"', serialized)

    def test_unknown_properties_are_rejected(self):
        self.assertFalse(self.schema["additionalProperties"])
        self.assertFalse(self.schema["properties"]["source_rows"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
