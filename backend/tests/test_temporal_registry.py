import unittest
from datetime import date
from app.temporal_registry import (
    SecurityMasterRecord, CorporateActionRecord,
    security_as_of, corporate_actions_as_of,
)


class TemporalRegistryTests(unittest.TestCase):
    def test_security_lifecycle_is_effective_dated(self):
        rows = [
            SecurityMasterRecord("S1", "OLD", "equity", "active", date(2020,1,1), date(2024,12,31), "e1"),
            SecurityMasterRecord("S1", "NEW", "equity", "active", date(2025,1,1), None, "e2"),
        ]
        self.assertEqual(security_as_of(rows, date(2024,6,1))["record"].symbol, "OLD")
        self.assertEqual(security_as_of(rows, date(2025,6,1))["record"].symbol, "NEW")

    def test_conflicting_overlapping_security_records_are_ambiguous(self):
        rows = [
            SecurityMasterRecord("S1", "ABC", "equity", "active", date(2020,1,1), None, "e1"),
            SecurityMasterRecord("S1", "XYZ", "equity", "active", date(2022,1,1), None, "e2"),
        ]
        self.assertEqual(security_as_of(rows, date(2023,1,1))["status"], "ambiguous")

    def test_invalid_security_date_range_rejected(self):
        with self.assertRaises(ValueError):
            SecurityMasterRecord("S1", "ABC", "equity", "active", date(2025,1,2), date(2025,1,1), "e")

    def test_late_known_corporate_action_is_excluded(self):
        actions = [
            CorporateActionRecord("A1","S1","bonus",date(2026,11,20),
                                  "2026-11-18T09:00:00Z","2026-11-18T09:00:00Z",1.1,"e1"),
            CorporateActionRecord("A2","S1","right",date(2026,11,21),
                                  "2026-11-24T09:00:00Z","2026-11-24T09:00:00Z",1.2,"e2"),
        ]
        result = corporate_actions_as_of(actions, "S1", "2026-11-22T12:00:00Z")
        self.assertEqual([a.action_id for a in result["actions"]], ["A1"])
        self.assertTrue(result["point_in_time_eligible"])

    def test_naive_corporate_action_timestamp_rejected(self):
        action = CorporateActionRecord("A1","S1","bonus",date(2026,11,20),
                                       "2026-11-18T09:00:00","2026-11-18T09:00:00",1.1,"e1")
        with self.assertRaises(ValueError):
            corporate_actions_as_of([action], "S1", "2026-11-22T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
