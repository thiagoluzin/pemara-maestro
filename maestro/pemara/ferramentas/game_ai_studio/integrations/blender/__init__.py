bl_info = {
    "name": "Maestro Pemara Asset Bridge",
    "author": "Pemaratech",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > ZICO AI",
    "description": "Importa GLB, normaliza, cria LODs/collider e exporta para engines",
    "category": "Import-Export",
}

import json
import os
from pathlib import Path

import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup


def _install_root() -> Path:
    marker = Path(__file__).with_name("install_root.txt")
    if marker.exists():
        return Path(marker.read_text(encoding="utf-8-sig").strip())
    return Path(os.environ.get("ZICO_GAME_AI_HOME", r"C:\ZicoGameAI"))


def _mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def _activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _apply_transforms(obj):
    _activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def _clean_mesh(obj):
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data)
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.0001)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()


def _normalize_asset(objects, target_size):
    if not objects:
        return
    points = []
    for obj in objects:
        points.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
    mins = [min(p[i] for p in points) for i in range(3)]
    maxs = [max(p[i] for p in points) for i in range(3)]
    extent = max(maxs[i] - mins[i] for i in range(3))
    if extent <= 0:
        return
    scale = target_size / extent
    center_x = (mins[0] + maxs[0]) * 0.5
    center_y = (mins[1] + maxs[1]) * 0.5
    floor_z = mins[2]
    for obj in objects:
        obj.location.x = (obj.location.x - center_x) * scale
        obj.location.y = (obj.location.y - center_y) * scale
        obj.location.z = (obj.location.z - floor_z) * scale
        obj.scale *= scale
        _apply_transforms(obj)


def _make_lod(source, suffix, ratio):
    lod = source.copy()
    lod.data = source.data.copy()
    bpy.context.collection.objects.link(lod)
    lod.name = f"{source.name.rsplit('_LOD', 1)[0]}_{suffix}"
    modifier = lod.modifiers.new(name="ZICO_Decimate", type="DECIMATE")
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    _activate(lod)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return lod


def _make_convex_collider(source):
    collider = source.copy()
    collider.data = source.data.copy()
    bpy.context.collection.objects.link(collider)
    collider.name = f"UCX_{source.name}"
    mesh = collider.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    unused = [v for v in result.get("geom_unused", []) + result.get("geom_interior", []) if isinstance(v, bmesh.types.BMVert)]
    if unused:
        bmesh.ops.delete(bm, geom=list(set(unused)), context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    collider.display_type = "WIRE"
    collider.hide_render = True
    return collider


class ZICO_Settings(PropertyGroup):
    input_glb: StringProperty(name="GLB de entrada", subtype="FILE_PATH")
    output_glb: StringProperty(name="GLB de saida", subtype="FILE_PATH")
    target_size: FloatProperty(name="Tamanho (m)", default=2.0, min=0.01, max=1000.0)
    lod1_ratio: FloatProperty(name="LOD1", default=0.50, min=0.05, max=0.95)
    lod2_ratio: FloatProperty(name="LOD2", default=0.20, min=0.01, max=0.90)
    clean_mesh: BoolProperty(name="Limpar malha", default=True)
    make_collider: BoolProperty(name="Collider convexo", default=True)


class ZICO_OT_import(Operator):
    bl_idname = "zico.import_asset"
    bl_label = "Importar GLB"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        path = bpy.path.abspath(context.scene.zico_settings.input_glb)
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Selecione um GLB valido")
            return {"CANCELLED"}
        before = set(context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        imported = [o for o in context.scene.objects if o not in before and o.type == "MESH"]
        _normalize_asset(imported, context.scene.zico_settings.target_size)
        self.report({"INFO"}, f"{len(imported)} malhas importadas")
        return {"FINISHED"}


class ZICO_OT_process(Operator):
    bl_idname = "zico.process_asset"
    bl_label = "Processar ativo"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "Selecione uma malha")
            return {"CANCELLED"}
        settings = context.scene.zico_settings
        if settings.clean_mesh:
            _clean_mesh(obj)
        obj.name = obj.name.rsplit("_LOD", 1)[0] + "_LOD0"
        _make_lod(obj, "LOD1", settings.lod1_ratio)
        _make_lod(obj, "LOD2", settings.lod2_ratio)
        if settings.make_collider:
            _make_convex_collider(obj)
        self.report({"INFO"}, "LOD0/1/2 e collider criados")
        return {"FINISHED"}


class ZICO_OT_export(Operator):
    bl_idname = "zico.export_asset"
    bl_label = "Exportar GLB para Unity"

    def execute(self, context):
        settings = context.scene.zico_settings
        path = bpy.path.abspath(settings.output_glb)
        if not path:
            path = str(_install_root() / "data" / "outbox" / "asset_game_ready.glb")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if Path(path).exists():
            self.report({"ERROR"}, "O arquivo já existe. Escolha outro nome para preservar o original.")
            return {"CANCELLED"}
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format="GLB",
            use_selection=False,
            export_apply=True,
            export_yup=True,
            export_materials="EXPORT",
        )
        for mesh_object in _mesh_objects():
            mesh_object.data.calc_loop_triangles()
        report = {
            "asset": Path(path).name,
            "meshes": len(_mesh_objects()),
            "triangles": sum(len(o.data.loop_triangles) for o in _mesh_objects()),
        }
        Path(path).with_suffix(".zico.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.report({"INFO"}, f"Exportado: {path}")
        return {"FINISHED"}


class ZICO_PT_panel(Panel):
    bl_label = "Maestro Pemara"
    bl_idname = "ZICO_PT_asset_bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Maestro"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.zico_settings
        layout.prop(settings, "input_glb")
        layout.prop(settings, "target_size")
        layout.operator("zico.import_asset", icon="IMPORT")
        layout.separator()
        layout.prop(settings, "clean_mesh")
        layout.prop(settings, "make_collider")
        layout.prop(settings, "lod1_ratio")
        layout.prop(settings, "lod2_ratio")
        layout.operator("zico.process_asset", icon="MOD_DECIM")
        layout.separator()
        layout.prop(settings, "output_glb")
        layout.operator("zico.export_asset", icon="EXPORT")


CLASSES = (ZICO_Settings, ZICO_OT_import, ZICO_OT_process, ZICO_OT_export, ZICO_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.zico_settings = bpy.props.PointerProperty(type=ZICO_Settings)


def unregister():
    del bpy.types.Scene.zico_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
