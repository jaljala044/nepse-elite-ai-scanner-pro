import unittest
from collections import Counter
from decimal import Decimal
from compare_p443_alternative_floorsheets import compare, parse

class ComparisonTests(unittest.TestCase):
    def test_duplicates_are_not_hidden(self):
        k=("123",Decimal(2),Decimal(10),Decimal(20))
        r=compare(Counter({k:1}),Counter({k:2}))
        self.assertEqual(r["exact_matches"],1)
        self.assertEqual(r["alternative_only"],1)
        self.assertFalse(r["exact_nonempty_multiset_match"])
        self.assertFalse(r["admission_allowed"])
    def test_empty_is_not_confirmation(self):
        self.assertFalse(compare(Counter(),Counter())["exact_nonempty_multiset_match"])
    def test_aliases_and_bad_amount(self):
        raw=b"contract_no,stock_symbol,business_date,quantity,rate,amount\n123,RAWA,2026-04-29,2,10,20\n124,RAWA,2026-04-29,2,10,1\n"
        rows,errors=parse(raw,"2026-04-29",{"RAWA"})
        self.assertEqual(sum(rows["RAWA"].values()),1)
        self.assertEqual(errors["RAWA"],1)
