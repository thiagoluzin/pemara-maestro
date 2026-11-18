"""3D download contract in a temporary store; no GPU or live requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import game_assets


class Models3DDownloadContractTests(unittest.TestCase):
    def test_glb_output_is_an_authenticated_attachment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_id = 'a' * 32
            folder = root / 'jobs' / job_id
            folder.mkdir(parents=True)
            (folder / 'job.json').write_text(json.dumps({'jobId': job_id, 'status': 'done'}))
            payload = b'glTF' + b'fixture'
            (folder / 'asset.glb').write_bytes(payload)
            with patch.object(game_assets, 'ROOT', root):
                for allowed, expected in [(False, 403), (True, 200)]:
                    app = FastAPI()
                    app.include_router(game_assets.create_game_assets_router(lambda _: allowed))
                    response = TestClient(app).get(f'/api/zico/games/assets/{job_id}/output')
                    self.assertEqual(response.status_code, expected)
                    if allowed:
                        self.assertEqual(response.content, payload)
                        self.assertEqual(response.headers['content-type'], 'model/gltf-binary')
                        self.assertIn('attachment', response.headers['content-disposition'])
                        self.assertIn('.glb', response.headers['content-disposition'])
                        self.assertEqual(int(response.headers['content-length']), len(payload))


if __name__ == '__main__':
    unittest.main()
