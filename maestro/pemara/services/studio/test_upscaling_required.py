import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import upscaling_required as p

class MandatoryUpscaleTests(unittest.TestCase):
    def test_exact_24_to_60_counts_and_fractional_duration_block(self):
        self.assertEqual(p.output_frame_count(360,'24'),900)
        self.assertEqual(p.output_frame_count(300,'30'),600)
        self.assertEqual(p.output_frame_count(900,'60'),900)
        with self.assertRaises(ValueError):
            p.output_frame_count(25,'24')

    def test_contain_geometry_retains_re1_ratio(self):
        self.assertEqual(p.contain_dimensions(768,1344,1080,1920),(1080,1890))
        self.assertEqual(p.contain_dimensions(768,1344,2160,3840),(2160,3780))
        self.assertEqual(p.contain_dimensions(768,1344,1440,2560),(1440,2520))

    def test_six_profiles_no_fallback_audio_is_preserved(self):
        for w,h in p.TARGETS:
            profile=p.canonical_profile(w,h)
            self.assertTrue(profile['required'])
            self.assertFalse(profile['fallback_allowed'])
            self.assertEqual(profile['target']['fps'],60)
            self.assertFalse(profile['audio']['new_foley_generation'])
        with self.assertRaises(ValueError):
            p.profile_id(720,1280)

    def test_reject_tampered_sampler_model_and_disconnected_seed(self):
        graph=p.build_workflow('RE1_NATIVE24_FOLEY.mp4',768,1344,1080,1920,'test',content_kind='animation')
        p.assert_graph(graph)
        cached=copy.deepcopy(graph)
        cached['15']['is_changed']=[float('nan')]
        cached['1']['is_changed']=[1234.5]
        p.assert_graph(cached)
        for nid,key,value in [('6','unet_name','seedvr2_7b_int8_convrot.safetensors'),
                              ('10','steps',2),('15','images',['3',0])]:
            other=copy.deepcopy(graph)
            other[nid]['inputs'][key]=value
            with self.assertRaises(ValueError):
                p.assert_graph(other)

    def test_reject_profile_opt_out(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json'
            profile=p.canonical_profile(1080,1920)
            path.write_text(json.dumps(profile),encoding='utf-8')
            self.assertEqual(p.load_profile(path),profile)
            profile['required']=False
            path.write_text(json.dumps(profile),encoding='utf-8')
            with self.assertRaises(ValueError):
                p.load_profile(path)

    def test_live_and_mixed_route_without_seed_at_all_six_sizes(self):
        for kind in ('live_action','mixed'):
            for w,h in p.TARGETS:
                graph=p.build_workflow('native.mp4',1280,720,w,h,'test',content_kind=kind)
                profile=p.assert_graph(graph)
                self.assertEqual(profile['pipeline_version'],p.CONVENTIONAL_PIPELINE)
                self.assertEqual(len(graph),2)
                self.assertNotIn('seedvr2',profile)
                self.assertEqual(graph['15']['inputs']['source_video'],['1',0])
                self.assertEqual(p.load_profile(p.PROFILE_DIR/(profile['profile_id']+'.json')),profile)
                graph['15']['inputs']['source_video']=['99',0]
                with self.assertRaises(ValueError): p.assert_graph(graph)

    def test_unknown_never_defaults_to_animation_for_new_workflow(self):
        with self.assertRaises(ValueError):
            p.build_workflow('native.mp4',1280,720,1920,1080,'test')
        with self.assertRaises(ValueError): p.pipeline_for('unknown')

    def test_lanczos_contain_pad_handles_upscale_downscale_and_portrait(self):
        self.assertEqual(p.spatial_filter(1280,720,1920,1080,lanczos=True),
                         'scale=1920:1080:flags=lanczos,pad=1920:1080:0:0:black')
        self.assertEqual(p.spatial_filter(3840,2160,1920,1080,lanczos=True),
                         'scale=1920:1080:flags=lanczos,pad=1920:1080:0:0:black')
        self.assertEqual(p.spatial_filter(768,1344,1080,1920,lanczos=True),
                         'scale=1080:1890:flags=lanczos,pad=1080:1920:0:15:black')

    def test_file_label_does_not_trigger_seed_detection(self):
        graph=p.build_workflow('sem_seedvr2.mp4',1280,720,1920,1080,'sem_seedvr2',content_kind='live_action')
        p.assert_graph(graph)

    def test_live_action_cannot_replace_seed_with_another_neural_spatial_upscaler(self):
        graph={'1':{'class_type':'ImageUpscaleWithModel','inputs':{}},
               '2':{'class_type':'PemaraDLSS5ContentPolicy','inputs':{'content_kind':'live_action'}}}
        with self.assertRaises(ValueError): p.assert_content_graph(graph)
        graph['1']['class_type']='ImageScale'
        graph['1']['inputs']['upscale_method']='lanczos'
        p.assert_content_graph(graph)

    def test_new_live_assembly_rejects_historical_seed_receipts(self):
        with patch.object(p,'valid_receipt',return_value={'pipeline_version':p.PIPELINE}):
            with self.assertRaises(ValueError): p.assert_finished_sources(['old.mp4'],'live_action')
            self.assertEqual(len(p.assert_finished_sources(['old.mp4'],'animation')),1)
        with patch.object(p,'valid_receipt',return_value={'pipeline_version':p.CONVENTIONAL_PIPELINE}):
            self.assertEqual(len(p.assert_finished_sources(['new.mp4'],'mixed')),1)

    def test_imported_seed_graph_live_mixed_unknown_block_before_execution(self):
        for kind in ('live_action','mixed','unknown'):
            graph={'1':{'class_type':'SeedVR2LoadDiTModel','inputs':{}},
                   '2':{'class_type':'PemaraDLSS5ContentPolicy','inputs':{'content_kind':kind}}}
            with self.assertRaises(ValueError): p.assert_content_graph(graph)
        graph['2']['inputs']['content_kind']='animation'
        p.assert_content_graph(graph)

    def test_live_graph_cannot_import_animation_profile_or_seed_node(self):
        graph=p.build_workflow('native.mp4',1280,720,1920,1080,'test',content_kind='live_action')
        graph['15']['inputs']['profile_id']=p.profile_id(1920,1080,'animation')
        with self.assertRaises(ValueError): p.assert_graph(graph)
        graph['15']['inputs']['profile_id']=p.profile_id(1920,1080,'live_action')
        graph['3']={'class_type':'UNETLoader','inputs':{'unet_name':p.SEED_MODEL}}
        with self.assertRaises(ValueError): p.assert_graph(graph)

    def test_full_receipt_needs_current_bytes_and_explicit_no_nr_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            video=Path(folder)/'clip.mp4'
            video.write_bytes(b'approved test bytes')
            receipt={'pipeline_version':p.PIPELINE,'technical_pass':True,
                     'output_sha256':p.dlss.sha(video)}
            p.receipt_path(video).write_text(json.dumps(receipt),encoding='utf-8')
            with patch.object(p.dlss,'valid_receipt',return_value=None):
                self.assertIsNone(p.valid_receipt(video))
            receipt['dlss5_applied']=False
            p.receipt_path(video).write_text(json.dumps(receipt),encoding='utf-8')
            with patch.object(p.dlss,'valid_receipt',side_effect=AssertionError('New video must not depend on DLSS')):
                self.assertTrue(p.valid_receipt(video))
                video.write_bytes(b'changed')
                self.assertIsNone(p.valid_receipt(video))

    def test_native_source_requires_retained_original_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            preview=Path(folder)/'preview.mp4'
            raw=Path(folder)/'raw.mp4'
            preview.write_bytes(b'finished')
            raw.write_bytes(b'native')
            proof={'source':str(raw),'source_sha256':p.dlss.sha(raw)}
            with patch.object(p.dlss,'valid_receipt',return_value=proof), patch.object(p.dlss,'_probe',return_value={
                    'streams':[{'codec_type':'video','width':768,'height':1344,
                                'avg_frame_rate':'24/1','nb_read_frames':'360'}]}):
                self.assertEqual(p.native_source(preview),raw.resolve())
                raw.write_bytes(b'wrong original')
                with self.assertRaises(ValueError):
                    p.native_source(preview)

    def test_assembly_refuses_missing_full_chain_even_with_dlss(self):
        with patch.object(p,'valid_receipt',return_value=None), patch.object(p.dlss,'valid_receipt',return_value={'technical_pass':True}):
            with self.assertRaises(ValueError):
                p.inherit_assembly(['unqualified.mp4'],'master.mp4')

if __name__=='__main__':
    unittest.main()
