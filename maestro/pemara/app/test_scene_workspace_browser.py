"""Exercise the actual episode controls and HTTP routes on a temporary project."""
import json
import mimetypes
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP.parent / "services" / "studio"))
import scene_routes
import cinema_routes
from cinema_queue import ChatStore
import video_projects as projects


class SceneBrowserTest(unittest.TestCase):
    def test_comparison_context_frame_correction_and_template(self):
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
            root = Path(tmp)
            app = FastAPI()
            app.include_router(scene_routes.router(root, lambda _: True, lambda r: r.json()))
            store=ChatStore(root/"cinema.sqlite3")
            store.heartbeat()
            app.include_router(cinema_routes.router(root,lambda _:True,lambda r:r.json(),None,store))
            client = TestClient(app)
            project = projects.create_project(root, name="Piloto teste", project_id="piloto", content_kind="animation")
            folder = root / "piloto"
            video = folder / "takes" / "scene.webm"
            subprocess.run(["ffmpeg","-loglevel","error","-f","lavfi","-i","testsrc2=size=160x90:rate=12",
                            "-t","4","-c:v","libvpx","-threads","1",str(video)],check=True)
            old = video.with_name("prior.webm")
            old.write_bytes(video.read_bytes())
            queue = projects._queue(folder)
            queue["takes"] = [{"id":f"T0{i}","name":f"Cena {i}", "maestro_status":"APPROVED","target_duration_seconds":4,
                "animation_prompt":"A personagem observa o jardim.",
                "video":{"output_active":str(video),"output_history":[{"path":str(old)}]}} for i in (1,2)]
            projects._atomic_json_write(projects._queue_path(folder), queue)

            def respond(route):
                req = route.request
                path = urlsplit(req.url).path
                if path.startswith("/api/studio/api/"):
                    endpoint = path[len("/api/studio"):]
                    if endpoint.endswith("/preview"):
                        return route.fulfill(path=str(video),content_type="video/webm")
                    if endpoint=="/api/video-projects":
                        return route.fulfill(json=projects.list_projects(root))
                    if endpoint.startswith("/api/video-projects/") and len(endpoint.split("/")) <= 5:
                        pid = endpoint.split("/")[3]
                        try:
                            payload = projects.list_takes(root,pid) if endpoint.endswith("/takes") else projects.get_project(root,pid)
                            return route.fulfill(json=payload)
                        except (ValueError,FileNotFoundError):
                            pass
                    if "/cinema/" in endpoint or "/episode-templates" in endpoint or "/versions" in endpoint or "/frame-marks" in endpoint:
                        response=client.request(req.method,endpoint,params=urlsplit(req.url).query,content=req.post_data_buffer,headers=req.headers)
                        return route.fulfill(status=response.status_code,body=response.content,headers=dict(response.headers))
                if path.startswith("/api/"):
                    return route.fulfill(json={"data":[],"items":[],"providers":[]})
                asset = (APP / (path.lstrip("/") or "index.html")).resolve()
                if asset.is_relative_to(APP) and asset.is_file():
                    return route.fulfill(path=str(asset), content_type=mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
                return route.fulfill(status=404,body="")

            browser = pw.chromium.launch()
            try:
                page = browser.new_page()
                page.route("**/*",respond)
                page.goto("https://maestro.test/")
                page.locator('[data-section="films"]').click()
                page.get_by_role("button",name="Abrir Cinema Studio").click()
                page.locator("#scene-strip button").nth(1).click()
                try:
                    page.wait_for_function("document.querySelector('#scene-player').readyState >= 2", timeout=7000)
                except Exception:
                    self.fail(str(page.locator("#scene-player").evaluate("(v) => [v.currentSrc,v.error?.message,v.readyState,document.querySelector('#scene-feedback').textContent]")))
                page.locator("#scene-compare").select_option(index=2)
                page.wait_for_function("document.querySelector('#scene-compare-player').readyState >= 2")
                page.locator("#scene-player").evaluate("(v) => v.currentTime = 1.5")
                page.wait_for_function("Math.abs(document.querySelector('#scene-compare-player').currentTime-1.5)<0.1")
                page.locator("#scene-mark").click()
                page.wait_for_selector("#scene-marks button")
                page.locator("#scene-context").click()
                page.wait_for_function("document.querySelector('#scene-player').currentSrc.includes('T01/preview')")
                page.wait_for_function("document.querySelector('#scene-player').currentSrc.includes('T02/versions')", timeout=10000)
                page.locator("#scene-correct").click()
                self.assertTrue(page.locator("#film-director-dialog").is_visible())
                self.assertEqual(page.locator("#film-director-take-id").input_value(),"T02")
                page.locator("#film-director-cancel").click()
                page.locator("#scene-workspace-open").click()
                page.locator("#scene-frame").click()
                page.wait_for_function("document.querySelector('#gen-base-image').files.length === 1")
                self.assertIn("piloto_T02_",page.locator("#gen-base-image").input_value())
                page.locator('[data-section="films"]').click()
                page.locator("#episode-templates-open").click()
                page.locator("#episode-save input").fill("Modelo reutilizável")
                page.locator("#episode-save button").click()
                page.wait_for_function("document.querySelector('#episode-create select').options.length === 1")
                page.locator("#episode-create input").fill("Episodio seguinte")
                page.locator("#episode-create button").click()
                page.wait_for_function("!document.querySelector('#episode-models').open")
                self.assertEqual(len(projects.list_projects(root)["data"]),2)
                page.locator("#scene-workspace-open").click()
                page.locator("#cinema-send textarea").fill("Prepare um plano geral do jardim.")
                page.locator("#cinema-send button").click()
                page.wait_for_function("document.querySelector('#cinema-messages').textContent.includes('Prepare um plano')")
                page.close()
                turn=store.claim()
                store.update(turn["id"],"done","Concluído",{"answer":"Comece com um plano geral do jardim.",
                             "shots":[],"correction":"","photography":None})
                second=browser.new_context(viewport={"width":393,"height":852})
                mobile=second.new_page()
                mobile.route("**/*",respond)
                mobile.goto("https://maestro.test/")
                mobile.locator('[data-section="films"]').click()
                mobile.locator("#scene-workspace-open").click()
                mobile.get_by_text("Comece com um plano geral do jardim.",exact=True).wait_for()
                with mobile.expect_response(lambda r:"/cinema/chat?since=" in r.url) as refreshed:
                    mobile.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                self.assertTrue(refreshed.value.json()["unchanged"])
                self.assertTrue(mobile.get_by_text("Comece com um plano geral do jardim.",exact=True).is_visible())
                mobile.get_by_role("button",name="Fotografia",exact=True).click()
                mobile.locator("#cinema-fields [name=palette]").fill("Âmbar")
                mobile.get_by_role("button",name="Salvar direção",exact=True).click()
                mobile.get_by_text("Direção salva no projeto.",exact=True).wait_for()
                self.assertTrue(mobile.locator("#scene-desk").evaluate("(e) => e.scrollWidth <= e.clientWidth + 1"))
                second.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()

