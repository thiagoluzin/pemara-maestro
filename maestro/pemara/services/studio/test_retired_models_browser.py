"""Generator picker regression with isolated local fixtures; no GPU requests."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright
from image_engines import ENGINES, QWEN_MODEL, HIDREAM_MODEL


def test_removed_models_are_absent_and_stale_image_preference_is_cleared():
    app_root = Path(__file__).resolve().parents[2] / "app"

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(app_root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    status = {"ok": True, "comfy_online": True, "defaults": {"image_model": QWEN_MODEL},
              "models": {"video": [], "image": [QWEN_MODEL, HIDREAM_MODEL], "loras": []},
              "providers": {"audio": {}},
              "imageEngines": [{k: v for k, v in e.items() if k != "requirements"} | {"ready": True} for e in ENGINES],
              "videoEngines": {"engines": [{"id": "minimax_h3", "display_name": "MiniMax H3",
                  "selectable": True, "readiness": {"state": "READY", "production_ready": True}}]}}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            issues, posts = [], []
            page.on("pageerror", lambda error: issues.append(str(error)))
            page.add_init_script("localStorage.setItem('maestro.imageEngine.image', 'llada_base')")

            def route_api(route):
                if route.request.method == "POST":
                    posts.append(route.request.url)
                    route.fulfill(status=409, content_type="application/json", body='{"erro":"Fixture: GPU disabled"}')
                    return
                payload = status if route.request.url.endswith("/api/generative/status") else {"ok": True, "items": [], "data": [], "total": 0, "services": {}}
                route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

            page.route("**/api/**", route_api)
            page.goto(f"http://127.0.0.1:{server.server_port}/index.html", wait_until="networkidle")
            page.locator('.nav-link[data-section="gen"]').click()
            page.locator('[data-gen-mode="image"]').click()
            options = page.locator("#gen-image-engine option").evaluate_all("options => options.map(o => o.value)")
            assert options == ["", "qwen21", "qwen21_fix", "hidream_o1"]
            assert page.locator("#gen-image-engine").input_value() == ""
            assert page.evaluate("localStorage.getItem('maestro.imageEngine.image')") is None
            page.locator("#gen-image-engine").select_option("hidream_o1")
            assert page.locator("#gen-model").input_value() == HIDREAM_MODEL
            page.locator('[data-gen-mode="video"]').click()
            assert page.locator('[data-video-engine-id="hunyuan_video_15"]').count() == 0
            h3 = page.locator('[data-video-engine-id="minimax_h3"]')
            assert h3.count() == 1 and h3.get_attribute("aria-checked") == "false"
            h3.click()
            assert h3.get_attribute("aria-checked") == "true"
            assert posts == [] and issues == []
            evidence = os.environ.get("PEMARA_RETIRED_MODELS_QA_DIR")
            if evidence:
                target = Path(evidence);target.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(target / "maestro_retired_models_fixture.png"), full_page=True)
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
