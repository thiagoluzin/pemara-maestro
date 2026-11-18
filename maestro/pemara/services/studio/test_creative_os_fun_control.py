import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from creative_os.assets import file_hash
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.fun_control import validate_request,patch_graph,apply_in_worker,verify_video
from creative_os.fun_control_jobs import generate,import_control
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.submit=Mock(return_value='control-job')
        self.s=CreativeService(self.root/'state',self.root/'projects',Bridge(self.submit,Mock(),
            lambda:{'optional':{'h3_fun_control':{'enabled':True}}},Mock(),Mock()))
        self.ir=sample();self.shot=self.s.save_shot(self.ir)
        self.file=self.s.assets.root/'audit'/'control.mp4';self.file.parent.mkdir(parents=True);self.file.write_bytes(b'fixture-video')
        self.asset=self.s.assets.register('audit','control.mp4','motion_reference')
        self.req={'ir':self.ir,'asset_id':self.asset['id'],'asset_sha256':self.asset['sha256'],'strength':1.0,'control_kind':'depth'}
    def tearDown(self):self.tmp.cleanup()

    def test_wrong_scope_and_external_controls_block(self):
        for key,val in [('strength',float('nan')),('asset_sha256','bad'),('control_kind','guess')]:
            req=copy.deepcopy(self.req);req[key]=val
            with self.assertRaises(CreativeError):validate_request(req,engine_id='minimax_h3',native_audio=False,profile='h3_production')
        req=copy.deepcopy(self.req);req['ir']['generation']['native_audio']=True
        with self.assertRaises(CreativeError):validate_request(req,engine_id='minimax_h3',native_audio=False,profile='h3_production')
        with self.assertRaises(CreativeError):generate(self.s,self.shot['id'],'x',asset_id='asset://other/a',control_kind='depth',seed=42)

    def test_failed_submit_never_replays_and_mutated_asset_is_blocked(self):
        self.submit.side_effect=TimeoutError('unknown')
        args=dict(asset_id=self.asset['id'],control_kind='depth',seed=42)
        with patch('creative_os.fun_control_jobs.verify_video',return_value={}):
            with self.assertRaises(TimeoutError):generate(self.s,self.shot['id'],'x',**args)
            self.assertEqual(generate(self.s,self.shot['id'],'x',**args)['status'],'submission_failed')
        self.submit.assert_called_once();self.file.write_bytes(b'changed')
        ns={'_CREATIVE_OS':self.s,'_save_comfy_input_video':Mock()}
        with self.assertRaises(CreativeError):apply_in_worker(ns,{},self.req)
        ns['_save_comfy_input_video'].assert_not_called()

    def test_patch_preserves_original_and_only_changes_guided_model(self):
        g={'m':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_fl2va_pruned_int8_convrot.safetensors'}},
           'g':{'class_type':'BasicGuider','inputs':{'model':['m',0]}},
           'c':{'class_type':'MiniMaxH3ImageToVideo','inputs':{'vae':['v',0]}}}
        p=patch_graph(g,'safe/input.mp4',1)
        self.assertEqual(g['g']['inputs']['model'],['m',0])
        from h3_acceleration import model_chain, validate_spectrum
        self.assertTrue(validate_spectrum(p))
        self.assertIn('creative_control_apply', [key for key, _ in model_chain(p,p['g']['inputs']['model'][0])])
        self.assertEqual(p['creative_control_apply']['inputs']['model'],['m',0])
        with self.assertRaises(CreativeError):patch_graph(g,'../escape.mp4',1)
        with self.assertRaises(CreativeError):patch_graph(p,'safe.mp4',1)

    def test_import_is_bounded_and_project_scoped(self):
        with patch('creative_os.fun_control_jobs.verify_video',return_value={}):
            asset=import_control(self.s,b'fixture-video','../../control.mp4')
        path,record=self.s.assets.resolve(asset['id'],'maestro_control')
        self.assertTrue(path.is_relative_to(self.s.assets.root));self.assertEqual(record['sha256'],file_hash(path))
        with self.assertRaises(CreativeError):import_control(self.s,b'','empty.mp4')
        with self.assertRaises(CreativeError):import_control(self.s,b'data','control.exe')

    def test_wrong_video_geometry_rejected(self):
        with patch('creative_os.fun_control.subprocess.run',return_value=Mock(stdout=b'{"streams":[{"codec_type":"video","width":640,"height":480,"nb_frames":"20","r_frame_rate":"24/1"}]}')):
            with self.assertRaises(CreativeError):verify_video(self.file)
