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

    def test_price_alert_rules_and_events(self):
        from app.private_accounts import add_alert, delete_alert, list_alerts, evaluate_price_alerts
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ",{"NEPSE_PRIVATE_DB":str(Path(d)/"accounts.db")}):
            add_alert("alice","NABIL","above","500")
            add_alert("alice","NABIL","above","500.00")
            self.assertEqual(len(list_alerts("alice")),1)
            self.assertEqual(list_alerts("bob"),[])
            observation={"symbol":"NABIL","session_date":"2026-11-20","close":"501","source_validation_status":"verified","finality_status":"final","source_id":"test_fixture","source_payload_sha256":"a"*64}
            self.assertEqual(evaluate_price_alerts("alice",dict(observation,finality_status="provisional")),[])
            self.assertEqual(evaluate_price_alerts("alice",dict(observation,close="499")),[])
            self.assertEqual(evaluate_price_alerts("bob",observation),[])
            self.assertEqual(len(evaluate_price_alerts("alice",observation)),1)
            self.assertEqual(evaluate_price_alerts("alice",observation),[])
            self.assertEqual(delete_alert("alice","NABIL","above","500"),[])
            for price in ("NaN","-1","1.001"):
                with self.assertRaises(ValueError):
                    add_alert("alice","NABIL","above",price)

    def test_mobile_sessions(self):
        from app.private_accounts import issue_mobile_session, mobile_principal, revoke_mobile_session
        from fastapi import HTTPException
        import time
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ",{"NEPSE_PRIVATE_DB":str(Path(d)/"accounts.db")}):
            now=int(time.time())
            a="Bearer "+issue_mobile_session("alice",now)["access_token"]
            b="Bearer "+issue_mobile_session("bob",now)["access_token"]
            self.assertEqual(mobile_principal(a,now),"alice")
            self.assertEqual(mobile_principal(b,now),"bob")
            with self.assertRaises(HTTPException):
                mobile_principal(a,now+900)
            revoke_mobile_session(a)
            with self.assertRaises(HTTPException):
                mobile_principal(a,now)
            self.assertEqual(mobile_principal(b,now),"bob")
            with self.assertRaises(HTTPException):
                mobile_principal("Bearer "+"x"*43,now)

    def test_account_http_boundaries(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.private_accounts import issue_mobile_session
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ",{
            "NEPSE_PRIVATE_DB":str(Path(d)/"accounts.db"),
            "NEPSE_PROXY_SECRET":"s"*32,
            "NEPSE_MOBILE_GATEWAY_PROOF":"g"*32,
            "NEPSE_MOBILE_EXCHANGE_ENABLED":"0",
            "NEPSE_DEPLOYMENT_MODE":"private",
            "NEPSE_ADMIN_SUBJECTS":"alice",
        }):
            client=TestClient(app)
            proxy={"x-nepse-proxy-secret":"s"*32,"x-nepse-subject":"alice"}
            gateway=dict(proxy,**{"x-nepse-mobile-gateway-proof":"g"*32})
            self.assertEqual(client.get("/v1/account/watchlist").status_code,401)
            self.assertEqual(client.post("/v1/account/mobile/session",headers=proxy).status_code,403)
            self.assertEqual(client.post("/v1/account/mobile/session",headers=gateway).status_code,503)
            with patch.dict("os.environ",{"NEPSE_MOBILE_EXCHANGE_ENABLED":"1"}):
                issued=client.post("/v1/account/mobile/session",headers=gateway)
                self.assertEqual(issued.status_code,200)
                self.assertEqual(issued.headers["cache-control"],"no-store")
                alice={"authorization":"Bearer "+issued.json()["access_token"]}
            bob={"authorization":"Bearer "+issue_mobile_session("bob")["access_token"]}
            self.assertEqual(client.put("/v1/account/watchlist",headers=alice,json={"symbols":["AAA","AAA"]}).json()["symbols"],["AAA"])
            self.assertEqual(client.get("/v1/account/watchlist",headers=bob).json()["symbols"],[])
            self.assertEqual(client.post("/v1/account/alerts",headers=alice,json={"symbol":"AAA","direction":"above","threshold":"500"}).status_code,200)
            self.assertEqual(client.get("/v1/account/alerts",headers=bob).json()["rules"],[])
            self.assertEqual(client.post("/v1/ingest/csv",headers=alice).status_code,401)
            self.assertEqual(client.post("/v1/account/mobile/logout",headers=alice).status_code,200)
            self.assertEqual(client.get("/v1/account/watchlist",headers=alice).status_code,401)
            self.assertEqual(client.get("/v1/account/watchlist",headers=bob).status_code,200)
