import unittest
from datetime import date
from app.temporal_registry import (
    SecurityMasterRecord, CorporateActionRecord,
    security_as_of, corporate_actions_as_of, validate_security_master_snapshot,
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

    def test_security_master_snapshot_counts_only_explicit_instrument_types(self):
        rows = [
            SecurityMasterRecord("S1", "ABC", "equity", "active", date(2020,1,1), None, "e1"),
            SecurityMasterRecord("S2", "FUND1", "mutual_fund", "active", date(2021,1,1), None, "e2"),
            SecurityMasterRecord("S3", "OLD1", "non_convertible_debenture", "delisted",
                                 date(2018,1,1), date(2020,12,31), "e3"),
        ]
        result = validate_security_master_snapshot(rows)
        self.assertEqual(result["unique_security_ids"], 3)
        self.assertEqual(result["instrument_type_counts"]["equity"], 1)
        self.assertEqual(result["instrument_type_counts"]["mutual_fund"], 1)

    def test_unknown_instrument_type_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported instrument_type"):
            SecurityMasterRecord("S1", "ABC", "ticker_guess", "active",
                                 date(2020,1,1), None, "e1")

    def test_overlapping_conflicting_lifecycle_rows_fail(self):
        rows = [
            SecurityMasterRecord("S1", "ABC", "equity", "active", date(2020,1,1), None, "e1"),
            SecurityMasterRecord("S1", "XYZ", "equity", "active", date(2022,1,1), None, "e2"),
        ]
        with self.assertRaisesRegex(ValueError, "overlapping conflicting"):
            validate_security_master_snapshot(rows)

    def test_symbol_overlap_across_security_ids_fails(self):
        rows = [
            SecurityMasterRecord("S1", "ABC", "equity", "active", date(2020,1,1), None, "e1"),
            SecurityMasterRecord("S2", "ABC", "mutual_fund", "active", date(2022,1,1), None, "e2"),
        ]
        with self.assertRaisesRegex(ValueError, "overlaps across distinct"):
            validate_security_master_snapshot(rows)

    def test_noncanonical_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "uppercase"):
            SecurityMasterRecord("S1", "abc", "equity", "active",
                                 date(2020,1,1), None, "e1")

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
