"""CPU import and geometry verification, including upstream bpy wheel metadata."""
from pathlib import Path
import importlib.metadata
import json
import tempfile
import torch
import flash_attn
import bpy

with tempfile.TemporaryDirectory() as temp:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    target = Path(temp) / 'cube.glb'
    bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB')
    assert target.stat().st_size > 0

receipt = {'importsPassed': True, 'geometryExportPassed': True, 'torch': torch.__version__,
           'bpy': bpy.app.version_string, 'flashAttention': importlib.metadata.version('flash-attn'),
           'pipCheckWarning': 'Upstream bpy 5.0.1 wheel declares cp39 metadata; imports and GLB export pass under Python 3.11.',
           'gpuInferenceTested': False}
Path('/mnt/d/PemaraRuntimes/maestro-game-ai/logs/skintokens-software.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt))
