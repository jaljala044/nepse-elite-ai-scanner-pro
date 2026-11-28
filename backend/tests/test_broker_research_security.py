import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.broker_research_security import BrokerResearchSecurity
import os

class SecurityTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI()
        @app.post("/v1/research/broker-context")
        def echo(body:dict): return body
        app.add_middleware(BrokerResearchSecurity)
        self.client=TestClient(app)
        self.path="/v1/research/broker-context"
        self.auth={"Authorization":"Bearer test-only-secret"}
    def test_missing_configuration(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_RESEARCH_TOKEN":""}):
            response=self.client.post(self.path,json={})
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.headers.get("cache-control"),"private, no-store, max-age=0")
            self.assertEqual(response.headers.get("pragma"),"no-cache")
    def test_authentication_and_replay(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_RESEARCH_TOKEN":"test-only-secret"}):
            unauthorized=self.client.post(self.path,json={})
            self.assertEqual(unauthorized.status_code,401)
            self.assertEqual(unauthorized.headers.get("cache-control"),"private, no-store, max-age=0")
            self.assertEqual(unauthorized.headers.get("pragma"),"no-cache")
            r=self.client.post(self.path,json={"value":123},headers=self.auth)
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json(),{"value":123})
            self.assertEqual(r.headers.get("cache-control"),"private, no-store, max-age=0")
            self.assertEqual(r.headers.get("pragma"),"no-cache")
    def test_size_and_rate_limit(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_RESEARCH_TOKEN":"test-only-secret"}),patch("app.broker_research_security.MAX_BYTES",64),patch("app.broker_research_security.LIMIT",2):
            oversized=self.client.post(self.path,content=b"x"*65,headers=self.auth)
            self.assertEqual(oversized.status_code,413)
            self.assertEqual(oversized.headers.get("cache-control"),"private, no-store, max-age=0")
            success=self.client.post(self.path,json={},headers=self.auth)
            self.assertEqual(success.status_code,200)
            self.assertEqual(success.headers.get("pragma"),"no-cache")
            limited=self.client.post(self.path,json={},headers=self.auth)
            self.assertEqual(limited.status_code,429)
            self.assertEqual(limited.headers.get("cache-control"),"private, no-store, max-age=0")
