"""CPU geometry smoke test, using factory startup and a temporary output."""
from pathlib import Path
import importlib.util
import tempfile
import bpy

path = Path(__file__).parent / 'integrations/blender/__init__.py'
spec = importlib.util.spec_from_file_location('maestro_bridge', path)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
bridge.register()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
assert bpy.ops.zico.process_asset() == {'FINISHED'}
assert len(bridge._mesh_objects()) == 4
with tempfile.TemporaryDirectory() as temp:
    target = Path(temp) / 'test.glb'
    bpy.context.scene.zico_settings.output_glb = str(target)
    assert bpy.ops.zico.export_asset() == {'FINISHED'}
    assert target.stat().st_size > 0
    before = target.read_bytes()
    try:
        bpy.ops.zico.export_asset()
    except RuntimeError:
        pass
    assert target.read_bytes() == before
bridge.unregister()
print('PASS: Blender import/register, mesh cleanup, LODs, collider, GLB export, preserve original')
