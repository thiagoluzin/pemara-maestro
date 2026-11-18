import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

p = argparse.ArgumentParser()
p.add_argument('engine', choices=['trellis2', 'pixal3d'])
p.add_argument('prompt_id')
p.add_argument('file')
args = p.parse_args()
path = Path(args.file)
scene = trimesh.load(path, force='scene')
for geometry in scene.geometry.values():
    assert len(geometry.faces) and len(geometry.vertices)
    assert np.isfinite(geometry.vertices).all()
    assert geometry.faces.min() >= 0 and geometry.faces.max() < len(geometry.vertices)
receipt = {'engine': args.engine, 'promptId': args.prompt_id, 'output': str(path),
    'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest(),
    'meshes': len(scene.geometry), 'vertices': sum(len(g.vertices) for g in scene.geometry.values()),
    'faces': sum(len(g.faces) for g in scene.geometry.values()), 'technicalInferencePassed': True,
    'backgroundRemoval': 'BiRefNet', 'textured': False, 'artisticApproval': False}
assert receipt['meshes'] > 0
Path('D:/PemaraRuntimes/maestro-game-ai/logs', args.engine + '-runtime.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt))
