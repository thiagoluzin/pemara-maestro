import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from creative_os.bridge import Bridge, normalize_save_video
from creative_os.service import CreativeService
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class ServiceTests(unittest.TestCase):
    def test_idempotent_submission_and_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            submit=Mock(return_value="job1")
            bridge=Bridge(submit, lambda _: {"status":"running","progress":23},
                          lambda: {"engines":{"minimax_h3":{"runnable":True}}}, lambda _: None, Mock())
            service=CreativeService(Path(d)/"state",Path(d)/"projects",bridge)
            shot=service.save_shot(sample())
            a=service.generate(shot["id"],{},"request1")
            self.assertEqual(a["id"],service.generate(shot["id"],{},"request1")["id"])
            submit.assert_called_once()
            with self.assertRaises(CreativeError): service.generate(shot["id"],{"seed":1},"request1")
            self.assertEqual(service.sync(a["id"])["progress"],23)
            self.assertIsNone(service.sync(a["id"])["human_verdict"])

    def test_exporter_compatibility_preserves_sampling(self):
        graph={"1":{"class_type":"SaveVideo","inputs":{"format":"mp4","codec":"h264"}}}
        result=normalize_save_video(graph,True)
        self.assertEqual(result["1"]["inputs"]["format.codec"],"h264")
        self.assertIn("codec",graph["1"]["inputs"])
