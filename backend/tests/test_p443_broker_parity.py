import unittest
from collections import Counter
from decimal import Decimal
from compare_p443_alternative_floorsheets import compare, broker_signature, parse_broker_trades

class BrokerParityTests(unittest.TestCase):
    def test_buyer_seller_identity_is_part_of_match(self):
        k=("1",Decimal(10),Decimal(5),Decimal(50),101,202)
        changed=("1",Decimal(10),Decimal(5),Decimal(50),102,202)
        r=compare(Counter({k:1}),Counter({changed:1}))
        self.assertEqual(r["exact_matches"],0)
        self.assertEqual(r["primary_only"],1)
        self.assertEqual(r["alternative_only"],1)
    def test_missing_or_invalid_broker_rejected(self):
        with self.assertRaises(ValueError):
            broker_signature({"buyer":"101","seller":""})
        with self.assertRaises(ValueError):
            broker_signature({"buyer":"0","seller":"202"})
    def test_broker_and_timestamp_fields(self):
        raw=b"contract_no,stock_symbol,calculation_date,quantity,rate,amount,buyer,seller,time\n1,RAWA,2026-04-29,10,5,50,101,202,11:00:00\n"
        rows,errors,timestamps,headers=parse_broker_trades(raw,"2026-04-29",{"RAWA"})
        self.assertEqual(sum(rows["RAWA"].values()),1)
        self.assertEqual(errors["RAWA"],0)
        self.assertEqual(timestamps["RAWA"],1)
