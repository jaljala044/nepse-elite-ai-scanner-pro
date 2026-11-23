import unittest
from inventory_hf_datasets import summarize_dataset, summarize_inventory

class HuggingFaceInventorySummaryTests(unittest.TestCase):
    def test_summary_counts_dates_and_sizes(self):
        info = {
            "repo": "owner/example", "revision": "main", "notes": "test",
            "records": [
                {"path": "floorsheet/2024-01-02.csv.gz", "size": 100, "oid": "a"},
                {"path": "floorsheet/2024-01-03.csv.gz", "size": 200, "oid": "b"},
                {"path": "indices/2024-01-02.csv.gz", "size": 50, "oid": "c"},
                {"path": "README.md", "size": 25, "oid": "d"},
            ],
        }
        result = summarize_dataset("test", info)
        self.assertEqual(result["files_found"], 4)
        self.assertEqual(result["estimated_total_bytes"], 375)
        self.assertEqual(result["first_path_date"], "2024-01-02")
        self.assertEqual(result["last_path_date"], "2024-01-03")
        self.assertEqual(result["dated_files"], 3)
        self.assertEqual(result["unpartitioned_files"], 1)
        self.assertEqual(result["files_by_extension"][".csv.gz"], 3)

    def test_gap_report_is_review_only(self):
        info = {"repo":"x/y","revision":"main","records":[
            {"path":"floorsheet/2024-01-02.csv.gz","size":1},
            {"path":"floorsheet/2024-02-02.csv.gz","size":1},
        ]}
        result = summarize_dataset("test", info)
        self.assertEqual(result["largest_calendar_gaps_over_7_days"][0]["calendar_days_apart"],31)
        self.assertIn("not automatically missing",result["largest_calendar_gaps_over_7_days"][0]["note"])

    def test_inventory_summary_keeps_no_download_mode(self):
        summary=summarize_inventory({"manifest_path":"manifest.json","datasets":{}})
        self.assertEqual(summary["mode"],"inventory_only_no_bulk_download")
        self.assertEqual(summary["dataset_count"],0)

if __name__=="__main__":
    unittest.main()
