import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.timeline_director import compile_timeline
from creative_os.timeline_jobs import generate,prepare
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.submit=Mock(return_value='timeline-job')
        self.job={'status':'running'};self.prov={}
        self.bridge=Bridge(self.submit,lambda _:self.job,lambda:{'optional':{'h3_timeline_director':{'enabled':True}}},
            Mock(return_value=None),Mock(),provenance=lambda _:self.prov)
        self.s=CreativeService(Path(self.tmp.name),Path(self.tmp.name),self.bridge)
        self.ir=sample();self.ir['duration_seconds']=10;self.shot=self.s.save_shot(self.ir)
    def tearDown(self): self.tmp.cleanup()

    def test_planning_reports_native_overlap_without_submitting(self):
        plan=prepare(self.s,self.shot['id'],seed=42)
        self.assertEqual(plan['output_frames'],226)
        self.assertEqual(plan['segment_frames'],124)
        self.assertFalse(plan['generation_submitted']);self.submit.assert_not_called()
        self.assertEqual(self.s.store.get('shots',self.shot['id'])['ir'],self.ir)

    def test_contract_blocks_wrong_engine_audio_refs_and_too_short(self):
        for mutator in (lambda ir:ir['generation'].update(preferred_engine='ltx25'),
                        lambda ir:ir['generation'].update(native_audio=True),
                        lambda ir:ir.update(control_source={'video':'asset://test/input'}),
                        lambda ir:ir.update(duration_seconds=5)):
            ir=sample();ir['duration_seconds']=10;mutator(ir)
            with self.assertRaises(CreativeError):compile_timeline(ir,seed=42)

    def test_uncertain_submission_is_never_replayed(self):
        self.submit.side_effect=TimeoutError('uncertain')
        with self.assertRaises(TimeoutError):generate(self.s,self.shot['id'],'once',seed=42)
        self.assertEqual(generate(self.s,self.shot['id'],'once',seed=42)['status'],'submission_failed')
        self.submit.assert_called_once()
        with self.assertRaises(CreativeError):generate(self.s,self.shot['id'],'once',seed=43)

    def test_only_matching_workflow_and_one_video_enter_review(self):
        record=generate(self.s,self.shot['id'],'once',seed=42)
        self.assertIsNone(record['human_verdict'])
        self.job={'status':'done','result':{'prompt_id':'p','outputs':[{'kind':'video','filename':'test.mp4'}],
            'creative_timeline':record['timeline_contract']}}
        with self.assertRaises(CreativeError):self.s.sync(record['id'])
        self.prov={'workflow_hash':record['timeline_contract']['workflow_hash']}
        self.job['result']['outputs'].append({'kind':'video','filename':'extra.mp4'})
        with self.assertRaises(CreativeError):self.s.sync(record['id'])
        self.job['result']['outputs'].pop()
        done=self.s.sync(record['id'])
        self.assertEqual(done['status'],'done');self.assertIsNone(done['human_verdict'])
