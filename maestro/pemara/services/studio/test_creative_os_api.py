import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.api import create_router
from test_creative_os_ir import sample


class APITests(unittest.TestCase):
    def test_real_routes_invalid_request_and_one_submission(self):
        with tempfile.TemporaryDirectory() as d:
            submit=Mock(return_value="j1")
            s=CreativeService(d,d,Bridge(submit,Mock(),lambda:{"engines":{"minimax_h3":{"runnable":True}}},Mock(),Mock()))
            app=FastAPI(); app.include_router(create_router(s))
            with TestClient(app) as c:
                self.assertEqual(c.get("/api/creative/health").json()["codex_transport"],"mcp_only")
                self.assertEqual(c.post("/api/creative/shots",json={}).status_code,422)
                self.assertEqual(c.post('/api/creative/control-assets',files={'file':('bad.exe',b'fixture')}).status_code,422)
                shot=c.post("/api/creative/shots",json=sample()).json()
                route=c.post(f"/api/creative/shots/{shot['id']}/route").json()
                self.assertEqual(route["route"]["selected_engine"],"minimax_h3")
                for _ in range(2):
                    result=c.post(f"/api/creative/shots/{shot['id']}/generate",json={"idempotency_key":"one"})
                    self.assertEqual(result.status_code,202,result.text)
                submit.assert_called_once()
