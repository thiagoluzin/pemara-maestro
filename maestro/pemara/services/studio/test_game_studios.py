import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import game_assets as assets
import game_images as images
import game_gpu_admission as admission
import game_3d
import io
from unittest.mock import MagicMock

class GameStudioTests(unittest.TestCase):
    def test_3d_worker_preserves_prompt_and_copies_only_local_output(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(game_3d, 'COMFY_OUTPUT', Path(temp).resolve()):
            root = Path(temp)
            (root/'generated').mkdir(); (root/'generated/asset.glb').write_bytes(b'glTFfixture')
            folder = root/'job'; folder.mkdir(); (folder/'source.png').write_bytes(b'input')
            uploaded = MagicMock(); uploaded.json.return_value = {'name':'input.png'}
            submitted = MagicMock(); submitted.json.return_value = {'prompt_id':'test-prompt'}
            finished = MagicMock(); finished.json.return_value = {'test-prompt': {'status':{'status_str':'success'}, 'outputs':{'2':{'files':[{'filename':'asset.glb','subfolder':'generated'}]}}}}
            with patch.object(game_3d.requests,'post',side_effect=[uploaded,submitted]), patch.object(game_3d.requests,'get',return_value=finished):
                game_3d.worker(folder, 'a'*32, 'trellis2')
            result = game_3d.json.loads((folder/'job.json').read_text())
            self.assertEqual(result['status'],'done')
            self.assertEqual(result['promptId'],'test-prompt')
            self.assertEqual((folder/'asset.glb').read_bytes(),b'glTFfixture')
            self.assertTrue((root/'generated/asset.glb').is_file())

    def test_3d_auth_and_invalid_upload_do_not_queue(self):
        app = FastAPI()
        app.include_router(game_3d.create_game_3d_router(lambda _: False))
        self.assertEqual(TestClient(app).get('/api/zico/games/3d/engines').status_code, 403)
        with tempfile.TemporaryDirectory() as temp, patch.object(game_3d, 'ROOT', Path(temp)), patch.object(game_3d, 'MARKERS', Path(temp)):
            project = Path(temp)/'projects'/('a'*32)
            project.mkdir(parents=True); (project/'project.json').write_text('{}')
            (Path(temp)/'trellis2-runtime.json').write_text('{}')
            app = FastAPI(); app.include_router(game_3d.create_game_3d_router(lambda _: True))
            with patch.object(game_3d.threading, 'Thread') as thread:
                response = TestClient(app).post('/api/zico/games/3d', data={'project_id': 'a'*32, 'engine': 'trellis2'}, files={'image': ('bad.png', b'invalid')})
                self.assertEqual(response.status_code, 400)
                thread.assert_not_called()
            with self.assertRaises(ValueError): game_3d.workflow('sample.png', '../model')

    def test_gpu_admission_never_unloads_a_busy_queue(self):
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(b'{"queue_running":[[1]],"queue_pending":[]}')
        with patch.object(admission.urllib.request, 'urlopen', return_value=response) as call, patch.object(admission.subprocess, 'run') as gpu:
            with self.assertRaises(RuntimeError): admission.admit(20000)
            self.assertEqual(call.call_count, 1)
            gpu.assert_not_called()

    def test_gpu_admission_releases_only_idle_cache(self):
        queue = MagicMock(); queue.__enter__.return_value = io.BytesIO(b'{"queue_running":[],"queue_pending":[]}')
        release = MagicMock()
        with patch.object(admission.urllib.request, 'urlopen', side_effect=[queue, release]) as call, patch.object(admission.subprocess, 'run', side_effect=[MagicMock(stdout='25000, 7000'), MagicMock(stdout='1000, 31000')]), patch.object(admission.time, 'sleep'):
            admission.admit(20000)
            self.assertEqual(call.call_args.args[0].full_url, 'http://127.0.0.1:8188/free')

    def client(self, allowed=True):
        app = FastAPI()
        app.include_router(assets.create_game_assets_router(lambda _: allowed))
        app.include_router(images.create_game_images_router(lambda _: allowed))
        return TestClient(app)

    def test_image_auth_and_explicit_engine(self):
        body = {'projectId': 'a'*32, 'engine': 'unknown', 'prompt': 'A vase'}
        self.assertEqual(self.client(False).post('/api/zico/games/images', json=body).status_code, 403)
        self.assertEqual(self.client(False).get('/api/zico/games/images/engines').status_code, 403)
        with tempfile.TemporaryDirectory() as temp, patch.object(images, 'ROOT', Path(temp)):
            folder = Path(temp)/'projects'/body['projectId']
            folder.mkdir(parents=True); (folder/'project.json').write_text('{}')
            self.assertEqual(self.client().post('/api/zico/games/images', json=body).status_code, 400)
            body['engine'] = 'flux2-klein'
            with patch.object(images, 'ready', return_value=False):
                self.assertEqual(self.client().post('/api/zico/games/images', json=body).status_code, 503)
            self.assertFalse((Path(temp)/'image_jobs').exists())

    def test_asset_invalid_upload_releases_capacity(self):
        project_id = 'b'*32
        with tempfile.TemporaryDirectory() as temp, patch.object(assets, 'ROOT', Path(temp)), patch.object(assets, 'BLENDER', Path(__file__)):
            project = Path(temp)/'projects'/project_id
            project.mkdir(parents=True); (project/'project.json').write_text('{}')
            client = self.client()
            for _ in range(2):
                response = client.post('/api/zico/games/assets', data={'project_id': project_id}, files={'asset': ('input.glb', b'not a GLB')})
                self.assertEqual(response.status_code, 400)
            with patch.object(assets, 'MAX_BYTES', 8):
                response = client.post('/api/zico/games/assets', data={'project_id': project_id}, files={'asset': ('input.glb', b'glTF' + b'0'*20)})
                self.assertEqual(response.status_code, 413)
            self.assertTrue(assets._gate.acquire(blocking=False)); assets._gate.release()

    def test_asset_auth_and_path_scope(self):
        response = self.client(False).post('/api/zico/games/assets', data={'project_id': 'a'*32}, files={'asset': ('input.glb', b'glTF')})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client().get('/api/zico/games/assets/not-a-job/output').status_code, 404)
        self.assertEqual(self.client(False).get('/api/zico/games/assets/'+'a'*32+'/output').status_code, 403)
        self.assertEqual(self.client(False).get('/api/zico/games/images/'+'a'*32+'/output').status_code, 403)

if __name__ == '__main__': unittest.main()
