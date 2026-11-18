import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import dlss5_content_policy as p
import dlss5_finishing as d
import actor_protection as a


class ContentRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'anchor.png';Image.new('RGB',(8,8),(20,40,60)).save(self.source)
    def tearDown(self): self.tmp.cleanup()
    def test_anchor_builder_is_integral_for_every_content_kind(self):
        for kind in ('live_action','mixed','animation'):
            graph=a.build_anchor_workflow('native.png',content_kind=kind)
            self.assertEqual(p.graph_kind(graph),kind);self.assertEqual(p.graph_stage(graph),'final')
            self.assertEqual(graph['2']['class_type'],'SaveImage')
            self.assertFalse(any(node['class_type']=='ImageToMask' or 'actor_mask' in node['inputs'] for node in graph.values()))
        with self.assertRaises(ValueError):a.build_anchor_workflow('native.png',content_kind='unknown')

    def test_unknown_blocks_before_gpu(self):
        for kind in ['unknown']:
            with patch.object(d,'preflight') as gpu,patch.object(d,'_image') as renderer:
                with self.assertRaises(d.DLSS5RequiredError):d.finish_file(self.source,content_kind=kind)
                gpu.assert_not_called();renderer.assert_not_called()
            self.assertFalse(list(self.root.glob('*.before_dlss5.*')))
    def test_live_and_mixed_finish_full_frame_without_actor_masks(self):
        for kind in ('live_action','mixed'):
            source=self.root/(kind+'.png');Image.new('RGB',(8,8),(20,40,60)).save(source)
            def render(native,dest,log):
                Image.new('RGB',(8,8),(90,80,70)).save(dest);return {'frames':1}
            with patch.object(d,'preflight'),patch.object(d,'_image',side_effect=render) as renderer,patch.object(a,'compose_image') as composite:
                proof=d.finish_file(source,content_kind=kind)
                self.assertEqual(d.finish_file(source,content_kind=kind),proof)
            self.assertEqual(renderer.call_count,1);composite.assert_not_called()
            self.assertEqual(proof['content_kind'],kind)
            self.assertEqual(proof['processing_mode'],'full_frame')
            self.assertEqual(proof['coverage_percent'],100)
            self.assertFalse(proof['automatic_masks'])
            self.assertFalse(proof['actor_protection_applied'])
            self.assertEqual(proof['parameters']['detail'],1)
            self.assertTrue(Path(proof['source']).exists())

    def test_animation_can_finish_full_frame_and_is_recorded(self):
        def render(source,dest,log):
            Image.new('RGB',(8,8),(90,80,70)).save(dest);return {'frames':1}
        with patch.object(d,'preflight'),patch.object(d,'_image',side_effect=render) as renderer:
            proof=d.finish_file(self.source,content_kind='animation')
            self.assertEqual(d.finish_file(self.source,content_kind='animation'),proof)
        self.assertEqual(renderer.call_count,1)
        self.assertEqual(proof['content_kind'],'animation')
        self.assertEqual(proof['processing_mode'],'full_frame')
        with self.assertRaises(d.DLSS5RequiredError):d.finish_file(self.source,content_kind='live_action')
    def test_historical_receipt_is_readable_but_cannot_be_live_action(self):
        old={'profile':d.PROFILE,'technical_pass':True,'output_sha256':d.sha(self.source)}
        d._atomic_json(d.receipt_path(self.source),old)
        self.assertEqual(d.finish_file(self.source),old)
        with self.assertRaises(d.DLSS5RequiredError):d.finish_file(self.source,content_kind='mixed')
    def test_declared_type_contract_is_bound_to_source_hash(self):
        d._atomic_json(p.sidecar(self.source),{'schema_version':'1.0','source_sha256':'wrong','content_kind':'animation'})
        with patch.object(d,'_image') as renderer,self.assertRaises(d.DLSS5RequiredError):d.finish_file(self.source)
        renderer.assert_not_called()
    def test_type_contract_remains_idempotent_after_finishing(self):
        d._atomic_json(p.sidecar(self.source),{'schema_version':'1.0','source_sha256':d.sha(self.source),'content_kind':'animation'})
        def render(source,dest,log):Image.new('RGB',(8,8),(1,2,3)).save(dest);return {}
        with patch.object(d,'preflight'),patch.object(d,'_image',side_effect=render) as renderer:
            result=d.finish_file(self.source);self.assertEqual(d.finish_file(self.source),result)
        self.assertEqual(renderer.call_count,1)
    def test_conflicting_workflow_declarations_block(self):
        graph={str(i):{'class_type':'PemaraDLSS5ContentPolicy','inputs':{'content_kind':kind}} for i,kind in enumerate(['animation','live_action'])}
        with self.assertRaises(ValueError):p.graph_kind(graph)
        graph={'1':{'class_type':'PemaraSaveActorProtectedImage','inputs':{}}}
        self.assertEqual(p.graph_kind(graph),'live_action')
        self.assertEqual(p.graph_stage(graph),'final')
    def test_native_live_action_preview_never_qualifies_as_dlss_final(self):
        original=self.source.read_bytes()
        proof=d.preserve_native_preview(self.source,'live_action')
        self.assertFalse(proof['technical_pass']);self.assertFalse(proof['final_delivery_allowed'])
        self.assertEqual(self.source.read_bytes(),original);self.assertIsNone(d.valid_receipt(self.source))
        copy=self.root/'copy.png';copy.write_bytes(original)
        d.carry_receipt(self.source,copy)
        self.assertIsNotNone(d.staging_receipt(copy));self.assertIsNone(d.valid_receipt(copy))
        with self.assertRaises(d.DLSS5RequiredError):d.inherit_assembly([self.source,copy],copy)
    def test_content_context_does_not_leak_to_next_job(self):
        @p.with_content_kind
        def run():return p.current_kind()
        self.assertEqual(run(content_kind='animation'),'animation')
        self.assertEqual(run(),'unknown');self.assertEqual(p.current_kind(),'unknown')
    def test_lossless_loader_preserves_all_byte_values_and_mask_white(self):
        pixels=np.arange(256,dtype=np.uint8).reshape(16,16)
        for mode in ['L','RGBA']:
            path=self.root/(mode+'.png')
            raw=pixels if mode=='L' else np.stack([pixels,np.flip(pixels,0),np.flip(pixels,1),pixels],axis=-1)
            Image.fromarray(raw,mode=mode).save(path)
            rgb,alpha=a.load_lossless_image(path)
            expected=np.array(Image.open(path).convert('RGBA'))
            np.testing.assert_array_equal(np.rint(rgb*255).astype(np.uint8),expected[...,:3])
            np.testing.assert_array_equal(np.rint((1-alpha)*255).astype(np.uint8),expected[...,3])
            self.assertEqual(int(np.rint(rgb*255).max()),255)


if __name__=='__main__':unittest.main()
