"""Exercise the new exporter without executing any GPU worker."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import upscaling_required as policy

class LanczosExporterTests(unittest.TestCase):
    def test_native_video_goes_to_rife_lanczos_nvenc_without_seed_images(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            source=root/'native.mp4'
            source.write_bytes(b'native source')
            mask=root/'reviewed_masks.json'
            mask.write_text('{}')
            folder=SimpleNamespace(get_input_directory=lambda:str(root),get_output_directory=lambda:str(root))
            mm=ModuleType('comfy.model_management')
            mm.unload_all_models=lambda:None
            mm.soft_empty_cache=lambda:None
            comfy=ModuleType('comfy'); comfy.model_management=mm
            latest=ModuleType('comfy_api.latest'); latest.VideoFromFile=lambda path:path
            api=ModuleType('comfy_api'); api.latest=latest
            path=policy.ENGINE.parent/'comfy_extensions/pemara_upscaling_required/__init__.py'
            spec=importlib.util.spec_from_file_location('test_exporter_module',path)
            module=importlib.util.module_from_spec(spec)
            with patch.dict(sys.modules,{'folder_paths':folder,'comfy':comfy,'comfy.model_management':mm,'comfy_api':api,'comfy_api.latest':latest}):
                spec.loader.exec_module(module)
                graph=policy.build_workflow(source.name,1280,720,1920,1080,'test',content_kind='live_action')
                before={'streams':[{'codec_type':'video','pix_fmt':'yuv420p','width':1280,'height':720,'avg_frame_rate':'24/1','r_frame_rate':'24/1','nb_read_frames':'24'}, {'codec_type':'audio'}]}
                after={'streams':[{'codec_type':'video','width':1920,'height':1080,'avg_frame_rate':'60/1','nb_read_frames':'60','duration':'1.0'},{'codec_type':'audio'}]}
                commands=[]
                def fake_run(command,**kwargs):
                    commands.append(command)
                    if '--lanczos' in command:
                        Path(command[4]).write_bytes(b'conventional finished frames')
                with patch.object(module.dlss,'preflight'),patch.object(module.dlss,'_probe',side_effect=[before,after]),patch.object(module.dlss,'_timestamps',side_effect=[[i/24 for i in range(24)],[i/60 for i in range(60)]]),patch.object(module.dlss,'_audio_hash',return_value='audio'),patch.object(module.dlss,'_audio_pcm_hash',return_value='pcm'),patch.object(module.dlss,'finish_file') as finish,patch.object(module.dlss,'carry_receipt'),patch.object(module.subprocess,'run',side_effect=fake_run),patch.object(module.subprocess,'Popen',side_effect=AssertionError('Seed frame encoder must never execute')):
                    inputs={k:v for k,v in graph['15']['inputs'].items() if k!='source_video'}
                    result=module.PemaraLanczosUpscaleRequiredSave().save(source_video=SimpleNamespace(get_stream_source=lambda:str(source),get_active_trim_window=lambda:(0.0,0.0)),prompt=graph,**inputs)
                self.assertEqual(len(commands),2)
                self.assertEqual(commands[0][2],str(source.resolve()))
                self.assertIn('--lanczos',commands[0])
                finish.assert_not_called()
                final=Path(result['result'][0])
                proof=__import__('json').loads(policy.receipt_path(final).read_text())
                self.assertEqual(proof['pipeline_version'],policy.CONVENTIONAL_PIPELINE)
                self.assertEqual(source.read_bytes(),b'native source')
                self.assertTrue(proof['audio_preserved'])
                self.assertIs(proof['dlss5_applied'],False)
