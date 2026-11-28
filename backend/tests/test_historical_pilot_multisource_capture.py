import unittest
from app.historical_pilot_source_contract import validate_historical_source_contract
from app.historical_pilot_multisource_capture import capture_required_historical_datasets


def make_contract(kind,capture_id):
    return {"source_id":"SRC-"+kind,"publisher_id":"PUB-"+kind,"dataset_kind":kind,"endpoint_url":"https://data.example.test/feed","allowed_hosts":["data.example.test"],"allowed_content_types":["text/csv"],"window_start":"2025-01-01T00:00:00+05:45","window_end":"2025-01-31T23:59:00+05:45","review_status":"approved","approved_by_human":True,"reviewer_id":"reviewer","reviewed_at":"2025-02-01T09:00:00+05:45","authority_evidence_ref":"DOC-"+kind,"licence_reviewed":True,"access_policy_reviewed":True,"authentication_mode":"public","page_parameter":"page","terminal_signal":"has_more_false","max_pages":1,"minimum_request_interval_seconds":1.0,"capture_id":capture_id}


class MultiSourceCaptureTests(unittest.TestCase):
    def test_two_required_dataset_types_are_captured_and_validated(self):
        reports={}; transports={}
        for kind in ("official_eod_ohlcv","official_market_calendar"):
            key=kind
            reports[key]=validate_historical_source_contract(contract=make_contract(kind,"CAP-"+kind),decision_cutoff="2025-02-02T00:00:00+05:45")
            transports[key]=lambda url:{"status_code":200,"final_url":url,"content_type":"text/csv","body":b"field,value\nA,1\n","has_more":False,"available_at":"2025-02-01T10:00:00+05:45"}
        out=capture_required_historical_datasets(source_contract_reports=reports,transports=transports,required_dataset_kinds=["official_eod_ohlcv","official_market_calendar"],captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"REQUIRED_DATASET_CAPTURE_SET_VALIDATED",msg=repr(out["errors"]))
        self.assertFalse(out["backtest_admission_allowed"])

    def test_duplicate_required_dataset_contracts_block_before_transport(self):
        reports = {
            "eod-a": validate_historical_source_contract(
                contract=make_contract("official_eod_ohlcv","CAP-EOD-A"),
                decision_cutoff="2025-02-02T00:00:00+05:45"),
            "eod-b": validate_historical_source_contract(
                contract=dict(make_contract("official_eod_ohlcv","CAP-EOD-B"),source_id="SRC-EOD-B"),
                decision_cutoff="2025-02-02T00:00:00+05:45"),
        }
        calls = []
        transports = {
            key: (lambda url: calls.append(url)) for key in reports
        }
        out = capture_required_historical_datasets(
            source_contract_reports=reports, transports=transports,
            required_dataset_kinds=["official_eod_ohlcv","official_market_calendar"],
            captured_at="2025-02-01T11:00:00+05:45",
            decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(calls,[])
        self.assertEqual(out["errors"][0]["reason"],"required_capture_contract_cardinality_invalid")
        self.assertEqual(out["missing_dataset_kinds"],["official_market_calendar"])
        self.assertIn("official_eod_ohlcv",out["errors"][0]["duplicate_contract_kinds"])

    def test_invalid_dataset_kind_list_is_rejected_cleanly(self):
        with self.assertRaisesRegex(ValueError,"required_dataset_kinds must be a nonempty unique list"):
            capture_required_historical_datasets(
                source_contract_reports={},transports={},
                required_dataset_kinds=[["official_eod_ohlcv"]],
                captured_at="2025-02-01T11:00:00+05:45",
                decision_cutoff="2025-02-02T00:00:00+05:45")

    def test_missing_dataset_or_transport_blocks_set(self):
        report=validate_historical_source_contract(contract=make_contract("official_eod_ohlcv","CAP-1"),decision_cutoff="2025-02-02T00:00:00+05:45")
        out=capture_required_historical_datasets(source_contract_reports={"eod":report},transports={},required_dataset_kinds=["official_eod_ohlcv","official_market_calendar"],captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["missing_dataset_kinds"],["official_eod_ohlcv","official_market_calendar"])
        self.assertEqual(out["errors"][0]["missing_contract_kinds"],["official_market_calendar"])
        self.assertEqual(out["errors"][0]["missing_transport_kinds"],["official_eod_ohlcv"])
        self.assertEqual(out["captured_dataset_kinds"],[])
        self.assertFalse(out["all_required_capture_packages_validated"])
        self.assertFalse(out["panel_assembly_allowed"])

    def test_missing_transport_with_complete_contract_inventory_blocks(self):
        kind = "official_eod_ohlcv"
        report = validate_historical_source_contract(contract=make_contract(kind,"CAP-1"),decision_cutoff="2025-02-02T00:00:00+05:45")
        out = capture_required_historical_datasets(source_contract_reports={"eod":report},transports={},required_dataset_kinds=[kind],captured_at="2025-02-01T11:00:00+05:45",decision_cutoff="2025-02-02T00:00:00+05:45")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["missing_dataset_kinds"],[kind])
        self.assertEqual(out["capture_results"],{})
        self.assertEqual(out["errors"][0]["missing_contract_kinds"],[])
        self.assertEqual(out["errors"][0]["missing_transport_kinds"],[kind])
        self.assertEqual(out["captured_dataset_kinds"],[])
        self.assertFalse(out["panel_assembly_allowed"])
        self.assertFalse(out["backtest_admission_allowed"])


if __name__=="__main__":unittest.main()
