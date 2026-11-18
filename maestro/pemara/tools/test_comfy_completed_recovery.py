import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import comfy_completed_recovery as recovery
import comfy_lifecycle as lifecycle


class CompletedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name); self.state = base/'state'; self.state.mkdir()
        self.proc = Mock(pid=42); self.proc.create_time.return_value=1000
        self.proc.cpu_times.return_value=SimpleNamespace(user=10, system=0)
        self.proc.memory_info.return_value=SimpleNamespace(rss=100_000_000)
        self.proc.children.return_value=[]
        self.active={'pid':42,'created':1000}
        (self.state/'runtime.json').write_text(json.dumps(self.active))
        self.request={'authorization':'Se vira e arruma','runtime':self.active,
                      'requested_at':time.time(),'idle_sample_at':time.time()-90,'idle_sample_cpu':10}
        self.write_request()
        self.output=base/'ferramentas/ComfyUI/output/REBELIAO_EP03_FHD60_20261103/T01_blank_seed3b_rife60_80eff5a1ff1b.mp4'
        self.output.parent.mkdir(parents=True); self.output.write_bytes(b'fixture')
        digest='3a8e3476c31b75ee6fa5c82e7e6ddd62d9a041753047c481b58f824e53347d1c'
        Path(str(self.output)+'.upscaling.json').write_text(json.dumps({'technical_pass':True,'output_sha256':digest,'frames':900,'fps':60}))
        self.l=SimpleNamespace(STATE=self.state, BASE=base, exact_process=Mock(return_value=self.proc),
                               listener=Mock(return_value=None),write_json=lifecycle.write_json,
                               register=Mock(),psutil=Mock())
        self.l.psutil.wait_procs.return_value=([self.proc],[])
        self.addCleanup(patch.stopall)
        patch.object(recovery.hashlib,'file_digest',return_value=Mock(hexdigest=Mock(return_value=digest))).start()
    def write_request(self):
        (self.state/'completed_ep03_recovery.json').write_text(json.dumps(self.request))
    def test_completed_idle_owner_recovery(self):
        self.assertTrue(recovery.recover(self.l,42)['owner_authorized_ep03_recovery'])
        self.proc.kill.assert_called_once()
    def test_pid_reuse_rejected(self):
        self.proc.create_time.return_value=1001
        with self.assertRaises(RuntimeError): recovery.recover(self.l,42)
        self.proc.kill.assert_not_called()
    def test_active_work_rejected(self):
        self.proc.cpu_times.return_value=SimpleNamespace(user=11,system=0)
        with self.assertRaises(RuntimeError): recovery.recover(self.l,42)
        self.proc.kill.assert_not_called()
    def test_child_render_rejected(self):
        self.proc.children.return_value=[Mock()]
        with self.assertRaises(RuntimeError): recovery.recover(self.l,42)
        self.proc.kill.assert_not_called()
    def test_live_listener_rejected(self):
        self.l.listener.return_value=42
        with self.assertRaises(RuntimeError): recovery.recover(self.l,42)
        self.proc.kill.assert_not_called()
    def test_missing_owner_authorization_rejected(self):
        self.request['authorization']=''; self.write_request()
        with self.assertRaises(RuntimeError): recovery.recover(self.l,42)
        self.proc.kill.assert_not_called()


if __name__=='__main__': unittest.main()
