import copy
import unittest
from creative_os.motion_director import compile_motion
from creative_os.ir import CreativeError
from test_creative_os_ir import sample


class MotionCompilerTests(unittest.TestCase):
    def setUp(self):
        self.shots = [sample(), sample()]
        self.shots[1]["shot_id"] = "SH02"

    def test_explicit_engine_audio_and_constraints_survive_compilation(self):
        self.shots[0]["constraints"] = {"no_people": True}
        before = copy.deepcopy(self.shots)
        result = compile_motion(self.shots, seed=23)
        node = result["graph"]["20"]["inputs"]
        self.assertEqual((node["width"], node["height"], node["steps"]), (1088,608,10))
        self.assertFalse(result["timeline"]["output"]["creativeOsNativeAudio"])
        self.assertNotIn("audio", result["graph"]["21"]["inputs"])
        self.assertIn("no_people", result["timeline"]["segments"][0]["prompt"])
        self.assertEqual(self.shots, before)
        self.assertEqual(result['segment_frames'],[124,124])
        self.shots[0]['duration_seconds']=6
        self.assertEqual(compile_motion(self.shots,seed=23)['segment_frames'],[141,124])
        self.shots[1]["generation"]["preferred_engine"] = "ltx_2_5"
        with self.assertRaises(CreativeError): compile_motion(self.shots, seed=23)

    def test_selective_rerun_does_not_silently_regenerate_context(self):
        with self.assertRaises(CreativeError): compile_motion(self.shots, seed=23, selected=[1])
        result = compile_motion(self.shots, seed=23, selected=[1], motion_context=False)
        self.assertEqual(result["selected_shots"], ["SH02"])
        self.assertEqual(result["timeline"]["runSelection"], [1])
        self.assertEqual(result["timeline"]["output"]["exportMode"], "segments")
        for invalid in ([], [True], [-1], [2]):
            with self.assertRaises(CreativeError): compile_motion(self.shots, seed=23, selected=invalid)

    def test_single_shot_and_duplicate_identity_are_rejected(self):
        with self.assertRaises(CreativeError): compile_motion(self.shots[:1], seed=23)
        with self.assertRaises(CreativeError): compile_motion([self.shots[0]]*2, seed=23)


if __name__ == "__main__": unittest.main()
