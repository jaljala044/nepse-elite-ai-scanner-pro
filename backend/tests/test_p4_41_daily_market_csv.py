import unittest
from pathlib import Path
from app.p4_41_daily_market_csv import parse_daily_market_csv,find_symbol_record

HEADER="S.No,Symbol,Conf.,Open,High,Low,Close,LTP,Close - LTP,Close - LTP %,VWAP,Vol,Prev. Close,Turnover,Trans.,Diff,Range,Diff %,Range %,VWAP %,120 Days,180 Days,52 Weeks High,52 Weeks Low"
EVIDENCE=Path(__file__).parents[2]/"data/evidence/benh/2026-11-28/public_daily_csv"
def line(n,symbol,open_,high,low,close,vol,turnover,trans):
 vol_field = f'"{vol}"' if "," in str(vol) else vol
 turnover_field = f'"{turnover}"' if "," in str(turnover) else turnover
 return f'{n},{symbol},30,{open_},{high},{low},{close},{close},0,0,{close},{vol_field},100,{turnover_field},{trans},0,0,0,0,0,0,0,0,0'
class DailyMarketCSVTests(unittest.TestCase):
 def parse(self,body):
  return parse_daily_market_csv(HEADER+"\n"+body,session_date="2026-10-14",source_url="https://example.test/2026_10_14.csv",retrieved_at="2026-11-28T17:00:00+04:00")
 def parse_evidence(self,day):
  raw=(EVIDENCE/f"{day}.csv").read_text()
  return parse_daily_market_csv(raw,session_date=day,source_url=f"https://raw.githubusercontent.com/OmitNomis/ShareSansarScraper/master/docs/Data/{day.replace('-','_')}.csv",retrieved_at="2026-11-28T17:00:00Z")
 def test_valid_marketwide_rows(self):
  r=self.parse(line(1,"ADBL",320,328,320,328,"139,162","45,263,784.50",517)+"\n"+line(2,"BENH",273,313.9,273,313.9,90,26634,9))
  self.assertEqual(r["status"],"RESEARCH_ONLY_VALIDATED"); self.assertEqual(r["row_count"],2)
  self.assertEqual(find_symbol_record(r,"benh")["record"]["volume"],90)
 def test_symbol_absence_is_not_zero_trade(self):
  r=self.parse(line(1,"ADBL",320,328,320,328,10,1000,2))
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"NOT_PRESENT_IN_ARCHIVE_FILE")
 def test_duplicate_symbol_flagged(self):
  row=line(1,"ADBL",320,328,320,328,10,1000,2)
  r=self.parse(row+"\n"+row.replace("1,ADBL","2,ADBL"))
  self.assertIn("line_3_duplicate_symbol_ADBL",r["errors"])
  self.assertEqual(r["status"],"REJECTED")
 def test_invalid_ohlc_row_quarantined_without_losing_valid_rows(self):
  r=self.parse(line(1,"ADBL",320,310,320,328,10,1000,2)+"\n"+line(2,"BENH",273,313.9,273,313.9,90,26634,9))
  self.assertEqual(r["status"],"RESEARCH_ONLY_WITH_QUARANTINE")
  self.assertEqual(r["row_count"],1)
  self.assertEqual(r["quarantined_row_count"],1)
  self.assertEqual(find_symbol_record(r,"ADBL")["status"],"QUARANTINED_ROW")
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"FOUND")
 def test_quarantined_symbol_is_not_reported_absent(self):
  r=self.parse(line(1,"BENH",273,270,273,313.9,90,26634,9))
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"QUARANTINED_ROW")
 def test_non_finite_numeric_values_are_quarantined(self):
  for value in ("NaN","Infinity","-Infinity"):
   r=self.parse(line(1,"BENH",273,313.9,273,313.9,value,26634,9))
   self.assertEqual(find_symbol_record(r,"BENH")["status"],"QUARANTINED_ROW")
   self.assertEqual(r["quarantined_rows"][0]["reasons"],["non_finite_numeric"])
 def test_extra_csv_fields_are_quarantined(self):
  r=self.parse(line(1,"BENH",273,313.9,273,313.9,90,26634,9)+",unexpected")
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"QUARANTINED_ROW")
  self.assertEqual(r["quarantined_rows"][0]["reasons"],["extra_csv_fields"])
 def test_duplicate_symbol_quarantines_both_source_rows(self):
  row=line(1,"BENH",273,313.9,273,313.9,90,26634,9)
  r=self.parse(row+"\n"+line(2,"BENH",273,313.9,273,313.9,91,27000,10))
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"QUARANTINED_ROW")
  self.assertEqual([x["source_line"] for x in r["quarantined_rows"]],[2,3])
  self.assertEqual(r["records"],[])
 def test_numeric_grouping_is_strict(self):
  r=self.parse(line(1,"BENH",273,313.9,273,313.9,"12,34",26634,9))
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"QUARANTINED_ROW")
  self.assertEqual(r["quarantined_rows"][0]["reasons"],["malformed_numeric"])
 def test_source_artifact_digest_is_bound_to_each_row(self):
  body=line(1,"BENH",273,313.9,273,313.9,90,26634,9)
  r=self.parse(body)
  self.assertEqual(r["records"][0]["source_artifact_sha256"],r["source_artifact"]["sha256"])
  self.assertEqual(r["records"][0]["parser_version"],r["source_artifact"]["parser_version"])
 def test_missing_required_column_rejected(self):
  r=parse_daily_market_csv("Symbol,Open,High,Low,Close\nADBL,1,2,1,2",session_date="2026-10-14",source_url="https://example.test/data.csv",retrieved_at="2026-11-28T17:00:00Z")
  self.assertIn("missing_columns",r["errors"][0])
 def test_invalid_session_rejected(self):
  r=parse_daily_market_csv(HEADER,session_date="bad",source_url="public",retrieved_at="now")
  self.assertIn("invalid_session_date",r["errors"])
 def test_retained_14_oct_file_has_no_benh_row(self):
  r=self.parse_evidence("2026-10-14")
  self.assertEqual(r["status"],"RESEARCH_ONLY_WITH_QUARANTINE")
  self.assertEqual((r["source_row_count"],r["row_count"],r["quarantined_row_count"]),(354,352,2))
  self.assertEqual({x["symbol"] for x in r["quarantined_rows"]},{"KBLD86","NICD88"})
  self.assertEqual(find_symbol_record(r,"BENH")["status"],"NOT_PRESENT_IN_ARCHIVE_FILE")
 def test_retained_15_oct_file_contains_benh_first_observed_row(self):
  r=self.parse_evidence("2026-10-15")
  found=find_symbol_record(r,"BENH")
  self.assertEqual(r["status"],"RESEARCH_ONLY_WITH_QUARANTINE")
  self.assertEqual((r["source_row_count"],r["row_count"],r["quarantined_row_count"]),(349,346,3))
  self.assertEqual({x["symbol"] for x in r["quarantined_rows"]},{"CBLD88","CCBD88","KBLD86"})
  self.assertEqual(found["status"],"FOUND")
  self.assertEqual((found["record"]["open"],found["record"]["high"],found["record"]["low"],found["record"]["close"]),(273.0,313.9,273.0,313.9))
  self.assertEqual((found["record"]["volume"],found["record"]["turnover"],found["record"]["transactions"]),(90.0,26634.0,9.0))

 def test_naive_retrieval_timestamp_is_rejected(self):
  r=parse_daily_market_csv(HEADER,session_date="2026-10-14",source_url="https://example.test/data.csv",retrieved_at="2026-11-28")
  self.assertEqual(r["status"],"REJECTED")
  self.assertIn("invalid_retrieved_at_utc",r["errors"])
 def test_non_https_or_credentialed_source_url_is_rejected(self):
  for url in ("http://example.test/data.csv","https://user@example.test/data.csv","https://example.test/data.csv#fragment"):
   r=parse_daily_market_csv(HEADER,session_date="2026-10-14",source_url=url,retrieved_at="2026-11-28T17:00:00Z")
   self.assertEqual(r["status"],"REJECTED")
   self.assertIn("invalid_source_url",r["errors"])
 def test_retrieval_timestamp_is_normalized_to_utc(self):
  r=self.parse(line(1,"BENH",273,313.9,273,313.9,90,26634,9))
  self.assertEqual(r["source_artifact"]["retrieved_at"],"2026-11-28T13:00:00Z")

if __name__=="__main__": unittest.main()
