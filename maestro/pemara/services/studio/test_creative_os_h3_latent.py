import copy
import tempfile
import unittest
from pathlib import Path
from creative_os.h3_latent_finishing import MODELS, source_contract, refinement_graph, fingerprint_source, package
from creative_os.ir import CreativeError


def source():
    return {
        '1':{'class_type':'UNETLoader','inputs':{'unet_name':MODELS['UNETLoader'][2]}},
        '2':{'class_type':'MiniMaxH3SigmaShift','inputs':{'model':['1',0],'shift_video':12,'shift_audio':3}},
        '3':{'class_type':'CLIPLoader','inputs':{'clip_name':MODELS['CLIPLoader'][2]}},
        '4':{'class_type':'VAELoader','inputs':{'vae_name':MODELS['VAELoader'][2]}},
        '6':{'class_type':'MiniMaxH3ImageToVideo','inputs':{'clip':['3',0],'vae':['4',0],
            'prompt':'same original description','width':1088,'height':608,'length':124}},
        '7':{'class_type':'BasicGuider','inputs':{'model':['2',0],'conditioning':['6',0]}},
        '8':{'class_type':'BasicScheduler','inputs':{'model':['2',0],'scheduler':'simple','steps':10,'denoise':1.0}},
        '9':{'class_type':'RandomNoise','inputs':{'noise_seed':23}},
        '10':{'class_type':'KSamplerSelect','inputs':{'sampler_name':'res_multistep'}},
        '11':{'class_type':'SamplerCustomAdvanced','inputs':{'latent_image':['6',1]}},
        '12':{'class_type':'LTXVSeparateAVLatent','inputs':{'av_latent':['11',0]}},
        '13':{'class_type':'VAEDecodeTiled','inputs':{'samples':['12',0],'vae':['4',0]}},
        '14':{'class_type':'ImageScale','inputs':{'image':['13',0],'width':1088,'height':608}},
        '15':{'class_type':'CreateVideo','inputs':{'images':['14',0],'fps':24.0}},
        '16':{'class_type':'SaveVideo','inputs':{'video':['15',0],'filename_prefix':'source'}}}


class H3LatentTests(unittest.TestCase):
    def test_hq_executor_records_prompt_copies_outputs_and_blocks_replay(self):
        from types import SimpleNamespace
        from threading import Event
        from unittest.mock import Mock,patch
        from creative_os.assets import file_hash
        from creative_os.h3_latent_finishing import execute
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'hq';target.mkdir();inputs=root/'inputs';inputs.mkdir()
            latent=root/'source.latent';latent.write_bytes(b'fixture latent')
            weight=root/'upscaler';weight.write_bytes(b'fixture weight')
            code=root/'code.py';code.write_bytes(b'fixture code')
            video=root/'output.mp4';video.write_bytes(b'fixture output')
            refined=root/'output.latent';refined.write_bytes(b'fixture refined latent')
            package_record={'artifact':{'sha256':file_hash(latent)},'metadata':{'frames':124}}
            service=SimpleNamespace(store=Mock(),finishing=SimpleNamespace(stop=Event()))
            service.store.get.return_value={'generation_id':'g1'}
            job={'id':'fixture-job','master_id':'m1','profile':{'qualification':{
                'code_files':{str(code):file_hash(code)},'models':{},
                'upscaler':{'path':str(weight),'sha256':file_hash(weight)}}}}
            def queue(graph,**kwargs):
                kwargs['prompt_id_cb']('fixture-prompt')
                return 'fixture-prompt',[{'kind':'video','filename':video.name},{'kind':'latent','filename':refined.name}]
            ns={'COMFY_INPUT_DIR':str(inputs),'_comfy_request':Mock(return_value={'system':{'comfyui_version':'0.34.2'}}),
                '_queue_comfy_workflow':Mock(side_effect=queue),'_safe_comfy_output_path':lambda name,*args:root/name}
            media={'pass':True,'audio_present':False,'video':{'width':1536,'height':864,'nb_read_frames':'124','r_frame_rate':'24/1'}}
            with patch('creative_os.h3_latent_finishing.package',return_value=(latent,{'graph':source()},package_record)),patch('creative_os.evaluation.inspect_video',return_value=media):
                candidate=execute(service,ns,job,target)
                self.assertEqual(candidate.read_bytes(),video.read_bytes())
                self.assertTrue((target/'prompt.json').is_file())
                self.assertEqual(latent.read_bytes(),b'fixture latent')
                with self.assertRaisesRegex(CreativeError,'nenhum reenvio'): execute(service,ns,job,target)
            ns['_queue_comfy_workflow'].assert_called_once()

    def test_package_requires_original_fingerprints_and_unchanged_models(self):
        import numpy as np
        from safetensors.numpy import save_file
        from creative_os.service import CreativeService
        from creative_os.bridge import Bridge
        from creative_os.assets import file_hash
        from creative_os.integration import archive_workflow
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);service=CreativeService(root,root,Bridge(Mock(),Mock(),Mock(),Mock(),Mock()))
            latent=root/'video.latent'
            save_file({'latent_tensor':np.zeros((1,24,37,38,68),dtype=np.float32),'latent_format_version_0':np.zeros((0,),dtype=np.float32)},str(latent))
            graph=source()
            for _,folder,name in MODELS.values():
                (root/folder).mkdir(exist_ok=True);(root/folder/name).write_bytes(b'fixture model')
            captured=fingerprint_source(graph,root,'0.34.2')
            qualified={k:v['sha256'] for k,v in captured['models'].items()}
            archive=archive_workflow(root/'workflows','test-prompt',graph)
            service.store.put('generations',{'status':'done','engine_id':'minimax_h3','prompt_id':'test-prompt',
                'provenance':{'workflow_hash':archive['workflow_hash']},
                'artifacts':[{'kind':'latent','relative_path':'video.latent','sha256':file_hash(latent)}]},entity_id='g1')
            with self.assertRaisesRegex(CreativeError,'fingerprints'): package(service,'g1',qualified)
            # Separate fixture generation, with metadata captured before its test submission.
            archive_workflow(root/'workflows','captured-prompt',graph,model_fingerprints=captured)
            generation=service.store.get('generations','g1')
            service.store.put('generations',{**generation,'prompt_id':'captured-prompt'},entity_id='g1',expected=generation['revision'],create=False)
            path,_,record=package(service,'g1',qualified)
            self.assertEqual(path,latent.resolve())
            self.assertTrue(record['roundtrip_qualified'])
            self.assertEqual(package(service,'g1',qualified)[2],record)
            _,folder,name=MODELS['VAELoader'];(root/folder/name).write_bytes(b'changed')
            with self.assertRaisesRegex(CreativeError,'Modelo mudou'): package(service,'g1',qualified)

    def test_refinement_preserves_original_models_prompt_seed_and_parent(self):
        graph=source();before=copy.deepcopy(graph)
        hq=refinement_graph(graph,'managed.latent')
        self.assertEqual(graph,before)
        for key in ('1','2','3','4','7','9','10'): self.assertEqual(hq[key],graph[key])
        self.assertEqual(hq['6']['inputs']['prompt'],graph['6']['inputs']['prompt'])
        self.assertEqual((hq['8']['inputs']['steps'],hq['8']['inputs']['denoise']),(4,0.25))
        self.assertEqual(hq['11']['inputs']['latent_image'],['creative_hq_concat',0])
        self.assertNotIn('audio',hq['15']['inputs'])

    def test_unqualified_source_reference_audio_and_paths_block(self):
        for mutation in (lambda g:g['6']['inputs'].update(first_frame=['99',0]),
                         lambda g:g['15']['inputs'].update(audio=['99',0]),
                         lambda g:g['6']['inputs'].update(length=372),
                         lambda g:g['1']['inputs'].update(unet_name='other.safetensors')):
            graph=source();mutation(graph)
            with self.assertRaises(CreativeError): refinement_graph(graph,'managed.latent')
        for name in ('../x.latent','C:\\x.latent','x/y.latent'):
            with self.assertRaises(CreativeError): refinement_graph(source(),name)

    def test_fingerprints_are_captured_before_execution_and_change_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for _,folder,name in MODELS.values():
                (root/folder).mkdir(exist_ok=True);(root/folder/name).write_bytes(b'original')
            before=fingerprint_source(source(),root,'0.34.2')
            _,folder,name=MODELS['UNETLoader'];(root/folder/name).write_bytes(b'changed-size')
            after=fingerprint_source(source(),root,'0.34.2')
            self.assertNotEqual(before['models']['UNETLoader']['sha256'],after['models']['UNETLoader']['sha256'])
            self.assertEqual(before['capture'],'BEFORE_PROMPT_SUBMISSION')
            with self.assertRaises(CreativeError): fingerprint_source(source(),root,'different')
