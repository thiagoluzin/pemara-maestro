"""Static asset preparation invoked by the Maestro worker in factory Blender."""
from pathlib import Path
import importlib.util
import sys
import bpy

source, destination = map(Path, sys.argv[sys.argv.index('--') + 1:])
if destination.exists():
    raise RuntimeError('Output already exists')
spec = importlib.util.spec_from_file_location('maestro_bridge', Path(__file__).parent / 'integrations/blender/__init__.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
bridge.register()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
if any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects):
    raise RuntimeError('Este processamento é para objetos estáticos. A malha com esqueleto foi preservada sem processamento.')
objects = list(bridge._mesh_objects())
if not objects:
    raise RuntimeError('O arquivo não contém malhas.')
for obj in objects:
    bridge._activate(obj)
    bpy.ops.zico.process_asset()
bpy.context.scene.zico_settings.output_glb = str(destination)
assert bpy.ops.zico.export_asset() == {'FINISHED'}
