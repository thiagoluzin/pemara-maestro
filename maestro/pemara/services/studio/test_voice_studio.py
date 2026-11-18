"""Isolated persistence/API/queue tests. No model execution or cloud access."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
import wave

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from voice_studio import VoiceStudio, create_voice_studio_router, digest, write_json
from voice_studio_models import NarrationCreate, ReviewCreate
from unittest.mock import Mock


def wav_bytes(seconds=2):
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(44100)
        audio.writeframes(b'\0\0' * int(44100 * seconds))
    return stream.getvalue()


def completed_fixture(service, job_id):
    """Explicit synthetic silence fixture; never an assertion of real synthesis."""
    folder = service.folder(job_id)
    (folder / 'speech.wav').write_bytes(wav_bytes())
    write_json(folder / 'result.json', {'requestSha256': digest(folder / 'request.json'), 'wavSha256': digest(folder / 'speech.wav'),
               'metrics': {'complete': True, 'finish_reason': 'eos'}, 'duration': 2., 'sampleRate': 44100,
               'engine': 'synthetic-test-fixture', 'networkGeneration': False})


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.calls, self.launches = [], []
        self.service = VoiceStudio(self.root, comfy=self.comfy, launcher=self.launches.append)
        app = FastAPI(); app.include_router(create_voice_studio_router(self.service, lambda request: request.headers.get('X-Test-Auth') == 'yes'))
        self.client = TestClient(app); self.headers = {'X-Test-Auth': 'yes'}

    def tearDown(self):
        self.client.close(); self.temp.cleanup()

    def comfy(self, path, payload=None):
        self.calls.append((path, payload))
        if path.startswith('/object_info'):
            return {'PemaraDrama3Studio': {}}
        return {'queue_running': [], 'queue_pending': []}

    def body(self, **kwargs):
        return {'requestId': uuid.uuid4().hex, 'title': 'Minha narração', 'text': 'Uma história inteira, com a minha voz.', **kwargs}

    def create(self, **kwargs):
        return self.service.create(NarrationCreate(**self.body(**kwargs)))

    def test_authenticated_routes_and_no_credential_or_reference_path_export(self):
        for path in ['/status', '/voices', '/jobs', '/jobs/' + 'a' * 32 + '/recipe']:
            self.assertEqual(self.client.get('/api/voice-studio' + path).status_code, 403)
        self.assertEqual(self.client.post('/api/voice-studio/jobs', json=self.body()).status_code, 403)

    def test_idempotence_and_conflicting_payload(self):
        payload = self.body(); first = self.service.create(NarrationCreate(**payload))
        second = self.service.create(NarrationCreate(**payload))
        self.assertEqual(first['id'], second['id']); self.assertEqual(len(self.launches), 1)
        with self.assertRaises(HTTPException) as conflict:
            self.service.create(NarrationCreate(**(payload | {'text': 'Outro texto'})))
        self.assertEqual(conflict.exception.status_code, 409)
        with self.assertRaises(HTTPException): self.create()

    def test_reference_upload_transcript_authorization_and_immutable_snapshot(self):
        metadata = {'name': 'Minha voz', 'transcript': 'O que eu falei.', 'description': 'pt-BR', 'authorized': True}
        response = self.client.post('/api/voice-studio/voices', headers=self.headers,
                    files={'audio': ('minha.wav', wav_bytes(), 'audio/wav')}, data={'metadata': json.dumps(metadata)})
        self.assertEqual(response.status_code, 201, response.text)
        voice = response.json(); folder = self.root / 'voices' / voice['id']
        self.assertEqual((folder / 'source.wav').read_bytes(), wav_bytes())
        self.assertEqual(voice['transcript'], metadata['transcript'])
        job = self.create(voiceId=voice['id']); request = json.loads((self.service.folder(job['id']) / 'request.json').read_text(encoding='utf-8'))
        self.assertEqual(request['reference']['sha256'], voice['sha256'])
        self.assertTrue(request['reference']['authorized'])
        self.assertEqual(digest(self.service.folder(job['id']) / 'reference.wav'), voice['sha256'])
        (folder / 'reference.wav').write_bytes(b'altered')
        self.assertEqual(self.client.get('/api/voice-studio/voices/' + voice['id'] + '/audio', headers=self.headers).status_code, 409)

    def test_upload_refuses_missing_consent_and_corrupt_or_overlong_audio(self):
        for consent, content in [(False, wav_bytes()), (True, b'not audio'), (True, wav_bytes(61))]:
            response = self.client.post('/api/voice-studio/voices', headers=self.headers,
                        files={'audio': ('ref.wav', content, 'audio/wav')}, data={'metadata': json.dumps({'name': 'Voz', 'transcript': 'Olá.', 'authorized': consent})})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.service.voices(), [])

    def test_full_output_integrity_review_history_and_download(self):
        job = self.create(); completed_fixture(self.service, job['id'])
        ready = self.service.get(job['id']); self.assertEqual(ready['status'], 'COMPLETED')
        review = self.service.review(job['id'], ReviewCreate(decision='rejected', note='Revisão sintética'))
        self.assertEqual(review['review']['decision'], 'rejected')
        url = '/api/voice-studio/jobs/' + job['id']
        self.assertEqual(self.client.get(url + '/audio/wav', headers=self.headers).content, wav_bytes())
        recipe = self.client.get(url + '/recipe', headers=self.headers).text
        self.assertNotIn(str(self.root), recipe); self.assertNotIn('reference.wav', recipe)
        (self.service.folder(job['id']) / 'speech.wav').write_bytes(b'altered')
        self.assertEqual(self.service.get(job['id'])['status'], 'INTEGRITY_ERROR')
        self.assertEqual(self.client.get(url + '/audio/wav', headers=self.headers).status_code, 404)

    def test_incomplete_audio_is_not_delivered(self):
        job = self.create(); completed_fixture(self.service, job['id'])
        result_path = self.service.folder(job['id']) / 'result.json'; result = json.loads(result_path.read_text())
        result['metrics']['complete'] = False; write_json(result_path, result)
        self.assertEqual(self.service.get(job['id'])['status'], 'INTEGRITY_ERROR')

    def test_only_own_pending_prompt_cancelled_no_global_interrupt(self):
        job = self.create(); record = self.service.raw(job['id']); record['promptId'] = 'my-own-prompt'; self.service._save(record)
        self.service.cancel(job['id'])
        self.assertTrue((self.service.folder(job['id']) / 'cancel.flag').exists())
        self.assertIn(('/queue', {'delete': ['my-own-prompt']}), self.calls)
        self.assertFalse(any('/interrupt' in path for path, _ in self.calls))

    def test_recovery_never_resubmits_unknown_or_known_prompt(self):
        job = self.create(); self.launches.clear()
        self.service.recover(); self.assertEqual(self.service.raw(job['id'])['status'], 'INTERRUPTED'); self.assertEqual(self.launches, [])
        record = self.service.raw(job['id']); record.update(status='SUBMITTING'); self.service._save(record)
        self.service.recover(); self.assertEqual(self.service.raw(job['id'])['status'], 'SUBMISSION_UNCERTAIN')
        self.assertEqual(self.launches, [])
        self.service.cancel(job['id']); self.assertEqual(self.service.get(job['id'])['status'], 'CANCELLED')

    def test_bounded_inputs_and_paths(self):
        for changes in [{'text': ' '}, {'mode': 'single', 'maxFrames': 16384}, {'temperature': float('nan')}, {'seed': True}, {'voiceId': '../file'}, {'unknown': 'ignored?'}]:
            response = self.client.post('/api/voice-studio/jobs', headers=self.headers, content=json.dumps(self.body(**changes)),)
            # Explicitly require JSON content type too.
            self.assertEqual(response.status_code, 415)
            response = self.client.post('/api/voice-studio/jobs', headers=self.headers | {'Content-Type': 'application/json'}, content=json.dumps(self.body(**changes)))
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get('/api/voice-studio/jobs/not-a-job', headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get('/api/voice-studio/jobs?pageSize=100', headers=self.headers).status_code, 422)

    def test_persistence_survives_service_recreation(self):
        job = self.create(); completed_fixture(self.service, job['id']); self.service.get(job['id'])
        restored = VoiceStudio(self.root, comfy=self.comfy, launcher=self.launches.append)
        restored.recover(); self.assertEqual(restored.jobs()['jobs'][0]['status'], 'COMPLETED')
        self.assertEqual(len(self.launches), 1)

    def test_autonomous_backend_submits_exact_local_graph_and_releases_lease(self):
        job = self.create(); self.service.capabilities = lambda: {'ready': True}
        lease = Mock(); self.service.lease = lease
        def engine(path, payload=None):
            self.calls.append((path, payload))
            if path == '/prompt':
                completed_fixture(self.service, job['id'])
                return {'prompt_id': 'test-prompt'}
            return {'queue_running': [], 'queue_pending': []}
        self.service.comfy = engine; self.service._run(job['id'])
        self.assertEqual(self.service.get(job['id'])['status'], 'COMPLETED')
        submissions = [payload for path, payload in self.calls if path == '/prompt']
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]['prompt'], self.service.graph(job['id']))
        lease.release.assert_called_once_with(job['id'])

    def test_busy_comfy_preserved_without_submitting_or_unloading(self):
        job = self.create(); self.service.capabilities = lambda: {'ready': True}
        self.service.comfy = lambda path, payload=None: {'queue_running': [['foreign']], 'queue_pending': []}
        self.service._run(job['id'])
        self.assertEqual(self.service.get(job['id'])['status'], 'FAILED')
        self.assertEqual(self.calls, [])

    def test_ambiguous_submission_is_not_retried_and_late_job_is_cancelled(self):
        job = self.create(); self.service.capabilities = lambda: {'ready': True}
        def engine(path, payload=None):
            self.calls.append((path, payload))
            if path == '/prompt': raise TimeoutError('test connection lost')
            return {'queue_running': [], 'queue_pending': []}
        self.service.comfy = engine; self.service._run(job['id'])
        self.assertEqual(self.service.get(job['id'])['status'], 'SUBMISSION_UNCERTAIN')
        self.assertEqual(len([path for path, _ in self.calls if path == '/prompt']), 1)
        self.assertEqual(self.service.cancel(job['id'])['status'], 'CANCELLED')
        self.assertTrue((self.service.folder(job['id']) / 'cancel.flag').exists())


if __name__ == '__main__':
    unittest.main()
