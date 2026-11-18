"""Real browser + isolated API; external research is synthetic in this test."""
import hashlib
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright, expect

from public_research import ResearchService, create_research_router

APP_ROOT = Path(__file__).resolve().parents[2] / 'app'
EVIDENCE = Path(__file__).resolve().parents[2] / 'dados/validation/maestro_research_20261102'


def synthetic_result(folder):
    run = folder / 'run'
    (run / 'sources').mkdir(parents=True)
    content = '<img src=x onerror=window.__research_xss=1>\nPublic reference fixture.'
    (run / 'sources/S1.md').write_text(content, encoding='utf-8')
    report = {'approved': False, 'findings': [
        {'id': 'C1', 'text': 'Afirmação sustentada', 'status': 'SUPPORTED', 'checks': [{'sourceId': 'S1'}]},
        {'id': 'C2', 'text': 'Afirmação sem sustentação', 'status': 'UNSUPPORTED_OR_UNCERTAIN', 'checks': [{'sourceId': 'S1'}]}],
        'sources': [{'id': 'S1', 'url': 'https://docs.typesafe.ai/llms.txt', 'ok': True, 'fetchedAt': '2026-11-02T10:00:00Z',
                     'verificationEligible': True, 'markdownSha256': hashlib.sha256(content.encode()).hexdigest(),
                     'metadata': {'statusCode': 200, 'cacheState': 'hit'}}],
        'verification': {'model': 'synthetic-fixture', 'usage': {'input_tokens': 0, 'output_tokens': 0}}}
    (run / 'dossier.json').write_text(json.dumps(report), encoding='utf-8')
    (run / 'dossier.md').write_text('# Synthetic dossier', encoding='utf-8')
    manifest = {path.relative_to(run).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in run.rglob('*') if path.is_file()}
    (run / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


class BrowserTests(unittest.TestCase):
    def test_create_read_review_and_mobile_layout_without_network_or_media_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = ResearchService(root / 'research', projects_root=root / 'projects')
            service.launcher = lambda job_id: synthetic_result(service.root / job_id)
            project = root / 'projects/fixture-project'
            project.mkdir(parents=True)
            original = '{"status":"FINALIZED","title":"Projeto preservado"}'
            (project / 'project_manifest.json').write_text(original)
            app = FastAPI()
            router = create_research_router(service, lambda request: True)
            app.include_router(router, prefix='/api/studio')

            @app.get('/api/studio/api/video-projects')
            def projects():
                return {'data': [{'projectId': 'fixture-project', 'name': 'Projeto preservado'}]}

            app.mount('/', StaticFiles(directory=APP_ROOT, html=True), name='static')
            sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(32)
            port = sock.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True); thread.start()
            for _ in range(100):
                if server.started: break
                time.sleep(.05)
            EVIDENCE.mkdir(parents=True, exist_ok=True)
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                    def intercept(route):
                        if '/api/studio/api/research' in route.request.url or '/api/studio/api/video-projects' in route.request.url:
                            route.continue_()
                        else:
                            route.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'data': [], 'items': [], 'total': 0,
                                'services': {}, 'models': {'image': [], 'video': [], 'loras': [], 'qwen_edit': [], 'qwen': []}, 'defaults': {}, 'providers': {'audio': {}}}))
                    page.route('**/api/**', intercept)
                    page.goto(f'http://127.0.0.1:{port}/index.html', wait_until='domcontentloaded')
                    page.locator('.nav-link[data-section="research"]').click()
                    expect(page.locator('#research-project option[value="fixture-project"]')).to_have_count(1)
                    topic = '<img src=x onerror=window.__research_xss=1> Pesquisa pública'
                    page.locator('#research-topic').fill(topic)
                    page.locator('#research-project').select_option('fixture-project')
                    page.locator('#research-domains').fill('docs.typesafe.ai')
                    page.locator('#research-urls').fill('https://docs.typesafe.ai/llms.txt')
                    page.locator('#research-claims').fill('Afirmação sustentada\nAfirmação sem sustentação')
                    page.locator('#research-public-only').check()
                    page.locator('#research-submit').click()
                    expect(page.locator('#research-detail-status')).to_have_text('Pronta para revisão')
                    expect(page.locator('.research-job')).to_contain_text('Pronta para revisão')
                    self.assertIsNone(page.evaluate('window.__research_xss'))
                    self.assertEqual(page.locator('#research-detail img').count(), 0)
                    page.locator('#research-detail details summary').click()
                    expect(page.locator('#research-detail pre')).to_contain_text('<img src=x')
                    self.assertIsNone(page.evaluate('window.__research_xss'))
                    self.assertEqual(page.locator('select[data-claim-id="C2"] option[value="accept"]').count(), 0)
                    page.locator('select[data-claim-id="C1"]').select_option('accept')
                    page.locator('select[data-claim-id="C2"]').select_option('exclude')
                    page.locator('.research-review textarea').fill('Fonte sintética conferida no teste isolado.')
                    page.get_by_role('button', name='Concluir revisão', exact=True).click()
                    expect(page.locator('#research-message')).to_have_text('Revisão da pesquisa registrada.')
                    page.locator('#research-submit').click()
                    expect(page.locator('#research-message')).to_contain_text('Pesquisa registrada')
                    self.assertEqual(len(list(service.root.glob('*/record.json'))), 1)
                    for width in [1440, 390, 320]:
                        page.set_viewport_size({'width': width, 'height': 1000})
                        page.wait_for_timeout(80)
                        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - window.innerWidth'), 1)
                        self.assertLessEqual(page.locator('#research-public-only').bounding_box()['width'], 24)
                        self.assertGreater(page.locator('.research-public-check span').bounding_box()['width'], 100)
                        page.screenshot(path=str(EVIDENCE / f'isolated-research-{width}.png'), full_page=True)
                    self.assertEqual(errors, [])
                    self.assertEqual((project / 'project_manifest.json').read_text(), original)
                    browser.close()
            finally:
                server.should_exit = True; thread.join(timeout=10); sock.close()


if __name__ == '__main__':
    unittest.main()
