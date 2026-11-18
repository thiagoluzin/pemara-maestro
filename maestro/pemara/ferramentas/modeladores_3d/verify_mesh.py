import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

p = argparse.ArgumentParser()
p.add_argument('engine')
p.add_argument('prompt_id')
p.add_argument('file')
args = p.parse_args()
path = Path(args.file)
scene = trimesh.load(path, force='scene')
assert scene.geometry, 'No meshes'
for mesh in scene.geometry.values():
    assert len(mesh.vertices) and len(mesh.faces), 'Empty mesh'
    assert np.isfinite(mesh.vertices).all(), 'Non-finite coordinates'
    assert mesh.faces.min() >= 0 and mesh.faces.max() < len(mesh.vertices), 'Invalid indices'
with path.open('rb') as handle:
    sha = hashlib.file_digest(handle, 'sha256').hexdigest()
receipt = dict(engine=args.engine, promptId=args.prompt_id, output=str(path),
               bytes=path.stat().st_size, sha256=sha,
               vertices=sum(len(m.vertices) for m in scene.geometry.values()),
               faces=sum(len(m.faces) for m in scene.geometry.values()),
               watertight=all(m.is_watertight for m in scene.geometry.values()),
               technicalInferencePassed=True, textured=False,
               printReady=False, artisticApproval=False)
path.with_suffix('.validation.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt))
