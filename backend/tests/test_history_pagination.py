import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app import main

class HistoryPaginationTests(unittest.TestCase):
    def test_pages(self):
        rows=[{"date":"2026-01-03","close":3},{"date":"2026-01-01","close":1},{"date":"2026-01-02","close":2}]
        with patch.dict(main.DATA,{"TEST":rows}):
            a=main.history_page("TEST",0,2)
            b=main.history_page("TEST",a["next_offset"],2,a["snapshot"])
            self.assertEqual([r["close"] for r in a["rows"]+b["rows"]],[1,2,3])
            self.assertIsNone(b["next_offset"])
            self.assertEqual(a["total"],3)
            for offset,limit,snapshot,code in [(2,2,None,409),(2,2,"bad",409),(-1,2,None,422),(0,1001,None,422),(4,2,a["snapshot"],422)]:
                with self.assertRaises(HTTPException) as ctx:
                    main.history_page("TEST",offset,limit,snapshot)
                self.assertEqual(ctx.exception.status_code,code)
            rows.append({"date":"2026-01-04","close":4})
            with self.assertRaises(HTTPException) as ctx:
                main.history_page("TEST",2,2,a["snapshot"])
            self.assertEqual(ctx.exception.status_code,409)
