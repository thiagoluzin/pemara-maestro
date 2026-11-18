"""Isolated browser smoke for the visible H3 workflow panel."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - portable restore may install it later
    sync_playwright = None


class H3WorkflowBrowserTest(unittest.TestCase):
    @unittest.skipIf(sync_playwright is None, "playwright is not installed")
    def test_direct_video_keeps_production_reference_collapsed(self):
        root = Path(__file__).resolve().parents[2]
        evidence = Path(r"E:\Pemara\logs\maestro_h3_workflow_20260816")
        evidence.mkdir(parents=True, exist_ok=True)
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8099", "--bind", "127.0.0.1", "--directory", str(root / "app")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            time.sleep(0.5)
            workflow = {
                "ok": True,
                "productionReady": True,
                "capabilities": {"masterCacheReady": True, "masterSpectrumReady": True, "fastH3OmniReady": True},
                "enginePolicy": "minimax_h3_only",
                "videoEngine": "MiniMax H3",
                "catalog": {"installedSkills": 300, "installedProfiles": 35},
                "stages": [
                    {"label": f"Etapa {index:02d}", "output": "Saida validada", "gate": "human_or_technical_gate"}
                    for index in range(1, 11)
                ],
            }
            status = {
                "ok": True,
                "comfy_online": True,
                "models": {
                    "image": [],
                    "video": ["minimax_h3_fl2va_pruned_int8_convrot.safetensors"],
                    "loras": [],
                    "qwen_edit": [],
                    "qwen": [],
                },
                "defaults": {
                    "video_model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                    "minimax_h3_native_audio_default": True,
                    "minimax_h3_text_to_video": True,
                    "minimax_h3_native_fps": 24,
                    "minimax_h3_max_duration": 15,
                    "minimax_h3_temporal_stride": 17,
                    "minimax_h3_temporal_offset": 5,
                    "minimax_h3_min_frames": 124,
                    "minimax_h3_max_frames": 362,
                },
                "providers": {"audio": {}},
                "videoEngines": {
                    "engines": [
                        {
                            "id": "minimax_h3",
                            "display_name": "MiniMax H3",
                            "selectable": True,
                            "readiness": {
                                "state": "READY",
                                "production_ready": True,
                                "message": "Pronto para produção",
                            },
                        }
                    ]
                },
                "h3Workflow": workflow,
            }
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                console_issues: list[str] = []
                page.on(
                    "console",
                    lambda message: console_issues.append(f"{message.type}: {message.text}")
                    if message.type in {"error", "warning"}
                    else None,
                )

                def route_api(route):
                    payload = status if route.request.url.endswith("/api/generative/status") else {
                        "ok": True,
                        "items": [],
                        "data": [],
                        "total": 0,
                        "services": {},
                    }
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

                page.route("**/api/**", route_api)
                page.goto("http://127.0.0.1:8099/index.html", wait_until="networkidle")
                page.locator('.nav-link[data-section="gen"]').click()
                page.locator('[data-gen-mode="video"]').click()
                page.locator('[data-video-engine-id="minimax_h3"]').click()
                panel = page.locator("#gen-h3-workflow")
                self.assertTrue(panel.is_visible())
                self.assertEqual(page.locator("#gen-h3-workflow-state").inner_text(), "Disponível")
                self.assertFalse(page.locator("#gen-h3-workflow-stages").is_visible())
                panel.locator("summary").click()
                self.assertEqual(page.locator("#gen-h3-workflow-stages li").count(), 10)
                page.locator("#gen-settings > summary").click()
                self.assertEqual(page.locator("#gen-h3-quality-profile").input_value(), "h3_production")
                page.locator("#gen-h3-quality-profile").select_option("h3_master")
                self.assertEqual(page.locator("#gen-steps").input_value(), "20")
                self.assertEqual(page.locator("#gen-width").input_value(), "1344")
                self.assertEqual(page.locator("#gen-height").input_value(), "768")
                self.assertTrue(page.locator("#gen-h3-sage-status").is_visible())
                self.assertIn("SageAttention + Spectrum", page.locator("#gen-h3-sage-status").inner_text())
                self.assertEqual(page.locator("#gen-h3-quality-profile option[value='h3_master_fbc20']").count(), 0)
                self.assertEqual(page.locator("#gen-h3-quality-profile option[value='h3_master_spectrum20']").count(), 0)
                page.locator("#gen-h3-quality-profile").select_option("h3_production")
                self.assertFalse(page.locator("#gen-h3-cache-help").is_visible())
                self.assertEqual(page.locator("#gen-steps").input_value(), "10")
                page.locator("#gen-h3-model-variant").select_option("fasth3_omni_8step_v1")
                self.assertEqual(page.locator("#gen-steps").input_value(), "8")
                self.assertTrue(page.locator("#gen-steps").is_disabled())
                self.assertIn("não fixa o primeiro quadro", page.locator("#gen-h3-variant-help").inner_text())
                page.locator("#gen-h3-model-variant").select_option("base")
                self.assertEqual(page.locator("#gen-steps").input_value(), "10")
                page.screenshot(path=str(evidence / "painel_h3_workflow.png"), full_page=True)
                (evidence / "browser_console.json").write_text(
                    json.dumps(console_issues, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                self.assertEqual(console_issues, [])
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
