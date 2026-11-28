import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detect_floorsheet_date_echo import inspect_payload

def payload(rows):
    return {"floorsheets":{"content":rows}}
def row(day, contract=None):
    return {"businessDate":day,"contractId":contract or day.replace("-","")+"000001"}

class FloorsheetEchoTests(unittest.TestCase):
    def test_matching_date_not_echo(self):
        r=inspect_payload(payload([row("2024-05-16")]),"2024-05-16")
        self.assertFalse(r["quarantine"])
    def test_all_rows_echoed_from_another_day(self):
        r=inspect_payload(payload([row("2026-11-26")]),"2024-05-16")
        self.assertIn("requested_date_mismatch",r["reasons"])
    def test_mixed_dates_quarantined(self):
        r=inspect_payload(payload([row("2024-05-16"),row("2026-11-26")]),"2024-05-16")
        self.assertIn("mixed_business_dates",r["reasons"])
    def test_contract_id_date_mismatch(self):
        r=inspect_payload(payload([row("2024-05-16","20261126000001")]),"2024-05-16")
        self.assertIn("contract_id_date_mismatch",r["reasons"])
    def test_missing_date_quarantined(self):
        r=inspect_payload(payload([{"contractId":"20240516000001"}]),"2024-05-16")
        self.assertIn("missing_or_invalid_business_date",r["reasons"])
    def test_empty_response_quarantined(self):
        self.assertTrue(inspect_payload(payload([]),"2024-05-16")["quarantine"])
    def test_never_promotes(self):
        self.assertFalse(inspect_payload(payload([row("2024-05-16")]),"2024-05-16")["promotion_allowed"])
if __name__=="__main__": unittest.main()
