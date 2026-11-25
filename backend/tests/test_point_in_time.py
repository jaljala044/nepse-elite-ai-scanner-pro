import unittest
from app.point_in_time import eligible_as_of, build_as_of_snapshot


class PointInTimeTests(unittest.TestCase):
    def test_late_publication_is_excluded(self):
        rows = [
            {"record_id":"a","available_at":"2026-11-24T10:00:00Z"},
            {"record_id":"b","available_at":"2026-11-24T16:00:00Z"},
        ]
        result = build_as_of_snapshot(rows, "2026-11-24T12:00:00Z")
        self.assertEqual([x["record_id"] for x in result["records"]], ["a"])
        self.assertEqual(result["excluded_count"], 1)

    def test_missing_available_time_is_not_eligible(self):
        self.assertFalse(eligible_as_of({"event_time":"2026-11-24T09:00:00Z"}, "2026-11-24T12:00:00Z"))

    def test_missing_and_future_availability_are_separately_counted(self):
        result = build_as_of_snapshot([
            {"record_id":"missing"},
            {"record_id":"future","available_at":"2026-11-25T00:00:00Z"},
            {"record_id":"known","available_at":"2026-11-24T10:00:00Z"},
        ], "2026-11-24T12:00:00Z")
        self.assertEqual(result["missing_available_at_count"], 1)
        self.assertEqual(result["missing_available_at_record_indexes"], [0])
        self.assertEqual(result["future_excluded_count"], 1)
        self.assertEqual(result["excluded_count"], 2)

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            eligible_as_of({"available_at":"2026-11-24T09:00:00"}, "2026-11-24T12:00:00Z")

    def test_invalid_timestamp_type_and_format_rejected(self):
        for value in (123, "not-a-date", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                eligible_as_of({"available_at": value}, "2026-11-24T12:00:00Z")

    def test_non_object_records_rejected(self):
        with self.assertRaisesRegex(ValueError, "records must contain objects"):
            build_as_of_snapshot([None], "2026-11-24T12:00:00Z")

    def test_non_string_record_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "record_id"):
            build_as_of_snapshot([{"record_id": 7, "available_at":"2026-11-24T10:00:00Z"}],
                                 "2026-11-24T12:00:00Z")

    def test_offset_timestamps_sort_by_actual_utc_time(self):
        result = build_as_of_snapshot([
            {"record_id":"later","available_at":"2026-11-24T12:00:00+02:00"},
            {"record_id":"earlier","available_at":"2026-11-24T09:30:00Z"},
        ], "2026-11-24T12:00:00Z")
        self.assertEqual([row["record_id"] for row in result["records"]], ["earlier", "later"])

    def test_future_input_never_in_snapshot(self):
        result = build_as_of_snapshot([{"available_at":"2026-11-25T00:00:00Z"}], "2026-11-24T23:59:59Z")
        self.assertEqual(result["included_count"], 0)
        self.assertTrue(result["point_in_time_eligible"])


if __name__ == "__main__":
    unittest.main()
