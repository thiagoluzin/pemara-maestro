import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.assets import file_hash
from creative_os.ir import CreativeError
from creative_os.semantic_critic import parse, workflow, execute
from creative_os.semantic_jobs import start, sync
from test_creative_os_ir import sample


class SemanticTests(unittest.TestCase):
    def test_advice_cannot_establish_identity_or_human_approval(self):
        row={'dimension':'identity','status':'no_visible_issue','evidence':'Same person.'}
        result=parse(json.dumps({'summary':'Consistent','observations':[row]}))
        self.assertEqual(result['observations']['identity']['status'],'uncertain')
        self.assertIsNone(result['human_verdict']);self.assertFalse(result['automatic_repair_allowed'])
        self.assertFalse(result['semantic_quality_proven'])

    def test_malformed_and_extra_approval_fields_rejected(self):
        for text in ('not JSON', '[]', '{"summary":"ok","observations":[],"approved":true}',
            '{"summary":"ok","observations":[{"dimension":"anatomy","status":"pass","evidence":"ok"}]}'):
            with self.assertRaises(CreativeError): parse(text)

    def test_factory_uses_local_image_and_no_enhancer(self):
        graph=workflow('original brief','sheet.png')
        self.assertEqual(graph['3']['class_type'],'TextGenerate')
        self.assertEqual(graph['3']['inputs']['sampling_mode'],'off')
        for image in ('../secret.png','C:/secret.png','/secret.png'):
            with self.assertRaises(CreativeError): workflow('brief',image)

    def test_worker_graph_identity_is_stable_across_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            output=[{'kind':'text','node':'4','text':'{"summary":"cube","observations":[]}'}]
            queue=Mock(return_value=('prompt-id',output))
            ns={'COMFY_INPUT_DIR':folder,'_queue_comfy_workflow':queue}
            a=execute(ns,'brief',b'fixture-sheet')
            b=execute(ns,'brief',b'fixture-sheet',resume_prompt_id='prompt-id')
            self.assertEqual(a['workflow_hash'],b['workflow_hash'])
            self.assertEqual(queue.call_args.kwargs['resume_prompt_id'],'prompt-id')


class SemanticJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.submit=Mock(return_value='job');self.job={};self.provenance={}
        bridge=Bridge(self.submit,lambda _:self.job,Mock(),Mock(),Mock(),provenance=lambda _:self.provenance)
        self.s=CreativeService(root,root,bridge)
        p=root/'video.mp4';p.write_bytes(b'fixture video');self.sha=file_hash(p)
        self.g=self.s.store.put('generations',{'status':'done','engine_id':'minimax_h3','ir':sample(),
            'human_verdict':None,'artifacts':[{'kind':'video','relative_path':'video.mp4','sha256':self.sha}]})
        self.s.sync=Mock(return_value=self.g)
        self.sheet=patch('creative_os.semantic_jobs.contact_sheet',return_value=(b'sheet',[0,1,2,3,4,5]));self.sheet.start()
    def tearDown(self): self.sheet.stop();self.tmp.cleanup()
    def finish(self,r):
        self.provenance={'workflow_hash':r['workflow_hash']}
        self.job={'status':'done','result':{'prompt_id':'prompt','text':'{"summary":"cube","observations":[]}',
            **{k:r[k] for k in ('source_prompt_hash','sheet_sha256','workflow_hash')}}}
    def test_idempotency_and_no_master_mutation(self):
        r=start(self.s,self.g['id'],self.sha,'request')
        self.assertEqual(start(self.s,self.g['id'],self.sha,'request'),r);self.submit.assert_called_once()
        self.finish(r);done=sync(self.s,r['id']);self.assertEqual(done['state'],'DONE')
        self.assertEqual(sync(self.s,r['id']),done)
        self.assertEqual(self.s.store.list('masters'),[])
        self.assertIsNone(self.s.store.get('generations',self.g['id'])['human_verdict'])
    def test_uncertain_submit_is_not_replayed(self):
        self.submit.side_effect=TimeoutError('uncertain')
        with self.assertRaises(TimeoutError): start(self.s,self.g['id'],self.sha,'request')
        self.assertEqual(start(self.s,self.g['id'],self.sha,'request')['state'],'SUBMISSION_FAILED')
        self.submit.assert_called_once()
    def test_provenance_mismatch_does_not_publish_review(self):
        r=start(self.s,self.g['id'],self.sha,'request');self.finish(r);self.provenance={}
        done=sync(self.s,r['id']);self.assertEqual(done['state'],'PROVENANCE_MISSING')
        self.assertNotIn('review',done)
