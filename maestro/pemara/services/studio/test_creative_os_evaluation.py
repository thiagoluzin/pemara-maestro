import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from creative_os.assets import file_hash
from creative_os.bridge import Bridge
from creative_os.service import CreativeService
from creative_os.evaluation import evaluate,verdict
from creative_os.ir import CreativeError


class EvaluationTests(unittest.TestCase):
    def test_technical_pass_never_approves_and_master_hash_is_fixed(self):
        with tempfile.TemporaryDirectory() as d:
            s=CreativeService(d,d,Bridge(Mock(),Mock(),Mock(),Mock(),Mock()))
            path=Path(d)/"video.mp4"; path.write_bytes(b"video")
            sha=file_hash(path)
            s.store.put("generations",{"status":"done","engine_id":"minimax_h3","project_id":"film","artifacts":[{"relative_path":"video.mp4","kind":"video","sha256":sha}]},entity_id="g1")
            with self.assertRaises(CreativeError): verdict(s,"g1","approved",sha)
            with patch("creative_os.evaluation.inspect_video",return_value={"pass":True}):
                e=evaluate(s,"g1")
            self.assertEqual(e["decision"],"PENDING_HUMAN_REVIEW")
            self.assertTrue(all(v is None for v in e["scores"].values()))
            self.assertEqual(verdict(s,"g1","approved",sha)["master"]["state"],"APPROVED")
            verdict(s,"g1","rejected",sha)
            self.assertEqual(s.store.get("masters","g1")["state"],"REVOKED")
            path.write_bytes(b"changed")
            with self.assertRaises(CreativeError): verdict(s,"g1","approved",sha)
