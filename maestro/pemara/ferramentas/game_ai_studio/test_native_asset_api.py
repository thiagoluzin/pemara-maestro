"""CPU end-to-end upload, processing and download using the real Blender worker."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'services/studio'))
import game_assets

with tempfile.TemporaryDirectory(prefix='maestro_asset_api_') as temporary:
    root = Path(temporary)
    fixture = root/'fixture.glb'
    builder = root/'fixture.py'
    builder.write_text("import bpy,sys\nbpy.ops.export_scene.gltf(filepath=sys.argv[-1],export_format='GLB')\n", encoding='utf-8')
    subprocess.run([str(game_assets.BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
                    '--python', str(builder), '--', str(fixture)], check=True, capture_output=True, timeout=60)
    original = fixture.read_bytes()
    project_id = 'c'*32
    project = root/'projects'/project_id
    project.mkdir(parents=True); (project/'project.json').write_text('{}')
    app = FastAPI(); app.include_router(game_assets.create_game_assets_router(lambda _: True))
    with patch.object(game_assets, 'ROOT', root), TestClient(app) as client:
        response = client.post('/api/zico/games/assets', data={'project_id': project_id}, files={'asset': ('fixture.glb', original)})
        assert response.status_code == 202, response.text
        job = response.json()
        deadline = time.monotonic() + 90
        while job['status'] in ('queued', 'running') and time.monotonic() < deadline:
            time.sleep(.5)
            job = client.get('/api/zico/games/assets/'+job['jobId']).json()
        assert job['status'] == 'done', job
        output = client.get(job['url'])
        assert output.status_code == 200 and output.content[:4] == b'glTF'
        assert fixture.read_bytes() == original
        print(json.dumps({'passed': True, 'upload': 202, 'processing': job['status'], 'download': 200,
                          'originalPreserved': True, 'outputBytes': len(output.content)}))
