"""Actual Chromium + isolated API; native conversion is an explicit identity fixture."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
import uuid

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import expect, sync_playwright
import numpy as np
import soundfile as sf
import uvicorn

from test_voice_conversion import fixture_completion, video_fixture
from voice_studio import VoiceStudio, create_voice_studio_router
from voice_studio_models import VoiceCreate
from voice_conversion import VoiceConversion, create_conversion_router
from voice_conversion_media import RATE, run

APP_ROOT = Path(__file__).resolve().parents[2] / 'app'
EVIDENCE = Path(__file__).resolve().parents[2] / 'dados/validation/voice_conversion_20261106'


class ConversionBrowserTests(unittest.TestCase):
    def test_upload_convert_compare_download_history_and_mobile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = VoiceStudio(root / 'library', comfy=lambda *args: {}, launcher=lambda _: None)
            library.capabilities = lambda: {'ready': True, 'message': 'test fixture'}
            voice_id = uuid.uuid4().hex; folder = library.root / 'voices' / voice_id; folder.mkdir(parents=True)
            ref = folder / 'source.wav'; sf.write(ref, np.sin(np.arange(RATE * 2) / 37) * .1, RATE)
            voice = library.register_voice(voice_id, VoiceCreate(name='Referência sintética de teste', transcript='Teste.', authorized=True), ref)
            converter = VoiceConversion(library, root / 'conversion', comfy=lambda *args: {})
            converter.capabilities = lambda: {'ready': True, 'message': 'test fixture', 'backgroundReady': True}
            converter.launcher = lambda job_id: fixture_completion(converter, job_id)
            mkv = root / 'guide.mkv'; video_fixture(mkv)
            video = root / 'guide.mp4'
            run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(mkv), '-c:v', 'copy', '-c:a', 'aac', str(video)])
            app = FastAPI(); app.include_router(create_voice_studio_router(library, lambda request: True), prefix='/api/studio')
            app.include_router(create_conversion_router(converter, lambda request: True), prefix='/api/studio')
            app.mount('/', StaticFiles(directory=APP_ROOT, html=True))
            sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(32)
            server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True); thread.start()
            for _ in range(100):
                if server.started: break
                time.sleep(.05)
            EVIDENCE.mkdir(parents=True, exist_ok=True)
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                    def intercept(route):
                        if '/api/studio/api/voice-' in route.request.url:
                            route.continue_()
                        else:
                            route.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'data': [], 'items': [], 'total': 0,
                                'services': {}, 'models': {'image': [], 'video': [], 'loras': [], 'qwen_edit': [], 'qwen': []}, 'defaults': {}, 'providers': {'audio': {}}}))
                    page.route('**/api/**', intercept)
                    page.goto(f'http://127.0.0.1:{sock.getsockname()[1]}/', wait_until='domcontentloaded')
                    page.locator('.nav-link[data-section="voices"]').click()
                    page.locator('#voice-tab-conversion').click()
                    expect(page.locator('#conversion-engine-status')).to_contain_text('Seed-VC')
                    page.locator('#conversion-file').set_input_files(str(video))
                    page.locator('#conversion-import').click()
                    expect(page.locator('#conversion-source-info')).to_contain_text('guide.mp4')
                    expect(page.locator('#conversion-source-video')).to_have_js_property('readyState', 4)
                    page.locator('#conversion-voice').select_option(voice['id'])
                    page.locator('#conversion-background').uncheck()
                    page.locator('#conversion-generate').click()
                    expect(page.locator('#conversion-result-status')).to_have_text('Pronto para ouvir e baixar')
                    self.assertEqual(converter.jobs()['total'], 1)
                    expect(page.locator('#conversion-result-body audio').first).to_have_js_property('readyState', 4)
                    with page.expect_download() as pending:
                        page.get_by_role('link', name='Baixar WAV sincronizado', exact=True).click()
                    path = pending.value.path()
                    data, rate = sf.read(path); self.assertEqual(len(data), 3 * RATE)
                    page.get_by_role('button', name='Ver vídeo com a nova voz', exact=True).click()
                    expect(page.locator('#conversion-source-video')).to_have_js_property('muted', True)
                    expect(page.locator('#conversion-result-body audio').first).to_have_js_property('paused', False)
                    for width in [1440, 1024, 768, 320]:
                        page.set_viewport_size({'width': width, 'height': 1000}); page.wait_for_timeout(80)
                        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - innerWidth'), 1, str(width))
                        if width <= 850:
                            source_box = page.locator('.conversion-source').bounding_box()
                            form_box = page.locator('#conversion-form').bounding_box()
                            self.assertLess(source_box['y'], form_box['y'])
                        page.screenshot(path=str(EVIDENCE / f'isolated-conversion-{width}.png'), full_page=True)
                    page.locator('#voice-tab-narration').click()
                    page.locator('#voice-tab-conversion').click()
                    expect(page.locator('#conversion-history .voice-history-row')).to_have_count(1)
                    # A fresh import must survive polling/refresh of old history.
                    second = root / 'new-guide.mp4'; second.write_bytes(video.read_bytes())
                    page.locator('#conversion-file').set_input_files(str(second))
                    page.locator('#conversion-import').click()
                    expect(page.locator('#conversion-source-info')).to_contain_text('new-guide.mp4')
                    expect(page.locator('#conversion-result')).to_be_hidden()
                    page.locator('#conversion-refresh').click()
                    expect(page.locator('#conversion-engine-status')).to_contain_text('Seed-VC')
                    expect(page.locator('#conversion-source-info')).to_contain_text('new-guide.mp4')
                    expect(page.locator('#conversion-result')).to_be_hidden()
                    self.assertEqual(errors, [])
                    browser.close()
            finally:
                server.should_exit = True; thread.join(timeout=10); sock.close()


if __name__ == '__main__':
    unittest.main()
