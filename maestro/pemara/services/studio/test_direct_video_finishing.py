"""Admission follows the owner's anchors-only DLSS policy (2026-10-22)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import main

class DirectVideoFinishingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / 'video.mp4'
        self.path.write_bytes(b'original')
        self.root_patch = patch.object(main, 'COMFY_OUTPUT_DIR', str(self.root))
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    @staticmethod
    def history(filename='video.mp4', subfolder='', folder_type='output'):
        return {'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'16': {'images': [{'filename': filename,
                    'subfolder': subfolder, 'type': folder_type}]}}}

    def test_video_formats_admitted_without_receipts_or_dlss(self):
        for suffix in ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.gif', '.apng'):
            with self.subTest(suffix=suffix):
                path = self.root / ('video' + suffix)
                path.write_bytes(b'original')
                with patch.object(main._dlss5, 'valid_receipt', side_effect=AssertionError('No video receipt')), patch.object(main._dlss5, 'finish_file', side_effect=AssertionError('No video DLSS')):
                    outputs = main._extract_comfy_outputs(self.history(path.name))
                self.assertEqual(outputs[0]['kind'], 'video')
                self.assertIn('url', outputs[0])
                self.assertEqual(path.read_bytes(), b'original')

    def test_missing_and_unsafe_video_outputs_rejected(self):
        for filename, subfolder, folder_type in (
            ('missing.mp4', '', 'output'), ('../video.mp4', '', 'output'),
            ('video.mp4', '..', 'output'), ('video.mp4', str(self.root), 'output'),
            ('video.mp4', '', 'temp'),
        ):
            with self.subTest(filename=filename, subfolder=subfolder, folder_type=folder_type):
                with self.assertRaisesRegex(ValueError, 'Saida visual ausente'):
                    main._extract_comfy_outputs(self.history(filename, subfolder, folder_type))

    def test_input_reference_is_not_exposed_as_output(self):
        self.assertEqual(main._extract_comfy_outputs(self.history(folder_type='input')), [])

    def test_anchor_without_receipt_still_rejected(self):
        (self.root / 'image.png').write_bytes(b'anchor')
        with patch.object(main._dlss5, 'valid_receipt', return_value=None):
            with self.assertRaisesRegex(main._dlss5.DLSS5RequiredError, 'sem recibo'):
                main._extract_comfy_outputs(self.history('image.png'))

    def test_anchor_with_valid_receipt_admitted(self):
        (self.root / 'image.png').write_bytes(b'anchor')
        with patch.object(main._dlss5, 'valid_receipt', return_value={'technical_pass': True}) as receipt:
            outputs = main._extract_comfy_outputs(self.history('image.png'))
        receipt.assert_called_once_with(str((self.root / 'image.png').resolve()))
        self.assertEqual(outputs[0]['kind'], 'image')

    def test_completed_prompt_is_recovered_without_resampling_or_finishing(self):
        def service(path, *args, **kwargs):
            if path == '/history/existing':
                return {'existing': self.history()}
            if path == '/queue':
                return {'queue_running': [], 'queue_pending': []}
            raise AssertionError('Must not submit a new render: ' + path)
        with patch.object(main, '_comfy_request', side_effect=service), patch.object(main._dlss5, 'finish_file', side_effect=AssertionError('No video DLSS')):
            prompt_id, outputs = main._queue_comfy_workflow({}, timeout=1, resume_prompt_id='existing')
        self.assertEqual(prompt_id, 'existing')
        self.assertEqual(outputs[0]['filename'], 'video.mp4')

    def test_video_finishing_is_noop_without_gpu_or_receipt(self):
        for suffix in ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.gif', '.apng'):
            with self.subTest(suffix=suffix), patch.object(main, '_GPU_LEASE_REGISTRY') as registry, patch.object(main._dlss5, 'valid_receipt', side_effect=AssertionError('No video receipt')), patch.object(main._dlss5, 'finish_file', side_effect=AssertionError('No video DLSS')):
                result = main._finish_required_media(self.root / ('video' + suffix))
                self.assertFalse(result['applied'])
                self.assertEqual(result['scope'], 'anchors_only')
                registry.acquire.assert_not_called()

if __name__ == '__main__':
    unittest.main()
