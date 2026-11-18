import bpy
import json
from pathlib import Path
import sys

source = Path(sys.argv[sys.argv.index('--') + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
armatures = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert armatures and meshes, 'GLB needs an armature and a mesh'
bones = sum(len(o.data.bones) for o in armatures)
assert bones > 0
result = {'meshes': len(meshes), 'armatures': len(armatures), 'bones': bones, 'output': str(source)}
source.with_suffix('.validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
