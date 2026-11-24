import unittest

from crosscheck_index_history_yonepse import compare_rows, extract_yonepse_rows


class YonepseIndexCrosscheckTests(unittest.TestCase):
    def test_extracts_nepse_series_by_date_index(self):
        manifest = {"latestDate": "2026-11-03", "latestStatus": "provisional"}
        payloads = {
            "2026-11": {
                "month": "2026-11",
                "dates": ["2026-11-02", "2026-11-03"],
                "updatedAt": "2026-11-03T12:00:00+05:45",
                "series": {
                    "NEPSE": [
                        [0, 100, 99, 110, 95, 1000, 200, 50],
                        [1, 0, 101, 105, 98, 1100, 220, 60],
                    ]
                },
            }
        }
        rows = extract_yonepse_rows(manifest, payloads)
        self.assertEqual(rows["2026-11-02"]["row"]["close"], 100)
        self.assertEqual(rows["2026-11-02"]["finality_status"], "unmarked")
        self.assertEqual(rows["2026-11-03"]["finality_status"], "provisional")

    def test_rejects_date_index_out_of_range(self):
        manifest = {"latestDate": "2026-11-02"}
        payloads = {
            "2026-11": {
                "month": "2026-11",
                "dates": ["2026-11-02"],
                "series": {"NEPSE": [[1, 100, 99, 110, 95, 1000, 200, 50]]},
            }
        }
        with self.assertRaisesRegex(ValueError, "invalid dateIndex"):
            extract_yonepse_rows(manifest, payloads)

    def test_rejects_duplicate_yonepse_date(self):
        manifest = {"latestDate": "2026-11-02"}
        payloads = {
            "2026-11": {
                "month": "2026-11",
                "dates": ["2026-11-02"],
                "series": {"NEPSE": [
                    [0, 100, 99, 110, 95, 1000, 200, 50],
                    [0, 101, 99, 110, 95, 1000, 200, 50],
                ]},
            }
        }
        with self.assertRaisesRegex(ValueError, "duplicate YONEPSE"):
            extract_yonepse_rows(manifest, payloads)

    def test_compares_close_and_turnover_mapping_without_autocorrection(self):
        socrateai = [{"close": "100", "open": "99", "high": "110", "low": "95", "volume": "1000"}]
        yonepse = {
            "row": {"close": 100, "open": 99, "high": 111, "low": 95, "turnover": 1001},
            "finality_status": "unmarked",
        }
        result = compare_rows(socrateai, yonepse)
        self.assertEqual(result["status"], "numeric_differences")
        self.assertEqual(result["differences"]["high"]["absolute_difference"], "1")
        self.assertEqual(result["differences"]["turnover_vs_socrateai_volume"]["absolute_difference"], "1")

    def test_provisional_latest_row_is_not_compared(self):
        socrateai = [{"close": "100", "open": "99", "high": "110", "low": "95", "volume": "1000"}]
        yonepse = {
            "row": {"close": 0, "open": 101, "high": 105, "low": 98, "turnover": 1100},
            "finality_status": "provisional",
        }
        result = compare_rows(socrateai, yonepse)
        self.assertEqual(result["status"], "yonepse_latest_provisional")
        self.assertNotIn("differences", result)


if __name__ == "__main__":
    unittest.main()
