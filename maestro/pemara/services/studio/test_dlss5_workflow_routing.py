import importlib.util
import json
from pathlib import Path
import sys, tempfile, types
import unittest
from unittest.mock import patch
from PIL import Image
import dlss5_finishing as d


class WorkflowExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        root=self.root
        class FakeSaveImage:
            OUTPUT_NODE=True;RETURN_TYPES=();FUNCTION='save'
            @classmethod
            def INPUT_TYPES(cls):return {'required':{'images':('IMAGE',)},'hidden':{'prompt':'PROMPT'}}
            def save(self,images,prompt=None):
                Image.new('RGB',(8,8),(1,2,3)).save(root/'native.png')
                return {'ui':{'images':[{'filename':'native.png','subfolder':'','type':'output'}]}}
        self.save=FakeSaveImage
        folders=types.ModuleType('folder_paths')
        folders.get_output_directory=lambda:str(root);folders.get_temp_directory=lambda:str(root);folders.get_input_directory=lambda:str(root)
        nodes=types.ModuleType('nodes');nodes.NODE_CLASS_MAPPINGS={'SaveImage':FakeSaveImage}
        server=types.ModuleType('server');server.PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(add_on_prompt_handler=lambda fn:None))
        mm=types.ModuleType('comfy.model_management');mm.unload_all_models=lambda:None;mm.soft_empty_cache=lambda:None
        comfy=types.ModuleType('comfy');comfy.model_management=mm
        self.modules=patch.dict(sys.modules,{'folder_paths':folders,'nodes':nodes,'server':server,'comfy':comfy,'comfy.model_management':mm})
        self.modules.start()
        path=Path(__file__).resolve().parents[2]/'ferramentas/comfy_extensions/pemara_dlss5_required/__init__.py'
        spec=importlib.util.spec_from_file_location('policy_fixture',path);self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
    def tearDown(self):self.modules.stop();self.tmp.cleanup()
    def graph(self,kind,stage='final'):
        return {'1':{'class_type':'SaveImage','inputs':{'images':['source',0]}},
                'policy':{'class_type':'PemaraDLSS5ContentPolicy','inputs':{'content_kind':kind,'stage':stage}}}
    def test_live_action_full_frame_export_is_required_at_submission(self):
        g=self.graph('live_action')
        with patch.object(d,'preflight'),patch.object(d,'finish_file',return_value={'profile':d.PROFILE}) as finish:
            result=self.mod.on_prompt({'prompt':g});self.save().save(None,prompt=g)
        self.assertEqual(result['prompt']['1']['class_type'],'SaveImage')
        self.assertEqual(finish.call_args.kwargs['content_kind'],'live_action')
        self.assertFalse(finish.call_args.kwargs.get('protect_actors',False))

    def test_animation_export_passes_declared_kind_to_finisher(self):
        g=self.graph('animation')
        with patch.object(d,'preflight'),patch.object(d,'finish_file',return_value={'profile':d.PROFILE}) as finish:
            result=self.mod.on_prompt({'prompt':g})
            self.save().save(None,prompt=g)
        self.assertEqual(result['prompt']['1']['class_type'],'SaveImage')
        self.assertEqual(finish.call_args.kwargs['content_kind'],'animation')
    def test_legacy_preview_stage_cannot_bypass_integral_anchor_finishing(self):
        g=self.graph('live_action','native_preview')
        with patch.object(d,'preflight'),patch.object(d,'finish_file',return_value={'profile':d.PROFILE}) as finish:
            self.mod.on_prompt({'prompt':g});result=self.save().save(None,prompt=g)
        finish.assert_called_once()
        self.assertEqual(finish.call_args.kwargs['content_kind'],'live_action')
        self.assertTrue(result['ui']['images'][0]['dlss5']['technical_pass'])

    def test_unknown_cannot_silently_become_animation(self):
        with patch.object(d,'preflight'):
            result=self.mod.on_prompt({'prompt':self.graph('unknown')})
        self.assertEqual(result['prompt']['1']['class_type'],'PemaraDLSS5Blocked_RuntimeUnavailable')
    def test_v3_hidden_prompt_is_read_from_executing_class(self):
        g=self.graph('animation')
        class V3:
            hidden=types.SimpleNamespace(prompt=g)
            @classmethod
            def execute(cls,images):pass
        kind,stage=self.mod.call_content_kind(V3.execute.__func__,(V3,None),{})
        self.assertEqual((kind,stage),('animation','final'))

    def glb_result(self, path=None):
        path = path or self.root/'asset.glb'
        return {'ui':{'files':[{'filename':path.name,'subfolder':'','type':'output'}]},
                'result':(str(path),)}

    def save_box(self):
        import trimesh
        path = self.root/'asset.glb'
        trimesh.creation.box().export(path)
        return path

    def test_glb_export_checks_real_geometry_without_raster_finishing(self):
        path = self.save_box()
        before = d.sha(path)
        result = self.glb_result(path)
        with patch.object(d,'finish_file') as finish:
            self.assertIs(self.mod.finish_result(result,'MaestroGame3D',content_kind='animation',
                stage='native_preview',export_kind='glb'), result)
        finish.assert_not_called()
        receipt = json.loads(Path(str(path)+'.verification.json').read_text())
        self.assertEqual(receipt['sha256'], before)
        self.assertGreater(receipt['vertices'], 0)
        self.assertGreater(receipt['faces'], 0)
        self.assertFalse(receipt['dlss5_applied'])
        self.assertEqual(receipt['content_kind'], 'animation')
        self.assertEqual(d.sha(path), before)

    def test_glb_is_not_accepted_as_a_raster_export(self):
        self.save_box()
        with self.assertRaises(d.DLSS5RequiredError):
            self.mod.finish_result(self.glb_result(),'SaveImage',content_kind='animation')

    def test_missing_truncated_wrong_header_and_empty_glb_fail(self):
        import trimesh
        path = self.root/'asset.glb'
        with self.assertRaises(FileNotFoundError):
            self.mod.verify_glb(path)
        for data in (b'', b'not a mesh', b'glTF'+bytes(50)):
            path.write_bytes(data)
            with self.assertRaises(d.DLSS5RequiredError):
                self.mod.verify_glb(path)
        import struct
        document = json.dumps({'asset':{'version':'2.0'},'scenes':[{'nodes':[]}]}).encode()
        document += b' ' * (-len(document) % 4)
        path.write_bytes(struct.pack('<4sIIII',b'glTF',2,20+len(document),len(document),0x4E4F534A)+document)
        with self.assertRaises(d.DLSS5RequiredError):
            self.mod.verify_glb(path)

    def test_textured_glb_retains_material_texture_and_image(self):
        import trimesh
        import numpy as np
        mesh = trimesh.creation.box()
        mesh.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),
            material=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new('RGB',(8,8),'red')))
        path = self.root/'asset.glb'
        mesh.export(path)
        before = d.sha(path)
        receipt = self.mod.verify_glb(path)
        self.assertEqual((receipt['materials'],receipt['textures'],receipt['images']),(1,1,1))
        self.assertEqual(d.sha(path), before)

    def test_nonfinite_vertices_fail(self):
        import trimesh
        mesh = trimesh.creation.box()
        mesh.vertices[0,0] = float('nan')
        path = self.root/'asset.glb'
        mesh.export(path)
        with self.assertRaises(d.DLSS5RequiredError):
            self.mod.verify_glb(path)

    def test_glb_return_must_match_published_path(self):
        self.save_box()
        result = self.glb_result()
        result['result'] = (str(self.root/'different.glb'),)
        with self.assertRaises(d.DLSS5RequiredError):
            self.mod.finish_result(result,'MaestroGame3D',export_kind='glb')

    def test_glb_cannot_escape_output_root(self):
        result = self.glb_result()
        result['ui']['files'][0]['subfolder'] = '..'
        with self.assertRaises(d.DLSS5RequiredError):
            self.mod.finish_result(result,'MaestroGame3D',export_kind='glb')

    def test_mesh_exporter_skips_nr_preflight_but_propagates_generation_error(self):
        class MeshExporter:
            OUTPUT_NODE=True;RETURN_TYPES=('STRING',);FUNCTION='generate';PEMARA_EXPORT_KIND='glb'
            @classmethod
            def INPUT_TYPES(cls):return {'required':{'image':('IMAGE',)},'hidden':{'prompt':'PROMPT'}}
            def generate(self,image,prompt=None):raise RuntimeError('TRELLIS failed')
        self.mod.nodes.NODE_CLASS_MAPPINGS['MaestroGame3D'] = MeshExporter
        g = {'1':{'class_type':'MaestroGame3D','inputs':{'image':['source',0]}},
             'policy':{'class_type':'PemaraDLSS5ContentPolicy','inputs':{'content_kind':'animation'}}}
        with patch.object(d,'preflight') as preflight:
            self.mod.on_prompt({'prompt':g})
            with self.assertRaisesRegex(RuntimeError,'TRELLIS failed'):
                MeshExporter().generate(None,prompt=g)
        preflight.assert_not_called()

    def test_video_remains_native_with_policy_receipt(self):
        path = self.root/'native.mp4'
        path.write_bytes(b'native video bytes for routing test')
        result = {'ui':{'videos':[{'filename':path.name,'subfolder':'','type':'output'}]}}
        with patch.object(d,'finish_file') as finish:
            self.mod.finish_result(result,'SaveVideo',content_kind='animation')
        finish.assert_not_called()
        self.assertTrue(Path(str(path)+'.finishing_policy.json').is_file())
        self.assertEqual(path.read_bytes(), b'native video bytes for routing test')


if __name__=='__main__':unittest.main()
