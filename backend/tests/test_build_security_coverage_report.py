import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from build_security_coverage_report import build_security_coverage_report


class SecurityCoverageReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.universe = self.root / "universe.csv"
        self.calendar = self.root / "calendar.csv"
        self.data = self.root / "data.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, path, fields, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def write_inputs(self):
        self.write_csv(self.universe,
            ["security_id", "symbol", "instrument_type", "valid_from", "valid_to", "target_in_scope"],
            [
                {"security_id":"S1","symbol":"AAA","instrument_type":"equity","valid_from":"2026-01-01","valid_to":"","target_in_scope":"true"},
                {"security_id":"S2","symbol":"FUND1","instrument_type":"mutual_fund","valid_from":"2026-01-02","valid_to":"","target_in_scope":"true"},
            ])
        cal_fields = ["date","status","source_id","evidence_uri","raw_evidence_sha256",
                      "published_at","retrieved_at_utc","verified_at_utc","scope","notes"]
        cal_rows = []
        for day, status in [("2026-01-02","verified_open"),("2026-01-03","verified_closed"),
                            ("2026-01-04","verified_exceptional_open")]:
            cal_rows.append({"date":day,"status":status,"source_id":"NEPSE-NOTICE-1",
                "evidence_uri":"https://example.invalid/notice","raw_evidence_sha256":"a"*64,
                "published_at":"2026-01-01T10:00:00+05:45","retrieved_at_utc":"2026-01-05T00:00:00Z",
                "verified_at_utc":"2026-01-05T00:00:00Z","scope":"all securities","notes":"fixture"})
        self.write_csv(self.calendar, cal_fields, cal_rows)
        self.write_csv(self.data, ["source_id","symbol","date"], [
            {"source_id":"publisher-a","symbol":"AAA","date":"2026-01-02"},
            {"source_id":"publisher-a","symbol":"AAA","date":"2026-01-03"},
            {"source_id":"publisher-a","symbol":"FUND1","date":"2026-01-04"},
        ])

    def test_coverage_counts_only_explicit_open_sessions(self):
        self.write_inputs()
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        self.assertEqual(report["target_equity_count"], 1)
        self.assertEqual(report["target_mutual_fund_count"], 1)
        self.assertFalse(report["target_universe_counts_match"])
        self.assertEqual(report["expected_target_equity_count"], 281)
        self.assertEqual(report["expected_target_mutual_fund_count"], 47)
        self.assertEqual(report["verified_open_session_count"], 2)
        aaa = next(row for row in report["per_security"] if row["symbol"] == "AAA")
        self.assertEqual(aaa["expected_verified_sessions"], 2)
        self.assertEqual(aaa["observed_expected_sessions"], 1)
        self.assertEqual(aaa["missing_sessions"], ["2026-01-04"])
        self.assertEqual(report["source_specific_reports"][0]["unexpected_observations"][0]["reason"], "observation_on_verified_closed_date")
        self.assertFalse(report["promotion_allowed"])

    def test_unknown_calendar_date_is_not_added_to_denominator(self):
        self.write_inputs()
        with self.data.open("a", encoding="utf-8") as stream:
            stream.write("publisher-a,AAA,2026-01-05\n")
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        self.assertIn("2026-01-05", report["source_specific_reports"][0]["unverified_calendar_observation_dates"])
        self.assertEqual(report["verified_open_session_count"], 2)

    def test_duplicate_source_rows_do_not_inflate_coverage(self):
        self.write_inputs()
        with self.data.open("a", encoding="utf-8") as stream:
            stream.write("publisher-a,AAA,2026-01-02\n")
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        aaa = next(row for row in report["per_security"] if row["symbol"] == "AAA")
        self.assertEqual(aaa["observed_expected_sessions"], 0)
        self.assertEqual(aaa["duplicate_session_rows"], ["2026-01-02"])

    def test_publishers_are_reported_separately_not_combined(self):
        self.write_inputs()
        with self.data.open("a", encoding="utf-8") as stream:
            stream.write("publisher-b,AAA,2026-01-02\n")
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        self.assertEqual(report["source_count"], 2)
        self.assertIsNone(report["aggregate_coverage_ratio"])
        self.assertEqual([x["source_id"] for x in report["source_specific_reports"]],
                         ["publisher-a", "publisher-b"])
        self.assertEqual(report["source_specific_reports"][1]["coverage_ratio"], 0.25)

    def test_unknown_symbols_are_reported_not_silently_dropped(self):
        self.write_inputs()
        with self.data.open("a", encoding="utf-8") as stream:
            stream.write("publisher-a,NOT_IN_UNIVERSE,2026-01-02\n")
            stream.write("publisher-a,NOT_IN_UNIVERSE,2026-01-02\n")
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        source = report["source_specific_reports"][0]
        self.assertEqual(source["unknown_symbol_observation_count"], 2)
        self.assertEqual(source["unknown_symbol_observations"], [{
            "symbol":"NOT_IN_UNIVERSE","date":"2026-01-02","row_count":2,
            "reason":"symbol_not_in_target_universe_snapshot"
        }])

    def test_excluded_debenture_can_remain_in_reference_universe(self):
        self.write_inputs()
        with self.universe.open("a", encoding="utf-8") as stream:
            stream.write("D1,DEBT1,non_convertible_debenture,2020-01-01,,false\n")
        report = build_security_coverage_report(
            self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))
        self.assertEqual(report["target_security_count"], 2)

    def test_debenture_cannot_be_marked_in_target_scope(self):
        self.write_inputs()
        with self.universe.open("a", encoding="utf-8") as stream:
            stream.write("D1,DEBT1,non_convertible_debenture,2020-01-01,,true\n")
        with self.assertRaisesRegex(ValueError, "only equity and mutual_fund"):
            build_security_coverage_report(
                self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))

    def test_unknown_instrument_type_fails_closed(self):
        self.write_inputs()
        rows = list(csv.DictReader(self.universe.open(encoding="utf-8")))
        rows[0]["instrument_type"] = "ticker_guess"
        self.write_csv(self.universe,
            ["security_id", "symbol", "instrument_type", "valid_from", "valid_to", "target_in_scope"], rows)
        with self.assertRaisesRegex(ValueError, "unsupported target instrument_type"):
            build_security_coverage_report(
                self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))

    def test_overlapping_symbol_in_universe_fails_closed(self):
        self.write_inputs()
        rows = list(csv.DictReader(self.universe.open(encoding="utf-8")))
        rows.append({"security_id":"S3","symbol":"AAA","instrument_type":"equity",
                     "valid_from":"2026-01-03","valid_to":"","target_in_scope":"true"})
        self.write_csv(self.universe,
            ["security_id", "symbol", "instrument_type", "valid_from", "valid_to", "target_in_scope"], rows)
        with self.assertRaisesRegex(ValueError, "overlapping in-scope symbol"):
            build_security_coverage_report(
                self.universe, self.calendar, [self.data], date(2026,1,1), date(2026,1,5))


if __name__ == "__main__":
    unittest.main()
