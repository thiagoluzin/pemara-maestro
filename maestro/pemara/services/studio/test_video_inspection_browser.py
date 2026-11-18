"""Isolated headless UI test; no external inference and no production writes."""
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright, expect

from editor_suite import EditorSuite
from test_video_inspection import FakeDecision, InspectionTests
from video_inspection import InspectionService, Explanations, create_inspection_router

APP = Path(__file__).resolve().parents[2] / "app"
EVIDENCE = APP.parents[2] / "evidencias-inspecao"


class InspectionBrowserTest(unittest.TestCase):
    def test_upload_triage_marker_seek_codex_explanation_and_mobile(self):
        InspectionTests.setUpClass()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                fake = FakeDecision()
                service = InspectionService(EditorSuite(Path(tmp) / "editor_suite"), decision=fake)
                app = FastAPI()
                app.include_router(create_inspection_router(service, lambda r: True), prefix="/api/studio")
                html = (APP / "index.html").read_text(encoding="utf-8")
                section = html[html.index('      <section class="section" id="section-inspection"'):html.index('      <section class="section" id="section-hyperframes"')]
                @app.get("/")
                def home():
                    return HTMLResponse('<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/assets/video-inspection.css">'
                        '<style>body{background:#101820;color:#eee;font:16px Arial;padding:16px}*{box-sizing:border-box}.panel{padding:16px}.section{display:none}.section.active{display:block}button{min-height:35px}</style>'
                        '<button id="open" onclick="document.getElementById(\'section-inspection\').classList.add(\'active\')">Inspeção</button>' + section + '<script src="/assets/video-inspection.js"></script>')
                app.mount("/assets", StaticFiles(directory=APP / "assets"))
                sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen(16)
                port = sock.getsockname()[1]
                server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
                thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True); thread.start()
                for _ in range(100):
                    if server.started: break
                    time.sleep(.05)
                errors = []
                try:
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(channel='msedge', headless=True)
                        page = browser.new_page(viewport={"width": 1400, "height": 1000})
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        page.goto(f"http://127.0.0.1:{port}")
                        page.click("#open")
                        expect(page.locator("#inspection-connection")).to_contain_text("configurado")
                        page.locator("#inspection-file").set_input_files(str(InspectionTests.source))
                        page.select_option("#inspection-kind", "animation")
                        page.fill("#inspection-context", "Animação sintética para testar fluxo, sem publicação.")
                        endpoint = "**/api/video-inspection/jobs"
                        submissions = []
                        def lose_response(route):
                            if route.request.method != "POST" or submissions:
                                return route.continue_()
                            response = route.fetch()
                            submissions.append(response.status)
                            route.abort()
                        page.route(endpoint, lose_response)
                        page.click("#inspection-submit")
                        expect(page.locator("#inspection-submit")).to_be_enabled(timeout=20000)
                        self.assertEqual(len(submissions), 1)
                        self.assertEqual(submissions, [202], page.locator("#inspection-message").inner_text())
                        self.assertTrue(page.evaluate("Boolean(sessionStorage.getItem('pemara.inspection.pending'))"))
                        page.reload()
                        page.click("#open")
                        page.click("#inspection-submit")
                        expect(page.locator("#inspection-submit")).to_be_enabled(timeout=10000)

                        expect(page.locator("#inspection-status")).to_contain_text("aguardando explicação", timeout=20000)
                        expect(page.locator(".inspection-marker")).to_have_count(4)
                        page.locator(".inspection-track").filter(has_text="Continuidade").locator("button").last.click()
                        expect(page.locator("#inspection-marker-detail")).to_contain_text("Aguardando investigação")
                        page.wait_for_function("Math.abs(document.getElementById('inspection-video').currentTime-1.75)<.05")
                        record = service.read(service.list()[0]["id"])
                        selected = next(m for m in record["markers"] if m["category"] == "continuity" and m["windowIndex"] == 1)
                        service.explain(record["id"], Explanations(sourceSha256=record["sourceSha256"], evidenceSha256=record["evidenceSha256"],
                            explanations=[{"markerId": selected["id"], "verdict": "false_positive", "observed": "Nada comprovado na amostra.",
                                           "hypothesis": "Hipótese apenas.", "correction": "Preservar a fonte.", "frameIndices": selected["frameIndices"]}]))
                        page.evaluate("document.getElementById('inspection-video').currentTime = 2.1")
                        page.click("#inspection-refresh")
                        expect(page.locator("#inspection-marker-detail")).to_contain_text("Falso positivo segundo o Codex")
                        self.assertAlmostEqual(page.evaluate("document.getElementById('inspection-video').currentTime"), 2.1, places=1)
                        self.assertEqual(len(service.list()), 1)
                        self.assertIsNone(page.evaluate("sessionStorage.getItem('pemara.inspection.pending')"))
                        self.assertEqual(page.locator("#inspection-marker-detail img").count(), 0)
                        EVIDENCE.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(EVIDENCE / "desktop.png"), full_page=True)
                        page.set_viewport_size({"width": 390, "height": 844})
                        page.screenshot(path=str(EVIDENCE / "mobile.png"), full_page=True)
                        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                        self.assertEqual(fake.calls, 2)
                        self.assertFalse(errors, errors)
                        (EVIDENCE / "result.json").write_text(json.dumps({"ok": True, "headless": True, "externalCalls": 0,
                            "markers": 4, "seekVerified": True, "explanationVerified": True, "retryKeptSingleJob": True, "playbackPreserved": True, "mobileOverflow": False}), encoding="utf-8")
                        browser.close()
                finally:
                    server.should_exit = True; thread.join(timeout=5)
        finally:
            InspectionTests.tearDownClass()


if __name__ == "__main__": unittest.main()

