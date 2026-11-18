"""Real CPU detector, raw-video save and upstream mask tests; no H3 sampling."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.argv=[sys.argv[0]]
RUNTIME=Path("D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara")
sys.path.insert(0,str(RUNTIME))
package=types.ModuleType("_pemara_face_test")
package.__path__=[str(RUNTIME/"custom_nodes/pemara_h3_face_refine")]
sys.modules[package.__name__]=package
adapter=importlib.import_module(package.__name__+".nodes")
fr=importlib.import_module(package.__name__+".upstream.face_refine_advanced")
import torch
import folder_paths


class FaceNodeCPU(unittest.TestCase):
    def test_no_face_preserves_frames_without_loading_h3_and_saves_raw(self):
        frames=torch.zeros(5,64,64,3)
        with tempfile.TemporaryDirectory() as out, patch.object(folder_paths,"get_output_directory",return_value=out), \
                patch.object(adapter,"_call",side_effect=AssertionError("No H3 model on no-face")):
            result=adapter.PemaraH3FaceRefine().refine(frames,None,None,"test",24.,7,"cpu/no_face")
            self.assertIs(result["result"][0],frames)
            report=json.loads(result["result"][1])
            self.assertEqual(report["status"],"no_face_detected_original_preserved")
            self.assertTrue(Path(report["original"]["path"]).is_file())
            self.assertFalse(report["audio_modified"]); self.assertFalse(report["identity_verified"])
            self.assertEqual(len(list(Path(out).rglob("*.json"))),1)

    def test_detector_failure_is_not_no_face(self):
        frames=torch.zeros(5,64,64,3)
        with patch.object(adapter,"_save_original",return_value={}), \
                patch.object(fr,"_detect_local_opencv_yunet",side_effect=RuntimeError("broken detector")):
            with self.assertRaisesRegex(RuntimeError,"broken detector"):
                adapter.PemaraH3FaceRefine().refine(frames,None,None,"",24.,0,"fail")

    def test_multi_face_tracks_consume_each_detection_once(self):
        data=[[{"box":[4.,4.,20.,20.],"confidence":.9},{"box":[38.,4.,55.,20.],"confidence":.9}] for _ in range(5)]
        tracks=list(adapter._track_detections(data,64,64,fr))
        self.assertEqual(len(tracks),2)
        self.assertEqual(sum(sum(len(x) for x in track) for track in tracks),10)
        self.assertEqual(sum(len(x) for x in data),10)

    def test_upstream_stitch_keeps_every_pixel_outside_mask(self):
        images=torch.rand(5,64,64,3)
        selected=[[{"box":[20.,15.,40.,38.],"confidence":.9}] for _ in range(5)]
        plan,crops,*_=adapter._plan(images,selected,{"model":fr.YUNET_2023MAR_RELATIVE},fr,384,"local_opencv_yunet",.5)
        repaired,mask,_,_,report=fr.stitch_face_refine_candidate(images,crops,plan,"ellipse",2.,1.,.65,.4,1,"cpu_memory_safe")
        self.assertTrue(torch.equal(repaired[mask==0],images[mask==0]))
        self.assertTrue(json.loads(report)["mask_outside_bit_exact"])

    def test_disabled_is_exact_passthrough(self):
        images=torch.rand(5,32,32,3)
        result=adapter.PemaraH3FaceRefine().refine(images,None,None,"",24.,0,"disabled",enabled=False)
        self.assertIs(result[0],images)


if __name__=="__main__": unittest.main(verbosity=2)
