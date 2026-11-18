import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import comfy_lifecycle as l


class OwnedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.state = self.root / 'state'
        self.state.mkdir(); self.base = self.root / 'maestro/pemara'
        self.progress = self.root / 'outputs/cupcake_lunar_gemeas_kpop_20261004/revisao_r05_animacao_narrativa/final_upscale_20261006/progress.json'
        self.progress.parent.mkdir(parents=True)
        self.prompt = 'ed7a518d-233f-4eaf-bf6e-b31a61d8c6e1'
        self.progress.write_text(json.dumps({'stages':[{'status':'submitted','prompt_id':self.prompt}]}))
        self.active = {'pid':42,'created':1000}
        (self.state/'runtime.json').write_text(json.dumps(self.active))
        self.request = {'runtime':self.active,'requested_at':1990,'observed_missing_at':1900,'progress':str(self.progress),'owned_prompt_id':self.prompt}
        self.write_request()
        self.proc = Mock(pid=42); self.proc.create_time.return_value=1000; self.proc.children.return_value=[]
        self.addCleanup(patch.stopall)
        patch.object(l,'STATE',self.state).start(); patch.object(l,'BASE',self.base).start()
        patch.object(l,'exact_process',return_value=self.proc).start()
        patch.object(l.time,'time',return_value=2000).start()
        self.listener = patch.object(l,'listener',return_value=None).start()
        patch.object(l,'register').start(); patch.object(l.psutil,'wait_procs',return_value=([self.proc],[])).start()
    def write_request(self):
        (self.state/'owned_listener_recovery.json').write_text(json.dumps(self.request))
    def test_explicit_owned_recovery(self):
        self.assertTrue(l.stop_owned_lost_listener(42)['recovered_owned_lost_listener'])
        self.proc.kill.assert_called_once()
    def test_pid_reuse_refuses(self):
        self.proc.create_time.return_value=1001
        with self.assertRaises(RuntimeError): l.stop_owned_lost_listener(42)
        self.proc.kill.assert_not_called()
    def test_listener_race_refuses(self):
        self.listener.return_value=42
        with self.assertRaises(RuntimeError): l.stop_owned_lost_listener(42)
        self.proc.kill.assert_not_called()
    def test_multiple_unfinished_jobs_refuse(self):
        self.progress.write_text(json.dumps({'stages':[{'status':'submitted','prompt_id':self.prompt}]*2}))
        with self.assertRaises(RuntimeError): l.stop_owned_lost_listener(42)
        self.proc.kill.assert_not_called()
    def test_expired_recovery_refuses(self):
        self.request['requested_at']=1800; self.write_request()
        with self.assertRaises(RuntimeError): l.stop_owned_lost_listener(42)
        self.proc.kill.assert_not_called()

if __name__=='__main__': unittest.main()
