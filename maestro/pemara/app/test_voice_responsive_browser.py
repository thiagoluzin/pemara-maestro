from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import unittest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return


class VoiceResponsiveBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CHROME.is_file():
            raise unittest.SkipTest("Google Chrome nao esta instalado.")
        handler = partial(_QuietHandler, directory=str(APP_ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        options = Options()
        options.binary_location = str(CHROME)
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--use-fake-device-for-media-stream")
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--window-size=1440,900")
        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 15)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.driver.quit()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_voice_controls_and_responsive_layout(self) -> None:
        port = self.server.server_address[1]
        self.driver.get(f"http://127.0.0.1:{port}/index.html")
        self.wait.until(
            lambda driver: driver.execute_script(
                "return document.querySelectorAll('[data-voice-tools]').length"
            )
            >= 9
        )
        self.driver.execute_script(
            "document.querySelector('[data-section=gen]').click()"
        )
        self.wait.until(
            lambda driver: driver.find_element(By.ID, "section-gen").is_displayed()
        )

        screenshots = REPO_ROOT / ".trash" / "maestro-responsive-20260811"
        screenshots.mkdir(parents=True, exist_ok=True)
        results = []
        for width, height in (
            (320, 568),
            (390, 844),
            (768, 1024),
            (1024, 768),
            (1440, 900),
        ):
            self.driver.execute_cdp_cmd(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": width,
                    "height": height,
                    "screenWidth": width,
                    "screenHeight": height,
                    "deviceScaleFactor": 1,
                    "mobile": width < 768,
                },
            )
            time.sleep(0.15)
            metrics = self.driver.execute_script(
                """
                const prompt = document.getElementById('gen-prompt');
                const toolbar = prompt.nextElementSibling;
                const buttons = [...toolbar.querySelectorAll('button')];
                return {
                  viewport: [innerWidth, innerHeight],
                  overflowX: Math.max(
                    document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    document.body.scrollWidth - document.body.clientWidth
                  ),
                  toolbars: document.querySelectorAll('[data-voice-tools]').length,
                  duplicateIds: [...document.querySelectorAll('[id]')]
                    .map(element => element.id)
                    .filter((id, index, all) => all.indexOf(id) !== index),
                  promptVisible: !!(prompt.offsetWidth || prompt.offsetHeight),
                  toolbarVisible: !!(toolbar.offsetWidth || toolbar.offsetHeight),
                  buttonLabels: buttons.map(button => button.textContent.trim()),
                  buttonAria: buttons.map(button => button.getAttribute('aria-label')),
                  buttonSizes: buttons.map(button => [
                    Math.round(button.getBoundingClientRect().width),
                    Math.round(button.getBoundingClientRect().height)
                  ]),
                  describedByValid: [...document.querySelectorAll('textarea[data-voice-input]')]
                    .every(textarea => (textarea.getAttribute('aria-describedby') || '')
                      .split(/\s+/).filter(Boolean).every(id => document.getElementById(id))),
                  mediaDevices: !!navigator.mediaDevices?.getUserMedia,
                  mediaRecorder: typeof MediaRecorder === 'function'
                };
                """
            )
            results.append({"requested": [width, height], **metrics})
            self.driver.save_screenshot(str(screenshots / f"{width}x{height}.png"))
            if width <= 390:
                self.driver.execute_script(
                    "document.getElementById('gen-prompt').scrollIntoView({block: 'center'})"
                )
                time.sleep(0.1)
                self.driver.save_screenshot(
                    str(screenshots / f"{width}x{height}-voice-controls.png")
                )
                self.driver.execute_script("window.scrollTo(0, 0)")

            self.assertLessEqual(metrics["overflowX"], 1)
            self.assertEqual(metrics["toolbars"], 9)
            self.assertEqual(metrics["duplicateIds"], [])
            self.assertTrue(metrics["promptVisible"])
            self.assertTrue(metrics["toolbarVisible"])
            self.assertEqual(metrics["buttonLabels"], ["Falar", "Enviar áudio"])
            self.assertTrue(all(metrics["buttonAria"]))
            minimum_height = 44 if width <= 480 else 40
            self.assertTrue(all(size[1] >= minimum_height for size in metrics["buttonSizes"]))
            self.assertTrue(metrics["describedByValid"])
            self.assertTrue(metrics["mediaDevices"])
            self.assertTrue(metrics["mediaRecorder"])

        self.driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 390,
                "height": 844,
                "screenWidth": 390,
                "screenHeight": 844,
                "deviceScaleFactor": 1,
                "mobile": True,
            },
        )
        self.driver.execute_script(
            """
            window.fetch = async () => new Response(JSON.stringify({
              ok: true,
              transcription: {
                text: 'Texto ditado acessivel.',
                language: 'pt',
                engine: 'faster-whisper'
              },
              privacy: {stored: false, cloud: false}
            }), {status: 200, headers: {'Content-Type': 'application/json'}});
            const prompt = document.getElementById('gen-prompt');
            prompt.value = 'Inicio: ';
            prompt.focus();
            prompt.setSelectionRange(prompt.value.length, prompt.value.length);
            """
        )
        record = self.driver.find_element(
            By.CSS_SELECTOR,
            "#gen-prompt + [data-voice-tools] [data-voice-record]",
        )
        self.driver.execute_script("arguments[0].click()", record)
        self.wait.until(lambda _driver: record.text.strip() == "Parar")
        self.driver.execute_script("arguments[0].click()", record)
        self.wait.until(
            lambda driver: "Texto ditado acessivel."
            in driver.find_element(By.ID, "gen-prompt").get_attribute("value")
        )
        flow = self.driver.execute_script(
            """
            const prompt = document.getElementById('gen-prompt');
            const tools = prompt.nextElementSibling;
            return {
              value: prompt.value,
              status: tools.querySelector('[data-voice-status]').textContent,
              tone: tools.dataset.tone,
              pressed: tools.querySelector('[data-voice-record]').getAttribute('aria-pressed')
            };
            """
        )
        self.assertEqual(flow["value"], "Inicio: Texto ditado acessivel.")
        self.assertIn("não foi guardado", flow["status"])
        self.assertEqual(flow["tone"], "ok")
        self.assertEqual(flow["pressed"], "false")

        denied = self.driver.execute_script(
            """
            const tools = document.getElementById('gen-prompt').nextElementSibling;
            const record = tools.querySelector('[data-voice-record]');
            const upload = tools.querySelector('[data-voice-upload]');
            const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
            navigator.mediaDevices.getUserMedia = async () => {
              throw new DOMException('denied for regression test', 'NotAllowedError');
            };
            record.click();
            return new Promise((resolve) => setTimeout(() => {
              const result = {
                status: tools.querySelector('[data-voice-status]').textContent,
                tone: tools.dataset.tone,
                recordEnabled: !record.disabled,
                uploadEnabled: !upload.disabled,
              };
              navigator.mediaDevices.getUserMedia = original;
              resolve(result);
            }, 50));
            """
        )
        self.assertIn("Toque em Falar para tentar novamente", denied["status"])
        self.assertEqual(denied["tone"], "error")
        self.assertTrue(denied["recordEnabled"])
        self.assertTrue(denied["uploadEnabled"])
        print(json.dumps({"viewports": results, "dictationFlow": flow}, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
