import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.motion_jobs import prepare, generate, sync
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class MotionJobsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.submit=Mock(return_value='job1')
        self.job={'status':'running','engine_id':'minimax_h3'}
        self.bridge=Bridge(self.submit,lambda _:self.job,
            lambda:{'optional':{'h3_motion_director':{'enabled':True}}},
            lambda o:self.root/o['filename'],Mock(),provenance=lambda _: {'workflow_hash':'a'*64})
        self.service=CreativeService(self.root/'state',self.root,self.bridge)
        self.shots=[]
        for i in range(2):
            ir=sample();ir['shot_id']='SH'+str(i)
            self.shots.append(self.service.save_shot(ir))
        self.plan=prepare(self.service,[s['id'] for s in self.shots],seed=42)

    def tearDown(self): self.tmp.cleanup()

    def test_submit_once_and_separate_artifacts_without_approval(self):
        b=generate(self.service,self.plan['id'],'key')
        self.assertEqual(generate(self.service,self.plan['id'],'key'),b)
        self.submit.assert_called_once()
        for i in range(2): (self.root/f'{i}.mp4').write_bytes(f'fake-video-{i}'.encode())
        self.job={'status':'done','engine_id':'minimax_h3','prompt_id':'prompt1','result':{
            'creative_motion':self.plan['compiled'],'seed':42,
            'outputs':[{'kind':'video','filename':f'{i}.mp4'} for i in range(2)]}}
        completed=sync(self.service,b['id'])
        self.assertEqual(len(completed['generation_ids']),2)
        records=[self.service.sync(g) for g in completed['generation_ids']]
        self.assertNotEqual(records[0]['artifacts'][0]['sha256'],records[1]['artifacts'][0]['sha256'])
        self.assertTrue(all(len(r['artifacts'])==1 and r['human_verdict'] is None and r['actual_seed'] is None for r in records))
        self.assertEqual(sync(self.service,b['id']),completed)

    def test_unknown_submission_is_not_replayed(self):
        self.submit.side_effect=TimeoutError('uncertain')
        with self.assertRaises(TimeoutError): generate(self.service,self.plan['id'],'key')
        retry=generate(self.service,self.plan['id'],'key')
        self.assertEqual(retry['state'],'SUBMISSION_FAILED')
        self.submit.assert_called_once()

    def test_stale_plan_and_unmatched_outputs_block(self):
        ir=sample();ir['shot_id']='SH0';ir['content']['description']='edited'
        self.service.save_shot(ir,expected=self.shots[0]['revision'])
        with self.assertRaises(CreativeError): generate(self.service,self.plan['id'],'key')
        self.submit.assert_not_called()
        p=prepare(self.service,[s['id'] for s in self.shots],seed=42)
        b=generate(self.service,p['id'],'key')
        self.job={'status':'done','result':{'outputs':[]}}
        with self.assertRaises(CreativeError): sync(self.service,b['id'])
        self.assertEqual(self.service.store.list('generations'),[])
