import unittest

from probe_nepse_public_notices import summarize_notice_payload


class PublicNoticeProbeTests(unittest.TestCase):
    def test_summarizes_keyword_candidates_without_dropping_payload_fields(self):
        payload = {
            "content": [
                {"id": 1, "title": "Market holiday notice", "publishedDate": "2026-11-08", "document": "x.pdf"},
                {"id": 2, "title": "Company disclosure", "publishedDate": "2026-11-09"},
            ]
        }
        result = summarize_notice_payload(payload)
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["keyword_candidate_count"], 1)
        self.assertEqual(result["keyword_candidates"][0]["record"]["document"], "x.pdf")

    def test_supports_plain_list_payload(self):
        result = summarize_notice_payload([{"subject": "Trading suspended"}, {"subject": "AGM"}])
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["keyword_candidate_count"], 1)

    def test_preserves_unrecognized_dict_as_single_record(self):
        payload = {"unexpected": "holiday field", "opaque": 123}
        result = summarize_notice_payload(payload)
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["keyword_candidate_count"], 1)
        self.assertEqual(result["keyword_candidates"][0]["record"], payload)


if __name__ == "__main__":
    unittest.main()
