import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import scene_routes
import video_projects as projects


class EpisodeWorkspaceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        app = FastAPI()
        app.include_router(scene_routes.router(self.root, lambda request: request.headers.get("x-test") == "yes",
                                               lambda request: request.json()))
        self.client = TestClient(app, headers={"x-test": "yes"})
        self.templates = "/api/episode-templates"
        self.spec = {"name": "Modelo de teste", "contentKind": "animation",
                     "scenes": [{"name": "Primeira cena", "durationSeconds": 4, "direction": "Abrir em plano geral."},
                                {"name": "Segunda cena", "durationSeconds": 6}]}

    def create(self):
        response = self.client.post(self.templates, json=self.spec)
        self.assertEqual(response.status_code, 201, response.text)
        url = self.templates + "/" + response.json()["templateId"] + "/episodes"
        data = {"name": "Episodio teste"}
        response = self.client.post(url, json=data)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.client.post(url, json=data).status_code, 409)
        return response.json()["projectId"]

    def test_templates_and_project(self):
        pid = self.create()
        result = projects.list_takes(self.root, pid)["data"]
        self.assertEqual([s["takeId"] for s in result], ["T01","T02"])
        self.assertEqual([s["durationSeconds"] for s in result], [4,6])
        self.assertEqual(result[0]["animationPrompt"], self.spec["scenes"][0]["direction"])
        self.assertTrue(all(s["status"] == "PLANNED" and not s["hasPreview"] for s in result))
        self.assertEqual(self.client.get(self.templates, headers={"x-test":"no"}).status_code, 403)
        self.assertEqual(self.client.post(self.templates, json={**self.spec,"contentKind":"unknown"}).status_code, 422)

    def test_versions_and_marks_stay_bound_to_sources(self):
        pid = self.create()
        folder = self.root / pid
        old, current = folder/"takes"/"old.mp4", folder/"takes"/"new.mp4"
        old.write_bytes(b"first version")
        current.write_bytes(b"second version")
        queue = projects._queue(folder)
        queue["takes"][0]["video"] = {"output_active":str(current), "output_history":[
            {"path":str(old)}, {"path":str(current)}, {"path":str(self.root/"elsewhere.mp4")}]}
        projects._atomic_json_write(projects._queue_path(folder), queue)
        url = "/api/video-projects/" + pid + "/takes/T01"
        versions = self.client.get(url+"/versions").json()["data"]
        self.assertEqual([v["file"] for v in versions], ["new.mp4","old.mp4"])
        key = versions[1]["versionId"]
        self.assertEqual(self.client.get(url+"/versions/"+key).content,b"first version")
        mark = {"versionId":key,"seconds":2.451}
        for _ in range(2):
            self.assertEqual(self.client.post(url+"/frame-marks",json=mark).status_code,201)
        self.assertEqual(self.client.get(url+"/frame-marks").json()["data"],[mark])
        old.write_bytes(b"changed media")
        self.assertEqual(self.client.get(url+"/versions/"+key).status_code,404)
        self.assertEqual(self.client.post(url+"/frame-marks",json=mark).status_code,404)


if __name__ == "__main__":
    unittest.main()

