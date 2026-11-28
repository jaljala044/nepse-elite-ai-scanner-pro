import unittest
from app.historical_pilot_source_contract import validate_historical_source_contract


class SourceContractTests(unittest.TestCase):
    def contract(self):
        return {"source_id":"SRC","publisher_id":"PUB","dataset_kind":"official_eod_ohlcv","endpoint_url":"https://data.example.test/eod","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45","review_status":"approved","approved_by_human":True,"reviewer_id":"reviewer-1","reviewed_at":"2025-02-01T09:00:00+05:45","authority_evidence_ref":"DOC-NEPSE-001","licence_reviewed":True,"access_policy_reviewed":True,"authentication_mode":"public","credential_reference":None,"page_parameter":"page","terminal_signal":"has_more_false","max_pages":50,"minimum_request_interval_seconds":1.0,"capture_id":"CAP-1"}
    def test_approved_contract_emits_safe_runner_spec_and_registry(self):
        out=validate_historical_source_contract(contract=self.contract(),decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"SOURCE_CONTRACT_APPROVED_FOR_CAPTURE")
        self.assertEqual(out["capture_spec"]["first_page"],1)
        self.assertFalse(out["credentials_embedded"])
        self.assertEqual(out["registry_record"]["publisher_id"],"PUB")
    def test_rejects_non_allowlisted_or_non_https_endpoint(self):
        c=self.contract(); c["endpoint_url"]="http://evil.example/eod"
        out=validate_historical_source_contract(contract=c,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CONTRACT_BLOCKED")
    def test_rejects_missing_human_approval_or_license_review(self):
        c=self.contract(); c["approved_by_human"]=False; c["licence_reviewed"]=False
        out=validate_historical_source_contract(contract=c,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CONTRACT_BLOCKED")
    def test_rejects_embedded_secret_values(self):
        c=self.contract(); c["api_key"]="do-not-commit"
        out=validate_historical_source_contract(contract=c,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertIn("secret_material_must_not_be_embedded_in_contract",str(out["errors"]))
    def test_rejects_credentials_in_endpoint_query(self):
        c=self.contract(); c["endpoint_url"]="https://data.example.test/eod?api_key=secret"
        out=validate_historical_source_contract(contract=c,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CONTRACT_BLOCKED")
        self.assertIn("endpoint_query_must_not_contain_credentials",str(out["errors"]))

    def test_rejects_url_userinfo_and_fragment(self):
        c=self.contract(); c["endpoint_url"]="https://user:password@data.example.test/eod#token"
        out=validate_historical_source_contract(contract=c,decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"CONTRACT_BLOCKED")

    def test_rejects_contract_review_after_decision_cutoff(self):
        out=validate_historical_source_contract(contract=self.contract(),decision_cutoff="2025-01-01T00:00:00+05:45")
        self.assertEqual(out["status"],"CONTRACT_BLOCKED")


if __name__=="__main__": unittest.main()
