import csv
import tempfile
import unittest
from pathlib import Path

from adjudicate_issue5_gaps import adjudicate

GAP_FIELDS = ["repository", "symbol", "trade_date", "gap_status"]
EVIDENCE_FIELDS = [
    "symbol", "trade_date", "evidence_kind", "authority", "source_id",
    "source_url", "evidence_sha256", "captured_at", "available_at",
    "effective_from", "effective_to", "rights_status",
]
STATUS = "UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE"
SMC = "jaljala044/nepse-smc-data"


class Issue5EvidenceAdjudicationTests(unittest.TestCase):
    def write(self, path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def gap(self, symbol="ABC", day="2026-01-02"):
        return {"repository": SMC, "symbol": symbol, "trade_date": day, "gap_status": STATUS}

    def evidence(self, kind="official_security_no_trade", **changes):
        row = {
            "symbol": "ABC", "trade_date": "2026-01-02",
            "evidence_kind": kind, "authority": "NEPSE",
            "source_id": "DOC-1", "source_url": "https://example.invalid/evidence",
            "evidence_sha256": "a" * 64,
            "captured_at": "2026-01-02T16:00:00+05:45",
            "available_at": "2026-01-02T16:05:00+05:45",
            "effective_from": "2026-01-02", "effective_to": "2026-01-02",
            "rights_status": "approved",
        }
        row.update(changes)
        return row

    def run_case(self, evidence_rows, cutoff="2026-01-03T00:00:00+05:45"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [self.gap()])
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, evidence_rows)
            return adjudicate(gaps, evidence, decision_cutoff=cutoff)

    def test_duplicate_csv_headers_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = root / "gaps.csv"
            gaps.write_text(
                "repository,repository,symbol,trade_date,gap_status\n"
                f"{SMC},{SMC},ABC,2026-01-02,{STATUS}\n",
                encoding="utf-8",
            )
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "duplicate CSV headers"):
                adjudicate(gaps, evidence)

    def test_whitespace_only_csv_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = root / "gaps.csv"
            gaps.write_text(
                "repository,symbol,trade_date,gap_status,   \\n"
                f"{SMC},ABC,2026-01-02,{STATUS},ignored\\n",
                encoding="utf-8",
            )
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "CSV headers must be nonblank"):
                adjudicate(gaps, evidence)

    def test_blank_gap_repository_is_rejected(self):
        report = self.run_case([])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [{
                "repository": "", "symbol": "ABC", "trade_date": "2026-01-02",
                "gap_status": STATUS,
            }])
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "invalid gap identity"):
                adjudicate(gaps, evidence)

    def test_extra_csv_columns_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = root / "gaps.csv"
            gaps.write_text(
                "repository,symbol,trade_date,gap_status\n"
                f"{SMC},ABC,2026-01-02,{STATUS},EXTRA\n",
                encoding="utf-8",
            )
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "malformed CSV row"):
                adjudicate(gaps, evidence)

    def test_unknown_gap_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [{
                "repository": "untrusted/mirror", "symbol": "ABC",
                "trade_date": "2026-01-02", "gap_status": STATUS,
            }])
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "invalid gap identity"):
                adjudicate(gaps, evidence)

    def test_explicit_official_no_trade_is_narrowly_classified(self):
        report = self.run_case([self.evidence()])
        row = report["results"][0]
        self.assertEqual(row["disposition"], "verified_no_trade")
        self.assertTrue(row["point_in_time_eligible_at_cutoff"])
        self.assertFalse(row["canonical_promotion_allowed"])

    def test_official_suspension_and_not_listed_are_distinct(self):
        suspended = self.run_case([self.evidence("official_suspension")])
        not_listed = self.run_case([self.evidence("official_not_listed")])
        self.assertEqual(suspended["results"][0]["disposition"], "verified_suspended")
        self.assertEqual(not_listed["results"][0]["disposition"], "verified_not_listed")

    def test_empty_floorsheet_is_not_no_trade_but_positive_execution_is_conflict(self):
        report = self.run_case([self.evidence("floorsheet_execution")])
        self.assertEqual(report["results"][0]["disposition"], "execution_evidence_without_source_bar")
        self.assertNotEqual(report["results"][0]["disposition"], "verified_no_trade")

    def test_counterpart_bar_does_not_become_authoritative(self):
        report = self.run_case([self.evidence("counterpart_valid_bar")])
        self.assertEqual(report["results"][0]["disposition"], "counterpart_bar_present_not_authoritative")

    def test_contradictory_evidence_stays_quarantined(self):
        report = self.run_case([
            self.evidence("official_security_no_trade"),
            self.evidence("floorsheet_execution", source_id="DOC-2", evidence_sha256="b" * 64),
        ])
        self.assertEqual(report["results"][0]["disposition"], "conflicting_evidence_quarantined")

    def test_late_evidence_not_point_in_time_eligible(self):
        report = self.run_case([self.evidence(available_at="2026-01-04T09:00:00+05:45")])
        self.assertFalse(report["results"][0]["point_in_time_eligible_at_cutoff"])

    def test_wrong_authority_and_rights_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires NEPSE/SEBON"):
            self.run_case([self.evidence(authority="THIRD_PARTY")])
        with self.assertRaisesRegex(ValueError, "rights not approved"):
            self.run_case([self.evidence(rights_status="unknown")])

    def test_orphan_evidence_and_non_https_source_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [self.gap()])
            orphan = self.evidence(symbol="XYZ")
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [orphan])
            with self.assertRaisesRegex(ValueError, "orphan evidence"):
                adjudicate(gaps, evidence)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [self.gap()])
            bad = self.evidence(source_url="http://example.invalid/evidence")
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [bad])
            with self.assertRaisesRegex(ValueError, "must use HTTPS"):
                adjudicate(gaps, evidence)

    def test_effective_range_must_cover_trade_date(self):
        with self.assertRaisesRegex(ValueError, "does not cover"):
            self.run_case([self.evidence(effective_from="2026-01-03", effective_to="2026-01-04")])

    def test_duplicate_gap_and_evidence_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [self.gap(), self.gap()])
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [self.evidence()])
            with self.assertRaisesRegex(ValueError, "duplicate gap source key"):
                adjudicate(gaps, evidence)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gaps = self.write(root / "gaps.csv", GAP_FIELDS, [self.gap()])
            ev = self.evidence()
            evidence = self.write(root / "evidence.csv", EVIDENCE_FIELDS, [ev, ev])
            with self.assertRaisesRegex(ValueError, "duplicate evidence identity"):
                adjudicate(gaps, evidence)


if __name__ == "__main__":
    unittest.main()
