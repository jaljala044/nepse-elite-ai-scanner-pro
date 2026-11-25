import unittest
from datetime import date
from app.hf_dataset_collector import (
    _extract_date, _is_candidate, _item_path, _matches_date, _safe_relative_path,
    _resolve_revision,
)

class HuggingFaceCollectorTests(unittest.TestCase):
    def test_mutable_hub_ref_resolves_to_immutable_commit(self):
        class Response:
            def raise_for_status(self):
                pass
            def json(self):
                return {"sha": "a" * 40}
        class Client:
            def get(self, url):
                self.url = url
                return Response()
        client = Client()
        self.assertEqual(_resolve_revision(client, "owner/dataset", "main"), "a" * 40)
        self.assertIn("/revision/main", client.url)

    def test_revision_resolution_rejects_non_commit_sha(self):
        class Response:
            def raise_for_status(self):
                pass
            def json(self):
                return {"sha": "main"}
        class Client:
            def get(self, url):
                return Response()
        with self.assertRaisesRegex(ValueError, "immutable commit SHA"):
            _resolve_revision(Client(), "owner/dataset", "main")

    def test_urekmazino_floorsheet_and_indices_paths(self):
        self.assertTrue(_is_candidate("floorsheet_indices_2024", "floorsheet/2024-01-02.csv"))
        self.assertTrue(_is_candidate("floorsheet_indices_2024", "indices/2024-01-02.csv"))
        self.assertFalse(_is_candidate("floorsheet_indices_2024", "README.md"))

    def test_ankit_parquet_table_paths(self):
        self.assertTrue(_is_candidate("market_data_2026", "floorsheet/date=2026-11-20/data.parquet"))
        self.assertTrue(_is_candidate("market_data_2026", "eod_history_ext/history.parquet"))
        self.assertFalse(_is_candidate("market_data_2026", "notebooks/analysis.ipynb"))

    def test_extract_date_variants(self):
        self.assertEqual(_extract_date("floorsheet/2024-01-02.csv"), date(2024, 1, 2))
        self.assertEqual(_extract_date("floorsheet/date=2026-11-20/data.parquet"), date(2026, 11, 20))
        self.assertEqual(_extract_date("prices/2024_01_02.csv"), date(2024, 1, 2))
        self.assertEqual(_extract_date("indices/1997-07-20.csv.gz"), date(1997, 7, 20))

    def test_hub_relative_file_names_are_joined_to_folder(self):
        self.assertEqual(
            _item_path({"path": "2024-01-02.csv"}, "floorsheet/"),
            "floorsheet/2024-01-02.csv",
        )
        self.assertEqual(
            _item_path({"path": "floorsheet/2024-01-02.csv"}, "floorsheet/"),
            "floorsheet/2024-01-02.csv",
        )
        self.assertEqual(
            _item_path({"rfilename": "2024-01-02.csv"}, "indices/"),
            "indices/2024-01-02.csv",
        )

    def test_date_filter(self):
        self.assertTrue(_matches_date("floorsheet/2024-06-01.csv", date(2024, 1, 1), date(2024, 12, 31)))
        self.assertFalse(_matches_date("floorsheet/2025-06-01.csv", date(2024, 1, 1), date(2024, 12, 31)))
        self.assertFalse(_matches_date("tables/no-date.parquet", date(2024, 1, 1), None))

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            _safe_relative_path("../../secrets.txt")

if __name__ == "__main__":
    unittest.main()
