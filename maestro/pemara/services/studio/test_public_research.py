import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from public_research import ResearchService, create_research_router


def payload(request_id='a' * 32):
    return {'requestId': request_id, 'topic': 'Documentação pública', 'publicOnly': True,
            'allowedDomains': ['docs.typesafe.ai'], 'urls': ['https://docs.typesafe.ai/llms.txt'],
            'claims': [{'id': 'C1', 'text': 'O serviço retorna respostas estruturadas.'}]}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.launched = []
        self.service = ResearchService(self.root / 'research', launcher=lambda job_id: self.launched.append(job_id),
                                       projects_root=self.root / 'projects')
        app = FastAPI()
        app.include_router(create_research_router(self.service, lambda request: request.headers.get('x-test-auth') == 'owner'))
        self.client = TestClient(app)
        self.headers = {'x-test-auth': 'owner'}

    def tearDown(self):
        self.temp.cleanup()

    def create(self, data=None):
        return self.client.post('/api/research/jobs', json=data or payload(), headers=self.headers)

    def finish(self, job_id='a' * 32):
        import hashlib
        run = self.service.root / job_id / 'run'
        (run / 'sources').mkdir(parents=True)
        source = '# Public fixture\nTypeSafe returns structured answers.'
        (run / 'sources/S1.md').write_text(source, encoding='utf-8')
        report = {'approved': False, 'findings': [
            {'id': f'C{i}', 'text': 'Public fixture claim', 'status': 'SUPPORTED' if i == 1 else 'UNSUPPORTED_OR_UNCERTAIN', 'checks': []} for i in range(1, 5)],
            'sources': [{'id': 'S1', 'url': 'https://docs.typesafe.ai/llms.txt', 'ok': True, 'metadata': {'statusCode': 200}}]}
        (run / 'dossier.json').write_text(json.dumps(report), encoding='utf-8')
        (run / 'dossier.md').write_text('# Fixture dossier', encoding='utf-8')
        manifest = {path.relative_to(run).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in run.rglob('*') if path.is_file()}
        (run / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return self.client.get(f'/api/research/jobs/{job_id}', headers=self.headers)

    def test_auth_required_for_every_read_and_write(self):
        for method, path in [('get', '/api/research/jobs'), ('post', '/api/research/jobs'),
                             ('get', '/api/research/jobs/' + 'a' * 32),
                             ('get', '/api/research/jobs/' + 'a' * 32 + '/dossier'),
                             ('get', '/api/research/jobs/' + 'a' * 32 + '/sources/S1'),
                             ('post', '/api/research/jobs/' + 'a' * 32 + '/reviews')]:
            self.assertEqual(getattr(self.client, method)(path, json={} if method == 'post' else None).status_code
                             if method == 'post' else self.client.get(path).status_code, 403)
        self.assertEqual(self.launched, [])

    def test_idempotency_and_concurrency_do_not_start_duplicate_paid_calls(self):
        first = self.create(); self.assertEqual(first.status_code, 202, first.text)
        self.assertEqual(self.create().status_code, 202)
        self.assertEqual(len(self.launched), 1)
        changed = payload(); changed['topic'] = 'Outro assunto'
        self.assertEqual(self.create(changed).status_code, 409)
        self.assertEqual(self.create(payload('b' * 32)).status_code, 409)

    def test_private_url_mass_assignment_and_character_version_are_validated(self):
        invalid = [dict(payload(), publicOnly=False), dict(payload(), urls=['https://127.0.0.1']),
                   dict(payload(), output='C:/private'), dict(payload(), maxSources=99),
                   dict(payload(), reference={'kind': 'character', 'work': 'Game', 'edition': '', 'incarnation': ''}),
                   dict(payload(), projectId='../secret')]
        for body in invalid:
            self.assertEqual(self.create(body).status_code, 422, body)
        self.assertEqual(self.launched, [])

    def test_project_link_is_validated_without_modifying_the_project(self):
        project = self.root / 'projects' / 'example'
        project.mkdir(parents=True)
        (project / 'project.json').write_text('{"status":"finalized"}')
        data = dict(payload(), projectId='example')
        self.assertEqual(self.create(data).status_code, 202)
        self.assertEqual((project / 'project.json').read_text(), '{"status":"finalized"}')

    def test_harness_receipt_and_sources_are_visible_without_exposing_machine_paths(self):
        self.create()
        response = self.finish(); self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['status'], 'READY_FOR_REVIEW')
        self.assertEqual(data['integrity'], 'ok')
        self.assertEqual(len(data['findings']), 4)
        self.assertNotIn('E:\\Pemara', response.text)
        source = self.client.get('/api/research/jobs/' + 'a' * 32 + '/sources/S1', headers=self.headers)
        self.assertEqual(source.status_code, 200)
        self.assertTrue(source.headers['content-type'].startswith('text/plain'))
        denied = self.client.get('/api/research/jobs/' + 'a' * 32 + '/sources/verification-request', headers=self.headers)
        self.assertIn(denied.status_code, [404, 422])

    def test_review_cannot_accept_unsubstantiated_claims_or_approve_media(self):
        self.create(); self.finish()
        base = '/api/research/jobs/' + 'a' * 32 + '/reviews'
        invalid = {'requestId': 'c' * 32, 'decision': 'reviewed', 'acceptedClaimIds': ['C1', 'C2', 'C3', 'C4'], 'excludedClaimIds': [], 'note': 'Reviewed'}
        self.assertEqual(self.client.post(base, json=invalid, headers=self.headers).status_code, 422)
        valid = dict(invalid, acceptedClaimIds=['C1'], excludedClaimIds=['C2', 'C3', 'C4'])
        response = self.client.post(base, json=valid, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['review']['decision'], 'reviewed')
        dossier = json.loads((self.service.root / ('a' * 32) / 'run' / 'dossier.json').read_text(encoding='utf-8'))
        self.assertFalse(dossier['approved'])
        self.assertEqual(self.client.post(base, json=valid, headers=self.headers).status_code, 201)
        self.assertEqual(len(list((self.service.root / ('a' * 32) / 'reviews').glob('*.json'))), 1)

    def test_source_tampering_blocks_review(self):
        self.create(); self.finish()
        (self.service.root / ('a' * 32) / 'run' / 'sources' / 'S1.md').write_text('changed')
        data = self.client.get('/api/research/jobs/' + 'a' * 32, headers=self.headers).json()
        self.assertEqual(data['integrity'], 'changed')
        self.assertEqual(self.client.post('/api/research/jobs/' + 'a' * 32 + '/reviews',
                         json={'requestId': 'd' * 32, 'decision': 'needs_sources', 'note': 'Needs review'}, headers=self.headers).status_code, 409)

    def test_existing_jobs_survive_new_service_instance_without_relaunch(self):
        self.create(); self.finish()
        recovered = ResearchService(self.service.root, launcher=lambda _: self.fail('must not relaunch'))
        self.assertEqual(recovered.get('a' * 32)['status'], 'READY_FOR_REVIEW')

    def test_body_limit_content_type_and_forged_authority_do_not_queue(self):
        self.assertEqual(self.client.post('/api/research/jobs', content='x' * 40000,
                         headers=self.headers | {'content-type': 'application/json'}).status_code, 413)
        self.assertEqual(self.client.post('/api/research/jobs', content='{}',
                         headers=self.headers | {'content-type': 'text/plain'}).status_code, 415)
        self.assertEqual(self.create(dict(payload(), approved=True, role='admin')).status_code, 422)
        self.assertEqual(self.launched, [])

    def test_production_auth_and_origin_guard_protect_the_new_router(self):
        # Compile only the real boundary helpers. Do not import main/start its
        # media services or GPU-related initialization for an authorization test.
        import ast
        import hmac
        import os
        import urllib.parse
        from fastapi import Request
        from fastapi.responses import JSONResponse
        names = {'_allowed_origins', '_canonical_browser_origin', '_browser_origin_allowed',
                 '_internal_token', '_public_studio_hosts', '_request_hosts', '_is_internal_request'}
        tree = ast.parse((Path(__file__).parent / 'main.py').read_text(encoding='utf-8-sig'))
        functions = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
        namespace = {'os': os, 'urllib': __import__('urllib'), 'hmac': hmac, 'Request': Request, 'List': list,
                     '_env_value': lambda key: 'unit-test-internal-token' if key == 'STUDIO_INTERNAL_TOKEN' else ''}
        exec(compile(functions, 'production-boundary-helpers', 'exec'), namespace)
        app = FastAPI()
        @app.middleware('http')
        async def guard(request, call_next):
            if not namespace['_is_internal_request'](request) or not namespace['_browser_origin_allowed'](request):
                return JSONResponse({'detail': 'Forbidden'}, status_code=403)
            return await call_next(request)
        app.include_router(create_research_router(self.service, namespace['_is_internal_request']))
        client = TestClient(app)
        good = {'x-studio-internal-token': 'unit-test-internal-token', 'origin': 'http://127.0.0.1:9501'}
        self.assertEqual(client.get('/api/research/jobs', headers=good).status_code, 200)
        self.assertEqual(client.get('/api/research/jobs', headers=good | {'origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(client.get('/api/research/jobs', headers={'x-forwarded-host': 'localhost', 'role': 'admin'}).status_code, 403)
        self.assertEqual(client.get('/api/research/jobs', headers={'x-studio-internal-token': 'unit-test-internal-token', 'sec-fetch-site': 'cross-site'}).status_code, 403)

    def test_worker_passes_only_fixed_argv_and_never_a_shell_or_gateway_secret(self):
        self.create(dict(payload(), topic='Public input ; echo injected'))
        from unittest.mock import MagicMock
        child = MagicMock(pid=123456, returncode=1)
        child.poll.return_value = 1
        with patch('public_research.subprocess.Popen', return_value=child) as launch, patch.dict('os.environ', {'STUDIO_INTERNAL_TOKEN': 'unit-test-only'}):
            self.service._run('a' * 32)
        args, kwargs = launch.call_args
        self.assertNotIn('Public input', ' '.join(args[0]))
        self.assertEqual(kwargs['shell'], False)
        self.assertNotIn('STUDIO_INTERNAL_TOKEN', kwargs['env'])
        self.assertEqual(self.service.get('a' * 32)['status'], 'INTERRUPTED_REVIEW_REQUIRED')


if __name__ == '__main__':
    unittest.main()
