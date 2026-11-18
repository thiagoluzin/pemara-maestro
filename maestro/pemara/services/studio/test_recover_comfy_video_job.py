import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import recover_comfy_video_job as recovery
from generative_jobs import GenerativeJobStore


class RecoverComfyVideoJobTest(unittest.TestCase):
    def test_recovers_terminal_h3_job_from_verified_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store_path = root / "jobs.json"
            output_root = root / "output"
            video = output_root / "maestro_generative" / "video" / "minimax_h3_fl2va_00112_.mp4"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"verified-video-placeholder")
            store = GenerativeJobStore(store_path, recover_on_init=False)
            receipts = recovery.artifact_receipts("job-h3", {
                "model": recovery.H3_MODEL, "prompt_id": "prompt-h3",
                "outputs": [{"kind": "video", "type": "output", "filename": video.name,
                             "subfolder": "maestro_generative/video"}],
            }, output_root)
            store.update(
                "job-h3",
                status="canceled",
                model=recovery.H3_MODEL,
                prompt_id="prompt-h3",
                frames=362,
                artifact_receipts=receipts,
                request_spec={"video_conditioning_profile": "identity_locked"},
            )

            with (
                patch.object(recovery, "JOB_STORE_PATH", store_path),
                patch.object(recovery, "COMFY_OUTPUT_ROOT", output_root),
                patch.object(
                    recovery,
                    "inspect_video",
                    return_value={
                        "duration": 12.03,
                        "fps": 30.0,
                        "width": 1280,
                        "height": 720,
                        "codec": "h264",
                    },
                ),
            ):
                other = video.with_name("minimax_h3_fl2va_other.mp4")
                other.write_bytes(video.read_bytes())
                with self.assertRaisesRegex(RuntimeError, "recibo"):
                    recovery.recover("job-h3", other)
                recovered = recovery.recover("job-h3", video)
                with self.assertRaises(RuntimeError):
                    recovery.recover("job-h3", video)

            self.assertEqual(recovered["status"], "done")
            self.assertEqual(recovered["progress"], 100)
            self.assertTrue(recovered["result"]["recovered_after_comfy_http_failure"])
            output = recovered["result"]["outputs"][0]
            self.assertEqual(output["filename"], video.name)
            self.assertEqual(output["subfolder"], "maestro_generative\\video")


if __name__ == "__main__":
    unittest.main()
