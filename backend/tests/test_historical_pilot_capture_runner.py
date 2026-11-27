import unittest
from app.historical_pilot_capture_runner import capture_registered_source_pages


class CaptureRunnerTests(unittest.TestCase):
    def spec(self):
        return {"review_status":"approved","source_id":"SRC","publisher_id":"PUB","endpoint_url":"https://data.example.test/history","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"page_parameter":"page","first_page":1,"capture_id":"CAP","window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45"}
    def response(self,body,more,page):
        return {"status_code":200,"final_url":f"https://data.example.test/history?page={page}","content_type":"text/csv","body":body,"has_more":more,"available_at":"2025-02-01T10:00:00+05:45"}
    def test_paginates_hashes_and_stops_only_on_explicit_terminal_page(self):
        calls=[]
        def fetch(url):
            calls.append(url); return self.response(f"page-{len(calls)}".encode(),len(calls)<2,len(calls))
        out=capture_registered_source_pages(source_spec=self.spec(),fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURED_PENDING_MANIFEST_VALIDATION"); self.assertEqual(out["raw_payload_count"],2); self.assertTrue(out["manifest"]["capture_complete"])
    def test_redirect_outside_allowlist_blocks(self):
        def fetch(url):
            r=self.response(b"data",False,1); r["final_url"]="https://evil.example/history"; return r
        out=capture_registered_source_pages(source_spec=self.spec(),fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURE_INCOMPLETE"); self.assertIn("redirect_outside_registered_host",str(out["errors"]))
    def test_future_available_page_blocks(self):
        def fetch(url):
            r=self.response(b"data",False,1); r["available_at"]="2025-02-03T00:00:00+05:45"; return r
        out=capture_registered_source_pages(source_spec=self.spec(),fetch_page=fetch,captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURE_INCOMPLETE")
    def test_unapproved_source_never_calls_transport(self):
        called=[]; spec=self.spec(); spec["review_status"]="pending"
        out=capture_registered_source_pages(source_spec=spec,fetch_page=lambda url:called.append(url),captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CAPTURE_BLOCKED"); self.assertEqual(called,[])


if __name__=="__main__": unittest.main()
