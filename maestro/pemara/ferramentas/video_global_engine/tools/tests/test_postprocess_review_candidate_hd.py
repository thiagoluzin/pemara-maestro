from __future__ import annotations

import copy
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from fractions import Fraction
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "postprocess_review_candidate_hd.py"
PROFILE = (
    Path(__file__).resolve().parents[2]
    / "upscale_profiles"
    / "ultrasharp_balanced_75_25_v1.json"
)
FAST_PROFILE = (
    Path(__file__).resolve().parents[2]
    / "upscale_profiles"
    / "realesrgan_x2_balanced_75_25_v1.json"
)
SPEC = importlib.util.spec_from_file_location("postprocess_review_candidate_hd", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_probe(*, audio: bool = True) -> dict:
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "h264",
            "width": 768,
            "height": 432,
            "pix_fmt": "yuv420p",
            "r_frame_rate": "24/1",
            "avg_frame_rate": "24/1",
            "nb_frames": "97",
            "nb_read_frames": "97",
        }
    ]
    if audio:
        streams.append(
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
                "channel_layout": "stereo",
            }
        )
    return {
        "streams": streams,
        "format": {
            "duration": "4.041667",
            "size": "12345",
            "bit_rate": "1000000",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        },
    }


class ProfileTests(unittest.TestCase):
    def test_canonical_profile_has_required_quality_contract(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        self.assertEqual(
            profile["pipeline_version"],
            "maestro_ultrasharp_review_candidate_v2",
        )
        self.assertEqual(profile["upscale"]["model"], "4x-UltraSharp.pth")
        self.assertEqual(profile["upscale"]["neural_blend"], 0.75)
        self.assertEqual(profile["upscale"]["source_lanczos_blend"], 0.25)
        self.assertEqual(profile["upscale"]["downscale_method"], "lanczos")
        self.assertEqual(profile["upscale"]["precision"], "float16")
        self.assertEqual(profile["encode"]["crf"], 10)
        self.assertEqual(profile["audio"]["policy"], "stream_copy_all")
        self.assertEqual(
            profile["cadence"]["policy"],
            "preserve_native_fps_and_frame_count",
        )

    def test_fast_profile_uses_official_realesrgan_x2_contract(self) -> None:
        profile = MODULE.load_profile(FAST_PROFILE)
        self.assertEqual(profile["profile_id"], "realesrgan_x2_balanced_75_25_v1")
        self.assertEqual(profile["upscale"]["model"], "RealESRGAN_x2plus.pth")
        self.assertEqual(profile["upscale"]["model_scale"], 2)
        self.assertEqual(
            profile["upscale"]["model_sha256"],
            "49FAFD45F8FD7AA8D31AB2A22D14D91B536C34494A5CFE31EB5D89C2FA266ABB",
        )
        self.assertEqual(profile["comfy"]["chunk_size"], 24)
        self.assertEqual(profile["comfy"]["per_batch"], 4)

    def test_unsafe_batch_overrides_are_rejected(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        args = MODULE.parse_args(
            [
                "source.mp4",
                "output",
                "--chunk-size",
                "25",
                "--per-batch",
                "2",
            ]
        )
        with self.assertRaisesRegex(RuntimeError, "chunk-size"):
            MODULE.effective_settings(args, profile)

    def test_profile_rejects_noncanonical_weak_encode(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        changed = copy.deepcopy(profile)
        changed["encode"]["crf"] = 28
        with self.assertRaisesRegex(RuntimeError, "CRF10"):
            MODULE.validate_profile(changed)


class GeometryAndFingerprintTests(unittest.TestCase):
    def test_low_frame_rate_source_is_rejected(self) -> None:
        probe = source_probe()
        probe["streams"][0]["r_frame_rate"] = "16/1"
        probe["streams"][0]["avg_frame_rate"] = "16/1"
        with self.assertRaisesRegex(RuntimeError, "too low"):
            MODULE.validate_source_probe(probe)

    def test_neural_ratio_exact_for_common_768x432_source(self) -> None:
        ratio, dimensions = MODULE.neural_ratio(768, 432, 1920, 1080, 4)
        self.assertEqual(ratio, 0.625)
        self.assertEqual(dimensions, (1920, 1080))

    def test_neural_ratio_covers_wider_832x480_without_stretch(self) -> None:
        ratio, dimensions = MODULE.neural_ratio(832, 480, 1920, 1080, 4)
        self.assertGreaterEqual(dimensions[0], 1920)
        self.assertGreaterEqual(dimensions[1], 1080)
        crop = MODULE.center_crop(*dimensions, 1920, 1080)
        self.assertEqual(Fraction(crop[0], crop[1]), Fraction(16, 9))
        self.assertLessEqual(ratio, 1.0)

    def test_too_small_source_is_rejected_instead_of_faking_fhd(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "too small"):
            MODULE.neural_ratio(320, 180, 1920, 1080, 4)

    def test_processing_fingerprint_covers_every_quality_input(self) -> None:
        baseline = {
            "pipeline_version": MODULE.PIPELINE_VERSION,
            "source": {"sha256": "A" * 64, "probe": source_probe()},
            "profile": MODULE.load_profile(PROFILE),
            "model": {"sha256": "B" * 64},
            "effective_processing": {
                "downscale_method": "lanczos",
                "precision": "float16",
            },
        }
        original = MODULE.json_fingerprint(baseline)
        mutations = [
            ("source", "sha256", "C" * 64),
            ("model", "sha256", "D" * 64),
            ("effective_processing", "downscale_method", "bicubic"),
            ("effective_processing", "precision", "float32"),
        ]
        for section, key, value in mutations:
            changed = copy.deepcopy(baseline)
            changed[section][key] = value
            self.assertNotEqual(
                original,
                MODULE.json_fingerprint(changed),
                msg=f"{section}.{key} was omitted from the fingerprint",
            )
        changed = copy.deepcopy(baseline)
        changed["profile"]["upscale"]["neural_blend"] = 0.5
        self.assertNotEqual(original, MODULE.json_fingerprint(changed))

    def test_blend_filter_is_explicit_75_25_and_center_crops(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        value = MODULE.blend_filter(
            (832, 480),
            (1920, 1107),
            (1920, 1080),
            profile,
        )
        self.assertIn("A*0.25000000+B*0.75000000", value)
        self.assertIn("crop=", value)
        self.assertIn("flags=lanczos", value)
        self.assertIn("range=limited", value)


class SidecarReuseTests(unittest.TestCase):
    def valid_sidecar(self) -> dict:
        return {
            "schema_version": "2.0",
            "processing_fingerprint": "F" * 64,
            "validation_status": "technical_pass_visual_qc_pending",
            "qc_status": "technical_pass_visual_qc_pending",
            "technical_validation": {"status": "technical_pass"},
            "human_review_status": "pending",
            "human_approval": {
                "status": "pending",
                "claimed_by_postprocessor": False,
            },
        }

    def test_exact_technical_pass_can_resume_without_claiming_approval(self) -> None:
        value = self.valid_sidecar()
        self.assertTrue(
            MODULE.sidecar_technically_reusable(value, "F" * 64)
        )
        self.assertEqual(value["human_review_status"], "pending")
        self.assertFalse(value["human_approval"]["claimed_by_postprocessor"])

    def test_fingerprint_mismatch_is_not_reused(self) -> None:
        self.assertFalse(
            MODULE.sidecar_technically_reusable(
                self.valid_sidecar(),
                "0" * 64,
            )
        )

    def test_rejected_candidate_is_never_reused(self) -> None:
        for rejected in (
            {"human_review_status": "rejected"},
            {"human_approval": {"status": "REJECTED"}},
            {"rejection": {"reason": "visual"}},
            {"rejected_at": "2026-07-23T00:00:00-03:00"},
        ):
            value = self.valid_sidecar()
            value.update(rejected)
            self.assertFalse(
                MODULE.sidecar_technically_reusable(value, "F" * 64)
            )

    def test_pending_without_technical_pass_is_not_reused(self) -> None:
        value = self.valid_sidecar()
        value["technical_validation"]["status"] = "pending"
        self.assertFalse(
            MODULE.sidecar_technically_reusable(value, "F" * 64)
        )


class ResumeAndHttpTests(unittest.TestCase):
    def test_chunk_checkpoint_requires_signature_and_valid_frames(self) -> None:
        signature = {"processing_fingerprint": "A" * 64, "count": 2}
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "chunk.json"
            MODULE.write_json_atomic(marker, signature)
            self.assertTrue(MODULE.marker_matches(marker, signature))
            self.assertFalse(
                MODULE.marker_matches(
                    marker,
                    {"processing_fingerprint": "B" * 64, "count": 2},
                )
            )

    def test_get_retries_transient_network_failures(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true}'
        with (
            mock.patch.object(
                MODULE.urllib.request,
                "urlopen",
                side_effect=[
                    urllib.error.URLError("temporary"),
                    response,
                ],
            ) as urlopen,
            mock.patch.object(MODULE.time, "sleep") as sleep,
        ):
            value = MODULE.http_json("http://comfy/test", profile)
        self.assertEqual(value, {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()

    def test_prompt_post_is_not_retried_to_avoid_duplicate_gpu_work(self) -> None:
        profile = MODULE.load_profile(PROFILE)
        with (
            mock.patch.object(
                MODULE.urllib.request,
                "urlopen",
                side_effect=urllib.error.URLError("lost response"),
            ) as urlopen,
            self.assertRaisesRegex(RuntimeError, "Cannot reach ComfyUI"),
        ):
            MODULE.http_json(
                "http://comfy/prompt",
                profile,
                method="POST",
                payload={"prompt": {}},
                retry=False,
            )
        self.assertEqual(urlopen.call_count, 1)


class DryRunTests(unittest.TestCase):
    def test_dry_run_is_read_only_and_emits_parseable_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            source.write_bytes(b"synthetic source placeholder")
            output = root / "not-created-output"
            work = root / "not-created-work"
            model = {
                "name": "4x-UltraSharp.pth",
                "path": "E:/fake/4x-UltraSharp.pth",
                "sha256": "A" * 64,
                "size": 66961958,
            }
            captured = io.StringIO()
            with (
                mock.patch.object(
                    MODULE,
                    "resolve_program",
                    side_effect=lambda name: name,
                ),
                mock.patch.object(
                    MODULE,
                    "resolve_model",
                    return_value=(Path(model["path"]), model),
                ),
                mock.patch.object(
                    MODULE,
                    "probe_media",
                    return_value=source_probe(audio=False),
                ),
                mock.patch.object(
                    MODULE,
                    "check_disk_space",
                    return_value={"c:": {"free_bytes": 999999999999}},
                ) as disk_check,
                mock.patch.object(MODULE, "preflight_comfy") as comfy_check,
                mock.patch.object(
                    MODULE,
                    "find_reusable_candidate",
                    return_value=None,
                ),
                redirect_stdout(captured),
            ):
                result = MODULE.main(
                    [
                        str(source),
                        str(output),
                        "--work-dir",
                        str(work),
                        "--profile",
                        str(PROFILE),
                        "--dry-run",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertRegex(
                captured.getvalue(),
                r"\[plan\] PROCESSING_FINGERPRINT=[0-9A-F]{64}",
            )
            self.assertIn("[plan] REQUIRED_WORK_BYTES=", captured.getvalue())
            self.assertIn("gpu_prompt_submitted", captured.getvalue())
            self.assertFalse(output.exists())
            self.assertFalse(work.exists())
            disk_check.assert_called_once()
            comfy_check.assert_called_once()


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "FFmpeg integration tools are unavailable",
)
class CodecIntegrationTests(unittest.TestCase):
    def test_stream_copy_accepts_exact_audio_packet_prefix_at_video_boundary(self) -> None:
        ffmpeg = str(shutil.which("ffmpeg"))
        ffprobe = str(shutil.which("ffprobe"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source_with_aac_tail.mp4"
            candidate = root / "candidate_trimmed_at_video_boundary.mp4"
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=320x180:rate=24:duration=0.084",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=880:sample_rate=48000:duration=0.125",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(source),
                ],
                check=True,
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-frames:v",
                    "2",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-c:a",
                    "copy",
                    str(candidate),
                ],
                check=True,
            )
            source_probe_data = MODULE.probe_media(ffprobe, source)
            candidate_probe_data = MODULE.probe_media(ffprobe, candidate)
            source_audio = MODULE.audio_streams(source_probe_data)
            candidate_audio = MODULE.audio_streams(candidate_probe_data)
            source_packets = MODULE.audio_packet_hashes(ffprobe, source, 0)
            candidate_packets = MODULE.audio_packet_hashes(ffprobe, candidate, 0)

            self.assertLess(len(candidate_packets), len(source_packets))
            self.assertEqual(source_packets[: len(candidate_packets)], candidate_packets)
            fingerprint = MODULE.validate_stream_copied_audio(
                ffprobe,
                source,
                candidate,
                source_audio,
                candidate_audio,
                target_duration=2 / 24,
            )
            self.assertRegex(str(fingerprint), r"^[0-9A-F]{64}$")

    def test_encode_preserves_frames_fps_audio_and_bt709_contract(self) -> None:
        ffmpeg = str(shutil.which("ffmpeg"))
        ffprobe = str(shutil.which("ffprobe"))
        profile = MODULE.load_profile(PROFILE)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            processed = root / "processed"
            processed.mkdir()
            candidate = root / "candidate.mp4"
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=768x432:rate=24:duration=0.084",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=880:sample_rate=48000:duration=0.084",
                    "-frames:v",
                    "2",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                check=True,
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-vf",
                    "scale=1920:1080:flags=lanczos",
                    "-frames:v",
                    "2",
                    str(processed / "frame_%06d.png"),
                ],
                check=True,
            )
            source_data = MODULE.probe_media(ffprobe, source)
            MODULE.encode_candidate(
                ffmpeg,
                source,
                processed,
                candidate,
                fps=Fraction(24, 1),
                frames=2,
                source_dimensions=(768, 432),
                neural_dimensions=(1920, 1080),
                target_dimensions=(1920, 1080),
                profile=profile,
                log_handle=io.StringIO(),
            )
            candidate_data, audio_hash = MODULE.validate_candidate(
                ffprobe,
                ffmpeg,
                source,
                candidate,
                source_data,
                fps=Fraction(24, 1),
                frames=2,
                target_dimensions=(1920, 1080),
                full_decode=True,
                log_handle=io.StringIO(),
            )
            video = MODULE.video_stream(candidate_data)
            self.assertEqual(video["codec_name"], "h264")
            self.assertEqual(MODULE.counted_frames(video), 2)
            self.assertEqual(video["color_range"], "tv")
            self.assertEqual(video["color_space"], "bt709")
            self.assertRegex(str(audio_hash), r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
