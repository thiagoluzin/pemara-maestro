"""Real Chromium against an isolated API; audio generation is a silence fixture."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import expect, sync_playwright
import uvicorn

from test_voice_studio import completed_fixture, wav_bytes
from voice_studio import VoiceStudio, create_voice_studio_router

APP_ROOT = Path(__file__).resolve().parents[2] / 'app'
EVIDENCE = Path(__file__).resolve().parents[2] / 'dados/validation/voice_studio_20261105'


class BrowserTests(unittest.TestCase):
    def test_narration_voice_clone_history_download_and_responsive_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = VoiceStudio(root / 'studio', comfy=lambda *args: {})
            service.capabilities = lambda: {'ready': True, 'message': 'Synthetic test engine', 'engine': 'synthetic-test-fixture'}
            service.launcher = lambda job_id: completed_fixture(service, job_id)
            app = FastAPI(); app.include_router(create_voice_studio_router(service, lambda request: True), prefix='/api/studio')
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
                    page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                    errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                    console_errors = []
                    page.on('console', lambda entry: console_errors.append(entry.text) if entry.type in ('error', 'warning') else None)
                    def intercept(route):
                        if '/api/studio/api/voice-studio' in route.request.url:
                            route.continue_()
                        else:
                            route.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'data': [], 'items': [], 'total': 0,
                                'services': {}, 'models': {'image': [], 'video': [], 'loras': [], 'qwen_edit': [], 'qwen': []}, 'defaults': {}, 'providers': {'audio': {}}}))
                    page.route('**/api/**', intercept)
                    page.goto(f'http://127.0.0.1:{sock.getsockname()[1]}/index.html', wait_until='domcontentloaded')
                    page.locator('.nav-link[data-section="voices"]').click()
                    expect(page.locator('#voice-engine-status')).to_contain_text('Drama 3')
                    expect(page.locator('#voice-generate')).to_be_enabled()
                    page.screenshot(path=str(EVIDENCE / 'studio-empty-desktop.png'), full_page=True)
                    page.locator('#voice-add-shortcut').click()
                    name = '<img src=x onerror=window.__voice_xss=1> Minha voz'
                    page.locator('#voice-clone-name').fill(name)
                    page.locator('#voice-clone-description').fill('Referência sintética de teste, não é clonagem real.')
                    page.locator('#voice-clone-transcript').fill('Transcrição sintética para teste de cadastro.')
                    page.locator('#voice-clone-audio').set_input_files({'name': 'fixture.wav', 'mimeType': 'audio/wav', 'buffer': wav_bytes()})
                    page.locator('#voice-clone-authorized').check()
                    page.locator('#voice-clone-save').click()
                    expect(page.locator('#voice-clone-dialog')).not_to_be_visible()
                    expect(page.locator('#voice-select option:checked')).to_have_text(name)
                    page.locator('#voice-title').fill('Narração de teste')
                    text = 'Este roteiro verifica o fluxo do estúdio. A geração deste teste é um arquivo sintético.'
                    page.locator('#voice-text').fill(text)
                    page.locator('#voice-mode').select_option('chunked')
                    page.locator('#voice-budget').select_option('16384')
                    page.locator('#voice-generate').click()
                    expect(page.locator('#voice-current-status')).to_have_text('Pronta para ouvir')
                    self.assertEqual(len(service.jobs()['jobs']), 1)
                    record = service.jobs()['jobs'][0]
                    self.assertEqual(record['settings']['mode'], 'chunked')
                    self.assertTrue(record['settings']['voiceId'])
                    expect(page.locator('#voice-current audio')).to_have_js_property('readyState', 4)
                    with page.expect_download() as download:
                        page.get_by_role('link', name='Baixar WAV', exact=True).click()
                    download_path = download.value.path()
                    self.assertEqual(Path(download_path).read_bytes(), wav_bytes())
                    page.get_by_role('button', name='Aprovar esta versão', exact=True).click()
                    expect(page.locator('#voice-current-body')).to_contain_text('aprovada por você')
                    self.assertEqual(service.get(record['id'])['review']['decision'], 'approved')
                    page.get_by_role('tab', name='Histórico', exact=True).click()
                    expect(page.locator('.voice-history-row')).to_have_count(1)
                    page.locator('.voice-history-row').click()
                    page.get_by_role('button', name='Editar como nova versão', exact=True).click()
                    expect(page.locator('#voice-text')).to_have_value(text)
                    self.assertEqual(len(service.jobs()['jobs']), 1, 'Editing must not synthesize')
                    for width in [1440, 1024, 768, 320]:
                        page.set_viewport_size({'width': width, 'height': 1100})
                        page.wait_for_timeout(100)
                        overflow = page.evaluate('document.documentElement.scrollWidth - innerWidth')
                        self.assertLessEqual(overflow, 1, f'Overflow at {width}: {overflow}')
                        page.screenshot(path=str(EVIDENCE / f'isolated-narration-{width}.png'), full_page=True)
                    page.get_by_role('tab', name='Minhas vozes').click()
                    expect(page.locator('.voice-library-card')).to_have_count(1)
                    self.assertEqual(page.locator('.voice-library-card img').count(), 0)
                    self.assertIsNone(page.evaluate('window.__voice_xss'))
                    page.locator('#voice-search').fill('inexistente')
                    expect(page.locator('#voice-library-list')).to_contain_text('Nenhuma voz encontrada')
                    page.locator('#voice-search').fill('')
                    page.get_by_role('button', name='Usar esta voz', exact=True).click()
                    page.locator('#voice-tab-narration').focus(); page.keyboard.press('ArrowRight')
                    expect(page.locator('#voice-tab-conversion')).to_have_attribute('aria-selected', 'true')
                    page.keyboard.press('ArrowRight')
                    expect(page.locator('#voice-tab-library')).to_have_attribute('aria-selected', 'true')
                    self.assertEqual(errors, [])
                    self.assertEqual(console_errors, [])
                    browser.close()
            finally:
                server.should_exit = True; thread.join(timeout=10); sock.close()


if __name__ == '__main__':
    unittest.main()
