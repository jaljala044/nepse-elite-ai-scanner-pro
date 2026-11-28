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
            self.assertEqual(self.client.post(self.path,json={}).status_code,503)
    def test_authentication_and_replay(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_RESEARCH_TOKEN":"test-only-secret"}):
            self.assertEqual(self.client.post(self.path,json={}).status_code,401)
            r=self.client.post(self.path,json={"value":123},headers=self.auth)
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json(),{"value":123})
    def test_size_and_rate_limit(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_RESEARCH_TOKEN":"test-only-secret"}),patch("app.broker_research_security.MAX_BYTES",64),patch("app.broker_research_security.LIMIT",2):
            self.assertEqual(self.client.post(self.path,content=b"x"*65,headers=self.auth).status_code,413)
            self.assertEqual(self.client.post(self.path,json={},headers=self.auth).status_code,200)
            self.assertEqual(self.client.post(self.path,json={},headers=self.auth).status_code,429)
