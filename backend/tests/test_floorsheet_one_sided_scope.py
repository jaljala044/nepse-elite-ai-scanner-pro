import csv
import json
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_one_sided_scope import classify_one_sided_contracts


class OneSidedScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.crosswalk = self.root / "crosswalk.csv"
        self.candidates = self.root / "candidates.csv"
        self.snapshot = self.root / "snapshot.csv"
        self._write(self.crosswalk, [
            {"symbol": "EQA", "security_id": "101", "security_name": "Equity A",
             "snapshot_date": "2026-11-25", "active_status": "A",
             "crosswalk_status": "snapshot_id_match_active_status_A"},
        ])
        self._write(self.candidates, [
            {"symbol": "MF1", "instrument_class_from_rendered_list": "Mutual Fund",
             "official_snapshot_id": "201", "official_snapshot_status": "A"},
            {"symbol": "EQ2", "instrument_class_from_rendered_list": "Equity",
             "official_snapshot_id": "102", "official_snapshot_status": "A"},
        ])
        self._write(self.snapshot, [
            {"symbol": "EQA", "security_id": "101", "security_name": "Equity A",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "MF1", "security_id": "201", "security_name": "Mutual Fund One",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "PROM", "security_id": "301", "security_name": "Company Promoter Share",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "DEB", "security_id": "401", "security_name": "Company Debenture 2088",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "BOND", "security_id": "501", "security_name": "Company Bond",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "ODD", "security_id": "601", "security_name": "Other Instrument",
             "active_status": "A", "snapshot_date": "2026-11-25"},
            {"symbol": "BONDED", "security_id": "701", "security_name": "Company Bonded Note",
             "active_status": "A", "snapshot_date": "2026-11-25"},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _audit(self):
        def record(day, contract, symbol):
            return {"trade_date": day, "contract_id": contract, "symbol": symbol,
                    "quantity": "10", "rate": "100", "amount": "1000",
                    "buyer_broker_code": "1", "seller_broker_code": "2"}
        return {
            "date_reports": {
                "2026-11-19": {"audit": {"comparison": {
                    "comparison_status": "compared_review_only",
                    "conflicting_shared_contract_count": 0,
                    "samir_only_contract_keys": [],
                    "right_only_contracts": [
                        record("2026-11-19", "1", "EQA"),
                        record("2026-11-19", "2", "MF1"),
                        record("2026-11-19", "3", "PROM"),
                        record("2026-11-19", "4", "DEB"),
                    ],
                }}},
                "2026-11-20": {"audit": {"comparison": {
                    "comparison_status": "compared_review_only",
                    "conflicting_shared_contract_count": 0,
                    "samir_only_contract_keys": [],
                    "right_only_contracts": [
                        record("2026-11-20", "5", "BOND"),
                        record("2026-11-20", "6", "EQ2"),
                        record("2026-11-20", "7", "ODD"),
                        record("2026-11-20", "8", "MISSING"),
                    ],
                }}},
            }
        }

    def test_classifies_dated_instrument_scope_and_preserves_unknowns(self):
        report = classify_one_sided_contracts(
            self._audit(), self.crosswalk, self.candidates, self.snapshot,
            "2026-11-25",
        )
        self.assertEqual(report["one_sided_contract_count"], 8)
        self.assertEqual(report["scope_class_counts"], {
            "EQUITY_CANDIDATE_NOT_IN_CROSSWALK": 1,
            "IN_SCOPE_EQUITY_CANDIDATE": 1,
            "OUT_OF_SCOPE_BOND": 1,
            "OUT_OF_SCOPE_DEBENTURE": 1,
            "OUT_OF_SCOPE_MUTUAL_FUND": 1,
            "OUT_OF_SCOPE_PROMOTER_SHARE": 1,
            "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH": 1,
            "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY": 1,
        })
        self.assertFalse(report["coverage_admission_allowed"])
        self.assertFalse(report["canonical_promotion_allowed"])
        self.assertEqual(report["date_summaries"]["2026-11-19"]["one_sided_contract_count"], 4)
        self.assertEqual(report["scope_classification_basis"],
                         "current_snapshot_hint_only_not_historical_effective_dated_identity")
        self.assertTrue(all(not row["historical_security_identity_verified"]
                            for row in report["one_sided_contracts"]))

    def test_bond_name_uses_word_boundaries(self):
        audit = self._audit()
        audit["date_reports"]["2026-11-20"]["audit"]["comparison"]["right_only_contracts"] = [
            {"trade_date": "2026-11-20", "contract_id": "B1", "symbol": "BOND",
             "quantity": "10", "rate": "100", "amount": "1000"}
        ]
        report = classify_one_sided_contracts(
            audit, self.crosswalk, self.candidates, self.snapshot, "2026-11-25"
        )
        self.assertEqual(report["one_sided_contracts"][0]["scope_class"], "OUT_OF_SCOPE_BOND")

    def test_bond_substring_without_word_boundary_is_not_a_bond_classification(self):
        audit = self._audit()
        audit["date_reports"]["2026-11-20"]["audit"]["comparison"]["right_only_contracts"] = [
            {"trade_date": "2026-11-20", "contract_id": "B2", "symbol": "BONDED",
             "quantity": "10", "rate": "100", "amount": "1000"}
        ]
        report = classify_one_sided_contracts(
            audit, self.crosswalk, self.candidates, self.snapshot, "2026-11-25"
        )
        self.assertEqual(report["one_sided_contracts"][0]["scope_class"],
                         "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY")

    def test_snapshot_rows_must_match_expected_snapshot_date(self):
        rows = self._read(self.snapshot)
        rows[0]["snapshot_date"] = "2026-11-24"
        self._write(self.snapshot, rows)
        with self.assertRaisesRegex(ValueError, "not dated 2026-11-25"):
            classify_one_sided_contracts(
                self._audit(), self.crosswalk, self.candidates, self.snapshot,
                "2026-11-25",
            )

    def test_candidate_snapshot_id_conflict_fails_closed(self):
        rows = self._read(self.candidates)
        rows[0]["official_snapshot_id"] = "999"
        self._write(self.candidates, rows)
        with self.assertRaisesRegex(ValueError, "target candidate/security snapshot ID conflict"):
            classify_one_sided_contracts(
                self._audit(), self.crosswalk, self.candidates, self.snapshot,
                "2026-11-25",
            )

    def test_crosswalk_snapshot_identity_mismatch_fails_closed(self):
        rows = self._read(self.crosswalk)
        rows[0]["security_id"] = "999"
        self._write(self.crosswalk, rows)
        with self.assertRaisesRegex(ValueError, "crosswalk/security snapshot conflict"):
            classify_one_sided_contracts(
                self._audit(), self.crosswalk, self.candidates, self.snapshot,
                "2026-11-25",
            )

    @staticmethod
    def _read(path):
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
