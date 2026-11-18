"""Exercise the actual generator UI against local fixtures only."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright


class HunyuanBrowserTests(unittest.TestCase):
    def test_picker_timing_and_submission(self):
        root = Path(__file__).resolve().parents[2]
        evidence = root.parents[1] / "work/hunyuan15_install_20261110"
        server = subprocess.Popen([sys.executable, "-m", "http.server", "18099", "--bind", "127.0.0.1",
            "--directory", str(root / "app")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            status = {"ok": True, "comfy_online": True, "defaults": {}, "models": {"video": [], "loras": []},
                "providers": {"audio": {}}, "videoEngines": {"engines": [
                    {"id": engine, "display_name": label, "selectable": True,
                     "readiness": {"state": "READY", "production_ready": True}}
                    for engine, label in (("minimax_h3", "MiniMax H3"), ("hunyuan_video_15", "HunyuanVideo 1.5"))]}}
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                issues, posts = [], []
                page.on("pageerror", lambda error: issues.append(str(error)))
                def route_api(route):
                    if route.request.url.endswith("/api/generative/status"):
                        payload = status
                    elif route.request.method == "POST" and route.request.url.endswith("/api/generative/job"):
                        posts.append(route.request.post_data_buffer)
                        route.fulfill(status=409, content_type="application/json", body='{"erro":"Teste interceptado antes da GPU"}')
                        return
                    else:
                        payload = {"ok": True, "items": [], "data": [], "total": 0, "services": {}}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                page.route("**/api/**", route_api)
                page.goto("http://127.0.0.1:18099/index.html", wait_until="networkidle")
                page.locator('.nav-link[data-section="gen"]').click()
                page.locator('[data-gen-mode="video"]').click()
                page.locator('[data-video-engine-id="hunyuan_video_15"]').click()
                self.assertEqual(page.locator("#gen-steps").input_value(), "50")
                self.assertEqual(page.locator("#gen-fps").input_value(), "24")
                self.assertEqual(page.locator("#gen-frames").input_value(), "121")
                self.assertFalse(page.locator("#gen-end-image-label").is_visible())
                self.assertFalse(page.locator("#gen-video-direction").is_visible())
                page.locator("#gen-video-duration").fill("10")
                page.locator("#gen-video-duration").dispatch_event("change")
                self.assertEqual(page.locator("#gen-frames").input_value(), "241")
                page.locator("#gen-content-kind").select_option("animation")
                page.locator("#gen-prompt").fill("Dois lutadores trocam um golpe e uma esquiva.")
                import io
                from PIL import Image
                anchor = io.BytesIO()
                Image.new("RGB", (64, 64), "blue").save(anchor, format="PNG")
                page.locator("#gen-base-image").set_input_files({"name": "test.png", "mimeType": "image/png", "buffer": anchor.getvalue()})
                page.locator("#gen-submit").click()
                page.wait_for_function("!document.querySelector('#gen-submit').disabled")
                self.assertEqual(len(posts), 1)
                raw = posts[0].decode("utf-8", errors="replace")
                self.assertIn('name="engine_id"\r\n\r\nhunyuan_video_15', raw)
                self.assertIn('name="camera_pose"\r\n\r\n\r\n', raw)
                self.assertIn('name="steps"\r\n\r\n50', raw)
                self.assertIn('name="frames"\r\n\r\n241', raw)
                page.screenshot(path=str(evidence / "hunyuan_ui_fixture.png"), full_page=True)
                self.assertEqual(issues, [])
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)
