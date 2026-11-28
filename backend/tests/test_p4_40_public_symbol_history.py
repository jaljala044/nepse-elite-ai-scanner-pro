import json
import unittest
from pathlib import Path
from app.p4_40_public_symbol_history import parse_public_symbol_history

DATA=Path(__file__).parents[2]/"data/evidence/benh/2026-11-28/sharesansar_scraper_benh_history.json"
class PublicSymbolHistoryTests(unittest.TestCase):
 def payload(self):
  return json.loads(DATA.read_text())
 def test_imports_22_research_only_rows(self):
  r=parse_public_symbol_history(self.payload(),source_url="https://omitnomis.github.io/ShareSansarScraper/api/history/BENH.json",retrieved_at="2026-11-28T16:30:00+04:00")
  self.assertEqual(r["status"],"RESEARCH_ONLY_VALIDATED")
  self.assertEqual(r["record_count"],22)
  self.assertFalse(r["production_admission_allowed"])
 def test_first_observed_session_is_15_oct_not_14_oct(self):
  r=parse_public_symbol_history(self.payload(),source_url="public",retrieved_at="2026-11-28")
  self.assertEqual(r["records"][0]["session_date"],"2026-10-15")
  self.assertIn("NOT_PROOF",r["missing_session_semantics"])
 def test_duplicate_dates_rejected(self):
  p=self.payload(); p["rows"].append(p["rows"][-1])
  r=parse_public_symbol_history(p,source_url="public",retrieved_at="2026-11-28")
  self.assertIn("duplicate_session_2026-11-27",r["errors"])
 def test_bad_ohlc_rejected(self):
  p=self.payload(); p["rows"][0][2]=200
  r=parse_public_symbol_history(p,source_url="public",retrieved_at="2026-11-28")
  self.assertIn("row_0_invalid_values",r["errors"])
 def test_reordered_columns_rejected(self):
  p=self.payload(); p["cols"][0]="open"
  r=parse_public_symbol_history(p,source_url="public",retrieved_at="2026-11-28")
  self.assertIn("unexpected_or_reordered_columns",r["errors"])
if __name__=="__main__": unittest.main()
