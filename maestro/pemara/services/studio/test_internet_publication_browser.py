"""Headless Maestro flow with a real, isolated Studio API and synthetic media."""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import expect, sync_playwright

import main as studio
import internet_publication as publication
from test_internet_publication import BRIEF, PLAN, install_synthetic_master


class PublicationBrowserTests(unittest.TestCase):
    def test_brief_plan_package_and_manual_metrics_on_real_routes(self):
        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(prefix="pemara-internet-browser-") as temporary:
            root = Path(temporary)
            evidence = Path(os.environ.get("PEMARA_INTERNET_EVIDENCE_DIR", temporary))
            evidence.mkdir(parents=True, exist_ok=True)
            with mock.patch.object(studio, "VIDEO_PROJECTS_ROOT", root):
                wrapper = FastAPI()
                wrapper.mount("/api/studio", studio.app)
                wrapper.mount("/", StaticFiles(directory=repo / "app", html=True))
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
                config = uvicorn.Config(wrapper, log_level="error", lifespan="off", access_log=False)
                server = uvicorn.Server(config)
                thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
                thread.start()
                try:
                    deadline = time.monotonic() + 10
                    while not server.started and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(server.started, "isolated API failed to start")
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(channel="msedge", headless=True)
                        try:
                            page = browser.new_page(viewport={"width": 1440, "height": 1000})
                            errors = []
                            mutations = []
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            def intercept(route):
                                request = route.request
                                if "/api/studio/api/video-projects" in request.url:
                                    if request.method not in {"GET", "HEAD"}:
                                        mutations.append({"method": request.method, "path": request.url.split(str(port), 1)[-1]})
                                    route.continue_()
                                else:
                                    # Other dashboards are not under test; do not poll GPU/model services.
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps({
                                        "ok": True, "data": [], "items": [], "total": 0, "services": {},
                                        "models": {"image": [], "video": [], "loras": [], "qwen_edit": [], "qwen": []},
                                        "defaults": {}, "providers": {"audio": {}},
                                    }))
                            page.route("**/api/**", intercept)
                            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
                            page.locator('.nav-link[data-section="films"]').click()
                            page.locator(".film-project-admin > summary").click()
                            page.locator("#film-name").fill("Navegador Sintético")
                            page.locator("#film-objective").fill(BRIEF)
                            expect(page.locator("#film-distribution-preview")).to_contain_text("Publicação na internet detectada")
                            page.locator("#film-create-submit").click()
                            expect(page.locator("#ip-badge")).to_have_text("Modo ativo", timeout=15000)
                            project_id = "navegador_sintetico"
                            self.assertTrue((root / project_id).is_dir())
                            for field, value in PLAN.items():
                                page.locator(f"#ip-plan-{field}").fill(value)
                            page.locator('#ip-plan-form button[type="submit"]').click()
                            expect(page.locator("#ip-readiness")).to_contain_text("Direção preenchida")
                            self.assertEqual(publication.get_publication(root, project_id)["plan"], PLAN)
                            expect(page.locator("#ip-prepare-package")).to_be_disabled()
                            install_synthetic_master(root, project_id)
                            page.evaluate("() => refreshFilmProjectData()")
                            page.locator("summary", has_text="2. Preparar pacote").click()
                            page.locator("#ip-package-platform").select_option("threads")
                            hostile_title = "<img src=x onerror=window.__ip_xss=1> Chama na tempestade"
                            page.locator("#ip-package-title").fill(hostile_title)
                            expect(page.locator("#ip-prepare-package")).to_be_enabled()
                            page.locator("#ip-prepare-package").click()
                            expect(page.locator("#ip-packages a")).to_have_count(1, timeout=15000)
                            expect(page.locator("#ip-packages")).to_contain_text(hostile_title)
                            self.assertIsNone(page.evaluate("window.__ip_xss"))
                            self.assertEqual(page.locator("#ip-packages img").count(), 0)
                            with page.expect_download() as download_info:
                                page.locator("#ip-packages a").click()
                            download = download_info.value
                            downloaded = root / "download.zip"
                            download.save_as(downloaded)
                            self.assertGreater(downloaded.stat().st_size, 1000)
                            page.locator("summary", has_text="3. Registrar resultados").click()
                            saved = publication.get_publication(root, project_id)
                            page.locator("#ip-measurement-package").select_option(saved["packages"][0]["id"])
                            page.locator("#ip-post-url").fill("https://threads.com/@synthetic/post/local-fixture")
                            page.locator("#ip-metric-views").fill("1000")
                            page.locator("#ip-metric-eligibleStarts").fill("1000")
                            page.locator("#ip-metric-viewersAt3Seconds").fill("650")
                            page.locator("#ip-save-measurement").click()
                            expect(page.locator("#ip-result-summary")).to_contain_text("1 publicação(ões), 1 observação(ões)")
                            result = publication.get_publication(root, project_id)
                            self.assertIsNone(result["measurements"][0]["metrics"]["reach"])
                            self.assertEqual(result["measurements"][0]["rates"]["retainedAt3SecondsPercent"]["value"], 65)
                            page.locator("#film-internet-publication").screenshot(path=str(evidence / "internet-mode-desktop.png"))
                            page.locator("#ip-plan-opening").fill("Rascunho que deve resistir à atualização periódica.")
                            page.evaluate("() => refreshFilmProjectData()")
                            expect(page.locator("#ip-plan-opening")).to_have_value("Rascunho que deve resistir à atualização periódica.")
                            page.locator("#ip-refresh").click()
                            expect(page.locator("#ip-plan-opening")).to_have_value("Rascunho que deve resistir à atualização periódica.")
                            page.set_viewport_size({"width": 390, "height": 844})
                            page.locator("#film-internet-publication").scroll_into_view_if_needed()
                            page.screenshot(path=str(evidence / "internet-mode-mobile.png"))
                            overflow = page.locator("#film-internet-publication").evaluate("node => node.scrollWidth > node.clientWidth + 2")
                            self.assertFalse(overflow, "publication panel overflows on mobile")
                            self.assertFalse(any("generate" in item["path"] or "approve" in item["path"] for item in mutations))
                            self.assertEqual(errors, [], errors)
                            (evidence / "browser-validation.json").write_text(json.dumps({
                                "status": "PASS", "realStudioRoutes": True, "lifespanWorkers": False,
                                "syntheticMediaOnly": True, "desktop": "1440x1000", "mobile": "390x844",
                                "xssExecuted": False, "mobilePanelOverflow": overflow,
                                "pageErrors": errors, "mutations": mutations,
                                "packages": len(result["packages"]), "measurements": len(result["measurements"]),
                                "sourceSha256": result["packages"][0]["sourceSha256"],
                            }, ensure_ascii=False, indent=2), encoding="utf-8")
                        finally:
                            browser.close()
                finally:
                    server.should_exit = True
                    thread.join(timeout=10)
                    sock.close()
                    self.assertFalse(thread.is_alive(), "isolated server did not stop")


if __name__ == "__main__":
    unittest.main()
