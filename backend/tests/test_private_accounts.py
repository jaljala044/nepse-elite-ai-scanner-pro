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

    def test_proxy_authentication(self):
        from app.private_accounts import principal
        from fastapi import HTTPException
        from starlette.requests import Request
        def req(secret, subject):
            return Request({"type":"http","headers":[(b"x-nepse-proxy-secret",secret.encode()),(b"x-nepse-subject",subject.encode())]})
        with patch.dict("os.environ",{"NEPSE_PROXY_SECRET":"a"*32}):
            self.assertEqual(principal(req("a"*32,"alice")),"alice")
            for secret, subject in [("wrong","alice"),("a"*32,""),("a"*32,"bad subject")]:
                with self.assertRaises(HTTPException) as ctx:
                    principal(req(secret,subject))
                self.assertEqual(ctx.exception.status_code,401)

    def test_roles(self):
        from app.main import account_session
        with patch.dict("os.environ",{"NEPSE_ADMIN_SUBJECTS":"alice"}):
            self.assertEqual(account_session("alice")["role"],"administrator")
            self.assertFalse(account_session("bob")["permissions"]["admin_ingestion"])
            self.assertFalse(account_session("alice")["permissions"]["ai_recommendations"])
