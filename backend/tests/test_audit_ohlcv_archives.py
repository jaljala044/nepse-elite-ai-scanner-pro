import unittest

from audit_ohlcv_archives import _repository_snapshot, audit_ohlcv_csv


class AuditOhlcvCsvTests(unittest.TestCase):
    def test_numeric_formatting_is_normalized_and_consecutive_repeat_is_flagged(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-02,10.00,11.0,9.00,10.50,100.0\n"
            "2024-01-03,10,11,9,10.5,100\n"
        ).encode()
        result = audit_ohlcv_csv(content, "03_stock_charts_ohlcv/TEST_OHLCV.csv")
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["unique_dates"], 2)
        self.assertEqual(result["invalid_rows"], [])
        self.assertEqual(result["repeated_adjacent_calendar_rows"], 1)
        self.assertEqual(result["observations"]["2024-01-02"][0]["volume"], "100")

    def test_duplicate_date_and_out_of_order_are_detected(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-03,10,11,9,10,100\n"
            "2024-01-03,10,11,9,10,100\n"
            "2024-01-02,10,11,9,10,100\n"
        ).encode()
        result = audit_ohlcv_csv(content, "TEST_OHLCV.csv")
        self.assertEqual(result["duplicate_dates"], [{"date": "2024-01-03", "count": 2}])
        self.assertEqual(result["out_of_order_transitions"], 1)

    def test_invalid_ohlc_and_non_integer_volume_are_rejected(self):
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-02,10,9,8,10,100\n"
            "2024-01-03,10,11,9,10,100.5\n"
        ).encode()
        result = audit_ohlcv_csv(content, "TEST_OHLCV.csv")
        self.assertEqual(result["valid_rows"], 0)
        self.assertEqual(len(result["invalid_rows"]), 2)

    def test_missing_required_column_fails_closed(self):
        content = b"Date,Open,High,Low,Close\n2024-01-02,10,11,9,10\n"
        with self.assertRaises(ValueError):
            audit_ohlcv_csv(content, "TEST_OHLCV.csv")


    def test_repository_snapshot_uses_exact_requested_commit_not_default_branch(self):
        class Response:
            status_code = 200
            def __init__(self, payload):
                self.payload = payload
            def json(self):
                return self.payload
            def raise_for_status(self):
                return None

        class Client:
            def __init__(self):
                self.urls = []
            def get(self, url):
                self.urls.append(url)
                if url.endswith("/repos/owner/repo"):
                    return Response({"default_branch": "main"})
                if url.endswith("/commits/" + "a" * 40):
                    return Response({"sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}}})
                if url.endswith("/git/trees/" + "b" * 40 + "?recursive=1"):
                    return Response({"truncated": False, "tree": []})
                raise AssertionError(f"unexpected URL: {url}")

        client = Client()
        commit, tree, files = _repository_snapshot(client, "owner/repo", "a" * 40)
        self.assertEqual(commit, "a" * 40)
        self.assertEqual(tree, "b" * 40)
        self.assertEqual(files, [])
        self.assertIn("/commits/" + "a" * 40, client.urls[1])

    def test_repository_snapshot_rejects_commit_ref_mismatch(self):
        class Response:
            status_code = 200
            def __init__(self, payload):
                self.payload = payload
            def json(self):
                return self.payload
            def raise_for_status(self):
                return None

        class Client:
            def get(self, url):
                if url.endswith("/repos/owner/repo"):
                    return Response({"default_branch": "main"})
                return Response({"sha": "c" * 40, "commit": {"tree": {"sha": "b" * 40}}})

        with self.assertRaisesRegex(RuntimeError, "requested pinned commit"):
            _repository_snapshot(Client(), "owner/repo", "a" * 40)

if __name__ == "__main__":
    unittest.main()
