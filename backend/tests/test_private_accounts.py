import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.private_accounts import watchlist,set_watchlist
class PrivateAccountsTests(unittest.TestCase):
    def test_isolation(self):
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ",{"NEPSE_PRIVATE_DB":str(Path(d)/"accounts.db")}):
            self.assertEqual(set_watchlist("a",["AAA","AAA"]),["AAA"])
            self.assertEqual(watchlist("b"),[])
            set_watchlist("b",["BBB"])
            self.assertEqual(watchlist("a"),["AAA"])
            self.assertEqual(watchlist("b"),["BBB"])
