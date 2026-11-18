import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.rewriter_jobs import start,sync
from creative_os.prompt_proposals import apply
from creative_os.h3_rewriter import workflow
from creative_os.ir import CreativeError,digest
from test_creative_os_ir import sample


class RewriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.submit=Mock(return_value='rewrite-job')
        self.job={'status':'running'};self.provenance={}
        self.bridge=Bridge(self.submit,lambda _:self.job,lambda:{'optional':{'h3_prompt_rewriter':{'enabled':True}}},Mock(),Mock(),provenance=lambda _:self.provenance)
        self.s=CreativeService(Path(self.tmp.name),Path(self.tmp.name),self.bridge)
        self.shot=self.s.save_shot(sample())
    def tearDown(self): self.tmp.cleanup()

    def finish(self,record):
        self.provenance={'workflow_hash':record['workflow_hash']}
        self.job={'status':'done','result':{'prompt_id':'prompt-1','text':'A reviewed candidate description',
            'rewriter':{'workflow_hash':record['workflow_hash'],'source_prompt_hash':record['source_prompt_hash']}}}

    def test_worker_result_becomes_unapplied_proposal_once(self):
        record=start(self.s,self.shot['id'],'request',23)
        self.assertEqual(start(self.s,self.shot['id'],'request',23),record)
        self.submit.assert_called_once();self.finish(record)
        done=sync(self.s,record['id'])
        self.assertEqual(sync(self.s,record['id']),done)
        p=self.s.store.get('prompt_proposals',done['proposal_id'])
        self.assertTrue(p['provenance_verified'])
        self.assertFalse(p['semantic_constraints_verified'])
        with self.assertRaises(CreativeError): apply(self.s,p['id'])
        self.assertEqual(self.s.store.get('shots',self.shot['id'])['ir_hash'],self.shot['ir_hash'])

    def test_stale_source_never_overwrites_or_creates_applicable_proposal(self):
        record=start(self.s,self.shot['id'],'request',23);self.finish(record)
        ir=sample();ir['content']['description']='Owner changed brief'
        self.s.save_shot(ir,expected=self.shot['revision'])
        self.assertEqual(sync(self.s,record['id'])['state'],'STALE_IR')
        self.assertEqual(self.s.store.list('prompt_proposals'),[])

    def test_unknown_submission_and_wrong_provenance_do_not_replay(self):
        self.submit.side_effect=TimeoutError('uncertain')
        with self.assertRaises(TimeoutError): start(self.s,self.shot['id'],'request',23)
        self.assertEqual(start(self.s,self.shot['id'],'request',23)['state'],'SUBMISSION_FAILED')
        self.submit.assert_called_once()
        self.submit.side_effect=None
        record=start(self.s,self.shot['id'],'other',23);self.finish(record);self.provenance={}
        self.assertEqual(sync(self.s,record['id'])['state'],'PROVENANCE_MISSING')

    def test_no_download_or_auto_application_in_factory(self):
        graph=workflow('Original brief',5,23)
        self.assertFalse(graph['2']['inputs']['auto_download'])
        self.assertFalse(graph['1']['inputs']['keep_model_loaded'])
        for seed in (-1,True,None):
            with self.assertRaises(CreativeError): workflow('Original',5,seed)
