import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import zico_audio as z
from video_sound import ExternalCommandVideoSoundProvider

class ZicoAudioTests(unittest.TestCase):
    def client(self, allowed=True):
        app=FastAPI()
        app.include_router(z.create_zico_router(lambda request: allowed))
        return TestClient(app)

    def test_public_access_denied(self):
        client=self.client(False)
        for path in ('','/capabilities','/outputs/'+'a'*32):
            self.assertEqual(client.get('/api/zico'+path).status_code,403)
        self.assertEqual(client.post('/api/zico/route',json={'task':'foley'}).status_code,403)

    def test_route_does_not_submit_or_replace_engine(self):
        result=self.client().post('/api/zico/route',json={'task':'foley do vídeo'}).json()
        self.assertEqual(result['engine'],'mmaudio')
        self.assertFalse(result['submitted'])

    def test_music_route_uses_original_creation_and_reinstrumentation_is_retired(self):
        client = self.client()
        result = client.post('/api/zico/route', json={'task': 'criar música original'}).json()
        self.assertEqual(result['engine'], 'yue2_local')
        self.assertEqual(result['maestroEndpoint'], '/api/generative/jobs')
        self.assertFalse(result['submitted'])
        for task in ('trocar instrumento', 'reorquestrar música', 'reinstrumentar música'):
            self.assertEqual(client.post('/api/zico/route', json={'task': task}).status_code, 410)
        result = client.post('/api/zico/route', json={'task': 'criar música com instrumentação pesada'}).json()
        self.assertEqual(result['engine'], 'yue2_local')

    def test_invalid_mix_and_output_rejected(self):
        client=self.client()
        self.assertEqual(client.post('/api/zico/mix',json={}).status_code,400)
        self.assertEqual(client.post('/api/zico/mix',json={'target_lufs':0}).status_code,422)
        self.assertEqual(client.get('/api/zico/outputs/invalid').status_code,404)

    def test_mix_preserves_input_and_uses_unique_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'silence.wav'
            with wave.open(str(source),'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000);wav.writeframes(b'\0\0'*48000)
            before=source.read_bytes()
            with patch.object(z,'OUTPUTS',Path(temp)/'outputs'):
                a=z.mix(z.MixRequest(dialogue=str(source)))
                b=z.mix(z.MixRequest(dialogue=str(source)))
                self.assertNotEqual(a['output'],b['output'])
                self.assertTrue(Path(a['output']).is_file())
                self.assertEqual(source.read_bytes(),before)

    def test_missing_weights_never_report_ready(self):
        import sys
        with tempfile.TemporaryDirectory() as temp:
            provider=ExternalCommandVideoSoundProvider({'id':'test','enabled':True,'argvTemplate':[sys.executable],
                'requiredPaths':[str(Path(temp)/'missing.pth')]})
            self.assertFalse(provider.status()['configured'])

    def test_fish_refuses_before_weight_verification(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(z,'ROOT',Path(temp)):
            response=self.client().post('/api/zico/fish/jobs',json={'text':'Teste'})
            self.assertEqual(response.status_code,503)
            self.assertEqual(self.client(False).post('/api/zico/fish/jobs',json={'text':'Teste'}).status_code,403)

    def test_game_project_scopes_paths_and_preserves_brief(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(z, 'GAME_PROJECTS', Path(temp)):
            client = self.client()
            data = {'name': '../Meu jogo', 'brief': 'Personagem e objetos'}
            response = client.post('/api/zico/games/projects', json=data)
            self.assertEqual(response.status_code, 201)
            project = response.json()
            self.assertFalse(project['generationEnabled'])
            self.assertEqual(len(project['id']), 32)
            self.assertTrue((Path(temp) / project['id'] / 'exports').is_dir())
            self.assertEqual(client.get('/api/zico/games/projects').json()['projects'][0]['brief'], data['brief'])
            self.assertEqual(self.client(False).get('/api/zico/games/projects').status_code, 403)
            self.assertEqual(self.client(False).post('/api/zico/games/projects', json=data).status_code, 403)

    def test_game_catalog_does_not_claim_installed_models(self):
        result = self.client().get('/api/zico/games/catalog')
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()['generationEnabled'])
        self.assertEqual(self.client(False).get('/api/zico/games/catalog').status_code, 403)

    def test_audio_upload_uses_unique_local_path_and_requires_auth(self):
        files = {'audio': ('../../original.wav', b'RIFF-example')}
        self.assertEqual(self.client(False).post('/api/zico/uploads', files=files).status_code, 403)
        with tempfile.TemporaryDirectory() as temp, patch.object(z, 'ROOT', Path(temp)):
            response = self.client().post('/api/zico/uploads', files=files)
            self.assertEqual(response.status_code, 201)
            target = Path(response.json()['path'])
            self.assertTrue(target.is_relative_to(Path(temp)/'uploads'))
            self.assertEqual(target.read_bytes(), b'RIFF-example')
            self.assertEqual(self.client().post('/api/zico/uploads', files={'audio': ('x.exe', b'test')}).status_code, 400)

if __name__=='__main__':
    unittest.main()
