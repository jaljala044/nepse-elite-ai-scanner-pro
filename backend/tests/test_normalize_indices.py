import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app.normalize_indices as ni

class NormalizeIndicesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.source=self.root/"indices_2024-01-02.csv.gz"
        self.silver=self.root/"data"/"silver"/"indices"
        self.quarantine=self.root/"data"/"quarantine"
        self.fields=["date","sector","open","high","low","close","absolute_change","percentage_change",
                     "number_52_weeks_high","number_52_weeks_low","turnover_values","turnover_volume",
                     "total_transaction","sn","id","created_at"]
    def tearDown(self):
        self.tmp.cleanup()
    def row(self, **changes):
        row={"date":"2024-01-02","sector":"NEPSE Index","open":"2060.47","high":"2061.92",
             "low":"2024.15","close":"2030.10","absolute_change":"-30.05",
             "percentage_change":"-1.46%","number_52_weeks_high":"2277.61",
             "number_52_weeks_low":"1807.53","turnover_values":"4043871307.00",
             "turnover_volume":"0","total_transaction":"0","sn":"12","id":"58779",
             "created_at":"2025-12-15T13:21:32.782062+05:45"}
        row.update(changes)
        return row
    def write(self, rows):
        with gzip.open(self.source,"wt",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=self.fields)
            writer.writeheader()
            writer.writerows(rows)
        return self.source
    def import_file(self,path):
        with patch.object(ni,"ROOT",self.root), patch.object(ni,"SILVER",self.silver), patch.object(ni,"QUARANTINE",self.quarantine):
            return ni.normalize_sector_index_csv(path,source="test")
    def test_gzip_sector_index(self):
        path=self.write([self.row()])
        result=self.import_file(path)
        self.assertEqual(result["unique_rows_accepted"],1)
        out=self.silver/"date=2024-01-02"/"indices.csv"
        with out.open(encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]["percentage_change_pct"],"-1.46")
        self.assertEqual(rows[0]["turnover_volume"],"0")
    def test_conflicting_duplicate_index_is_rejected(self):
        path=self.write([self.row(),self.row(close="2031.00")])
        with self.assertRaises(ValueError):
            self.import_file(path)
    def test_invalid_ohlc_is_quarantined(self):
        path=self.write([self.row(high="1000")])
        with self.assertRaises(ValueError):
            self.import_file(path)
        self.assertTrue(any(self.quarantine.glob("index_rejects_*.jsonl")))
if __name__=="__main__":
    unittest.main()
