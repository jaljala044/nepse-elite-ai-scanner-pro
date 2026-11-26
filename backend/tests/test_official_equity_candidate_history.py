import csv
import json
import tempfile
import unittest
from pathlib import Path

from audit_official_equity_candidate_history import reconcile


class OfficialEquityCandidateHistoryTests(unittest.TestCase):
    def _fixture(self, root):
        capture = {
            "source_id": "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME",
            "requested_start_date": "2026-11-19",
            "requested_end_date": "2026-11-24",
            "historical_security_identity_verified": False,
            "symbols": [
                {"symbol": "ABC", "status": "ROWS_RETURNED_REVIEW_ONLY",
                 "current_id_match": True, "current_security_list_id": "1",
                 "rows": [
                     {"business_date": d, "trades": t, "volume": q, "turnover": v}
                     for d,t,q,v in [
                         ("2026-11-19", 1, 10, 1000),
                         ("2026-11-20", 0, 0, 0),
                         ("2026-11-24", 2, 20, 2000),
                     ]
                 ]},
                {"symbol": "XYZ", "status": "ROWS_RETURNED_REVIEW_ONLY",
                 "current_id_match": True, "current_security_list_id": "2",
                 "rows": [
                     {"business_date": d, "trades": 0, "volume": 0, "turnover": 0}
                     for d in ("2026-11-19", "2026-11-20", "2026-11-24")
                 ]},
            ],
        }
        cap = root / "capture.json"
        cap.write_text(json.dumps(capture))
        floors = root / "floors"
        floors.mkdir()
        for day in ("2026-11-19", "2026-11-20", "2026-11-24"):
            for source in ("samir", "socrateai"):
                fields = ["date", "contract_no", "stock_symbol", "quantity", "amount"] if source == "samir" else ["date", "transaction", "symbol", "quantity", "amount"]
                with (floors / f"{source}-{day}.csv").open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    if day == "2026-11-19" or day == "2026-11-24":
                        writer.writerow({"date": day,
                            "contract_no" if source == "samir" else "transaction": "1",
                            "stock_symbol" if source == "samir" else "symbol": "ABC",
                            "quantity": 10 if day == "2026-11-19" else 20,
                            "amount": 1000 if day == "2026-11-19" else 2000})
        return cap, floors

    def test_positive_exact_and_zero_without_floor_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap, floors = self._fixture(Path(tmp))
            report = reconcile(cap, floors, expected_equity_count=2)
        statuses = report["dates"]["2026-11-20"]["socrateai"]["status_counts"]
        self.assertEqual(statuses, {"OFFICIAL_ZERO_ACTIVITY_NO_FLOORSHEET_ROW": 2})
        self.assertEqual(report["dates"]["2026-11-19"]["socrateai"]["status_counts"],
                         {"MATCH_EXACT": 1, "OFFICIAL_ZERO_ACTIVITY_NO_FLOORSHEET_ROW": 1})
        self.assertFalse(report["coverage_admission_allowed"])

    def test_mismatched_current_id_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap, floors = self._fixture(Path(tmp))
            data = json.loads(cap.read_text())
            data["symbols"][0]["current_id_match"] = False
            cap.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "capture status/current ID match"):
                reconcile(cap, floors)


if __name__ == "__main__":
    unittest.main()
