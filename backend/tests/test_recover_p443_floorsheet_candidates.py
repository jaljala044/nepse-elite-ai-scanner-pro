import hashlib
import unittest
from recover_p443_floorsheet_candidates import extract

HEADER = "transaction,symbol,buyer,seller,quantity,rate,amount,date\n"

def fixture(body):
    raw = (HEADER+body).encode()
    return {"size_bytes":len(raw),"git_blob_sha":hashlib.sha1(
        f"blob {len(raw)}\0".encode()+raw).hexdigest(),
        "date":"2026-04-29","symbols":["RAWA"]},raw

class RecoveryTests(unittest.TestCase):
    def test_reconstruct_without_admission(self):
        item,raw=fixture("20260429002,RAWA,1,2,20,610,12200,2026-04-29\n"
                         "20260429001,RAWA,2,1,10,600,6000,2026-04-29\n")
        row=extract(item,raw)[0]
        self.assertEqual((row["open"],row["high"],row["low"],row["close"],row["volume"]),
                         ("600","610","600","610","30"))
        self.assertFalse(row["admission_allowed"])
        self.assertEqual(row["ordering"],"contract_number_unverified")

    def test_duplicate_and_bad_amount_block(self):
        line="20260429001,RAWA,1,2,10,600,6000,2026-04-29\n"
        item,raw=fixture(line+line+"20260429002,RAWA,1,2,10,600,1,2026-04-29\n")
        row=extract(item,raw)[0]
        self.assertEqual(row["status"],"blocked")
        self.assertGreater(row["target_errors"],0)
        self.assertFalse(row["admission_allowed"])

    def test_integrity_and_missing_trades(self):
        item,raw=fixture("")
        self.assertEqual(extract(item,raw)[0]["status"],"blocked")
        with self.assertRaises(ValueError):
            extract(item,raw+b"x")
