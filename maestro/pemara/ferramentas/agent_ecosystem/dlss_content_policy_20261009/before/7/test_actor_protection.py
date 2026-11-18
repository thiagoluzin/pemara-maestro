import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import actor_protection as a
import dlss5_finishing as d


class ActorProtectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'anchor.png'
        self.mask = self.root / 'mask.png'
        self.pixels = np.zeros((8, 8, 4), np.uint8)
        self.pixels[:] = [30, 80, 140, 170]
        Image.fromarray(self.pixels).save(self.source)
        matte = np.zeros((8, 8), np.uint8); matte[:, :3] = 255; matte[:, 3] = 128
        Image.fromarray(matte).save(self.mask)
        self.data = {'schema_version': '1.0', 'mode': a.MODE,
            'source_sha256': a.sha(self.source), 'protected_subjects': ['Jill'],
            'mask_review': {'status': 'PASS', 'reviewer': 'fixture reviewer', 'note': 'synthetic interior and edge'},
            'masks': [{'path': str(self.mask), 'sha256': a.sha(self.mask)}]}
        self.manifest = a.sidecar(self.source)
        self.write()

    def write(self):
        self.manifest.write_text(json.dumps(self.data), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_linear_composite_preserves_actor_background_and_alpha(self):
        original = np.array([[[0, 0, 0, 42], [0, 0, 0, 43], [0, 0, 0, 44]]], np.uint8)
        treated = np.full_like(original, 255)
        result = a.composite_rgba(original, treated, np.array([[255, 128, 0]], np.uint8))
        np.testing.assert_array_equal(result[0, 0], original[0, 0])
        self.assertGreater(int(result[0, 1, 0]), 180)  # Linear-light mix, not dark byte-space 127.
        self.assertEqual(int(result[0, 2, 0]), 255)
        np.testing.assert_array_equal(result[..., 3], original[..., 3])

    def test_stale_source_is_rejected_before_gpu(self):
        self.source.write_bytes(b'changed')
        with patch.object(d, 'preflight') as gpu, self.assertRaises(d.DLSS5RequiredError):
            d.finish_file(self.source, protect_actors=True)
        gpu.assert_not_called()

    def test_wrong_geometry_and_empty_masks_are_rejected(self):
        for size, value in [((4, 4), 255), ((8, 8), 0), ((8, 8), 255), ((8, 8), 128)]:
            Image.new('L', size, value).save(self.mask)
            self.data['masks'][0]['sha256'] = a.sha(self.mask); self.write()
            with self.assertRaises(ValueError):
                a.read_contract(self.manifest, self.source, (8, 8), 1)

    def test_frame_coverage_cannot_broadcast_a_single_mask(self):
        with self.assertRaisesRegex(ValueError, 'uma mascara por quadro'):
            a.read_contract(self.manifest, self.source, (8, 8), 2)

    def test_pending_visual_review_cannot_pass_by_metadata(self):
        self.data['mask_review']['status'] = 'PENDING'; self.write()
        with self.assertRaises(ValueError):
            a.read_contract(self.manifest, self.source, (8, 8), 1)

    def test_mask_mutation_is_detected(self):
        contract = a.read_contract(self.manifest, self.source, (8, 8), 1)
        Image.new('L', (8, 8), 0).save(self.mask)
        with self.assertRaisesRegex(ValueError, 'Mascara mudou'):
            a.verify_contract(contract)

    def test_missing_requested_mask_never_uses_full_frame_fallback(self):
        self.manifest.unlink()
        with patch.object(d, 'preflight') as gpu, patch.object(d, '_image') as renderer:
            with self.assertRaisesRegex(d.DLSS5RequiredError, 'sem fallback integral'):
                d.finish_file(self.source, protect_actors=True)
        gpu.assert_not_called(); renderer.assert_not_called()

    def test_selective_finish_receipt_and_idempotence(self):
        def render(source, dest, log):
            Image.new('RGBA', (8, 8), (220, 190, 170, 255)).save(dest)
            return {'width': 8, 'height': 8, 'frames': 1}
        with patch.object(d, 'preflight'), patch.object(d, '_image', side_effect=render) as renderer:
            receipt = d.finish_file(self.source)
            again = d.finish_file(self.source)
        self.assertEqual(receipt, again); self.assertEqual(renderer.call_count, 1)
        self.assertEqual(receipt['profile'], d.ACTOR_PROFILE)
        self.assertTrue(receipt['protected_pixels_exact'])
        self.assertIsNotNone(d.valid_receipt(self.source))
        with Image.open(self.source) as image:
            pixels = np.asarray(image)
        np.testing.assert_array_equal(pixels[:, :3], self.pixels[:, :3])
        self.assertEqual(pixels[0, 7, 0], 220)
        self.assertTrue(Path(receipt['neural_intermediate']['path']).is_file())

    def test_full_frame_receipt_cannot_masquerade_as_actor_protection(self):
        self.manifest.unlink()
        d._atomic_json(d.receipt_path(self.source), {'profile': d.PROFILE, 'technical_pass': True,
            'output_sha256': d.sha(self.source)})
        self.write()
        with self.assertRaisesRegex(d.DLSS5RequiredError, 'sem DLSS recursivo'):
            d.finish_file(self.source)

    def test_mixed_assembly_records_selective_provenance(self):
        first = self.root / 'first.mp4'; first.write_bytes(b'a')
        second = self.root / 'second.mp4'; second.write_bytes(b'b')
        result = self.root / 'master.mp4'; result.write_bytes(b'ab')
        for path, profile, mode in [(first, d.PROFILE, 'full_frame'), (second, d.ACTOR_PROFILE, a.MODE)]:
            d._atomic_json(d.receipt_path(path), {'profile': profile, 'technical_pass': True,
                'output_sha256': d.sha(path), 'processing_mode': mode,
                'actor_protection': {'mode': a.MODE, 'contract_sha256': 'fixture'}})
        receipt = d.inherit_assembly([first, second], result)
        self.assertEqual(receipt['profile'], d.ASSEMBLY_PROFILE)
        self.assertEqual(set(receipt['processing_modes']), {'full_frame', a.MODE})
        self.assertIsNotNone(d.valid_receipt(result))

    def test_real_cpu_video_composition_preserves_frames_actor_and_audio(self):
        ffmpeg = Path('C:/ProgramData/chocolatey/bin/ffmpeg.exe')
        if not ffmpeg.is_file():
            self.skipTest('CPU ffmpeg fixture runtime unavailable')
        source = self.root / 'source.mkv'; treated = self.root / 'treated.mkv'; output = self.root / 'composed.mkv'
        pixels = np.zeros((3, 16, 16, 4), np.uint8); pixels[..., 3] = 255
        for index in range(3): pixels[index, ..., :3] = [20 + index * 40, 70, 100]
        other = pixels.copy(); other[..., :3] = [220, 180, 40]
        common = [str(ffmpeg), '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
            '-s', '16x16', '-r', '24', '-i', '-']
        subprocess.run(common + ['-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
            '-frames:v', '3', '-t', '0.125', '-c:v', 'ffv1', '-c:a', 'pcm_s16le', str(source)],
            input=pixels.tobytes(), capture_output=True, check=True)
        subprocess.run(common + ['-frames:v', '3', '-c:v', 'ffv1', str(treated)],
            input=other.tobytes(), capture_output=True, check=True)
        mask = self.root / 'video_mask.png'
        matte = np.zeros((16,16), np.uint8); matte[:, :8] = 255
        Image.fromarray(matte).save(mask)
        data = dict(self.data, source_sha256=a.sha(source),
            masks=[{'path':str(mask), 'sha256':a.sha(mask)} for _ in range(3)])
        manifest = a.sidecar(source); manifest.write_text(json.dumps(data), encoding='utf-8')
        contract = a.read_contract(manifest, source, (16,16), 3)
        a.compose_video(source, treated, output, contract, ffmpeg, (16,16), '24', codec='ffv1')
        decoded = subprocess.run([str(ffmpeg), '-v', 'error', '-i', str(output), '-map', '0:v:0',
            '-pix_fmt', 'rgba', '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
        actual = np.frombuffer(decoded, np.uint8).reshape(3,16,16,4)
        np.testing.assert_array_equal(actual[:, :, :8], pixels[:, :, :8])
        np.testing.assert_array_equal(actual[:, :, 8:], other[:, :, 8:])
        self.assertEqual(d._audio_pcm_hash(source), d._audio_pcm_hash(output))
        video = next(s for s in d._probe(output)['streams'] if s['codec_type']=='video')
        self.assertEqual(int(video['nb_read_frames']), 3)


if __name__ == '__main__':
    unittest.main()
