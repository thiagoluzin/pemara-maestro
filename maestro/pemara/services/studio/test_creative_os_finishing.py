import tempfile
import unittest
import os
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock,patch
from creative_os.assets import file_hash
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.finishing import Finishing
from creative_os.ir import CreativeError


class FinishingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.s=CreativeService(self.root,self.root,Bridge(Mock(),Mock(),Mock(),Mock(),Mock()))
        self.source=self.root/'approved.mp4'; self.source.write_bytes(b'original')
        self.artifact={'relative_path':'approved.mp4','sha256':file_hash(self.source),'kind':'video'}
        self.s.store.put('generations',{'human_verdict':'approved'},entity_id='g1')
        self.s.store.put('masters',{'generation_id':'g1','state':'APPROVED','artifact':self.artifact},entity_id='m1')
        def executor(job,source,target):
            output=target/'candidate.mp4'; output.write_bytes(b'candidate'); return output
        self.executor=Mock(side_effect=executor)
        self.f=Finishing(self.s,{'native':{'enabled':True},'latent':{'enabled':False}},self.executor,lambda:{'ok':True},lambda _:nullcontext())
    def tearDown(self): self.f.stop.set(); self.tmp.cleanup()

    def enqueue(self,key='one'):
        with patch.object(self.f,'start'):
            return self.f.enqueue('m1','native',key)

    def test_approval_hash_and_missing_plugin_gates(self):
        with self.assertRaises(CreativeError): self.f.enqueue('m1','latent','one')
        self.source.write_bytes(b'changed')
        with self.assertRaises(CreativeError): self.enqueue()
        self.executor.assert_not_called()

    def test_latent_hq_blocks_legacy_master_before_queue(self):
        self.f.profiles['h3_latent_2stage_v1']={'enabled':True,'requires_captured_latent':True}
        with self.assertRaisesRegex(CreativeError,'latent'):
            self.f.enqueue('m1','h3_latent_2stage_v1','legacy')
        self.assertEqual(self.s.store.list('hq_jobs'),[])
        self.executor.assert_not_called()

    def test_idempotent_candidate_never_autoapproved(self):
        a=self.enqueue();self.assertEqual(a['id'],self.enqueue()['id'])
        with patch('creative_os.finishing.inspect_video',return_value={'pass':True}): self.f.run()
        result=self.s.store.get('hq_jobs',a['id'])
        self.assertEqual(result['state'],'PENDING_HUMAN_REVIEW')
        self.assertIsNone(result['human_verdict'])
        self.assertEqual(self.source.read_bytes(),b'original')
        self.executor.assert_called_once()
        self.f.run();self.executor.assert_called_once()
        self.f.review(a['id'],'approved',result['artifacts'][0]['sha256'])
        self.assertEqual(self.s.store.get('hq_jobs',a['id'])['state'],'APPROVED')

    def test_revoke_before_worker_and_no_replay_after_crash(self):
        a=self.enqueue()
        self.s.store.put('masters',{'generation_id':'g1','state':'REVOKED','artifact':self.artifact},entity_id='m1',create=False)
        self.f.run(); self.executor.assert_not_called()
        self.assertEqual(self.s.store.get('hq_jobs',a['id'])['state'],'FAILED')
        self.s.store.put('hq_jobs',{'state':'RUNNING','worker_pid':99999999},entity_id='crashed')
        with patch.object(self.f,'start'): self.f.recover()
        self.assertEqual(self.s.store.get('hq_jobs','crashed')['state'],'INTERRUPTED')

    def test_queue_cancel_never_runs(self):
        a=self.enqueue();self.f.cancel(a['id']);self.f.run();self.executor.assert_not_called()

    def test_finishing_child_keeps_lease_if_parent_exits(self):
        from gpu_lease import GpuLeaseRegistry,GpuLeaseBusy
        lease=GpuLeaseRegistry(self.root/'lease.json')
        parent=os.getpid()
        lease.acquire(owner='studio',operation='hq',job_id='job')
        with patch('gpu_lease.os.getpid',return_value=123456):
            record=lease.adopt_child_process('job',expected_parent_pid=parent)
        self.assertEqual(record['pid'],123456)
        with patch.object(lease,'_pid_is_running',return_value=True):
            with self.assertRaises(GpuLeaseBusy):lease.acquire(owner='new-studio',operation='video',job_id='other')
        with self.assertRaises(GpuLeaseBusy):lease.adopt_child_process('other',expected_parent_pid=parent)

    def test_incident_pause_survives_worker_restart(self):
        self.s.store.put('workers',{'paused':True},entity_id='hq')
        self.f.start()
        self.assertIsNone(self.f.worker)
