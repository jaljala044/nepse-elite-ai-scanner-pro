import unittest
from datetime import date,timedelta
from app.index_intelligence import index_intelligence
class IndexIntelligenceTests(unittest.TestCase):
    def fixture(self):
        days=[str(date(2025,1,1)+timedelta(days=i)) for i in range(65)]
        rows=[dict(index=k,date=d,close=100+i*m,reviewed=True,evidence_id="fixture") for k,m in [("NEPSE",1),("BANK",2)] for i,d in enumerate(days)]
        return rows,dict(sessions=days,benchmark="NEPSE",expected_indices=["NEPSE","BANK"],calendar_verified=True)
    def test_trend_rotation(self):
        rows,kw=self.fixture()
        r=index_intelligence(rows,**kw)
        self.assertEqual(r["indices"]["NEPSE"]["trend"],"bullish")
        self.assertGreater(r["indices"]["BANK"]["rotation_trail"][-1]["relative_return_pct"],0)
        self.assertIsNone(r["production_score"])
    def test_missing_session(self):
        rows,kw=self.fixture()
        r=index_intelligence(rows[:-1],**kw)
        self.assertEqual(r["indices"]["BANK"]["status"],"unavailable")
    def test_duplicate(self):
        rows,kw=self.fixture()
        self.assertEqual(index_intelligence(rows+[rows[0]],**kw)["reason"],"duplicate_or_out_of_scope")
    def test_calendar_gate(self):
        rows,kw=self.fixture()
        kw["calendar_verified"]=False
        self.assertEqual(index_intelligence(rows,**kw)["status"],"unavailable")
