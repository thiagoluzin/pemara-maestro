import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dlss5_finishing as d


class RequiredFinishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'candidate.mp4'
        self.path.write_bytes(b'original-picture-and-audio')

    def tearDown(self):
        self.temp.cleanup()

    def test_failure_preserves_original_and_never_creates_valid_receipt(self):
        with patch.object(d, 'preflight'), patch.object(d, '_video', side_effect=d.DLSS5RequiredError('GPU failed')):
            with self.assertRaises(d.DLSS5RequiredError):
                d.finish_file(self.path, content_kind='animation')
        self.assertEqual(self.path.read_bytes(), b'original-picture-and-audio')
        self.assertEqual(len(list(self.path.parent.glob('*.before_dlss5.*'))), 1)
        self.assertIsNone(d.valid_receipt(self.path))

    def test_success_is_atomic_and_does_not_apply_twice(self):
        def render(source, dest, log):
            dest.write_bytes(b'finished-picture-and-audio')
            return {'frames':900}
        with patch.object(d, 'preflight'), patch.object(d, '_video', side_effect=render) as renderer:
            receipt = d.finish_file(self.path, content_kind='animation')
            repeated = d.finish_file(self.path, content_kind='animation')
        self.assertEqual(renderer.call_count, 1)
        self.assertEqual(receipt, repeated)
        self.assertEqual(Path(receipt['source']).read_bytes(), b'original-picture-and-audio')
        self.path.write_bytes(b'tampered')
        self.assertIsNone(d.valid_receipt(self.path))

    def test_source_changed_during_processing_blocks_commit(self):
        def render(source, dest, log):
            dest.write_bytes(b'finished')
            self.path.write_bytes(b'concurrent-change')
            return {}
        with patch.object(d, 'preflight'), patch.object(d, '_video', side_effect=render):
            with self.assertRaises(d.DLSS5RequiredError):
                d.finish_file(self.path, content_kind='animation')
        self.assertEqual(self.path.read_bytes(), b'concurrent-change')
        self.assertIsNone(d.valid_receipt(self.path))

    def test_unsupported_output_blocks_delivery(self):
        path = self.path.with_suffix('.gif')
        path.write_bytes(b'gif')
        with patch.object(d, 'preflight'), self.assertRaises(d.DLSS5RequiredError):
            d.finish_file(path, content_kind='animation')
        self.assertIsNone(d.valid_receipt(path))

    def test_component_tamper_blocks_before_render(self):
        with patch.dict(d.PINNED, {self.path:'0'*64}, clear=True):
            with self.assertRaisesRegex(d.DLSS5RequiredError, 'hash divergente'):
                d.preflight()

    def test_assembly_cannot_inherit_an_untreated_take(self):
        with self.assertRaises(d.DLSS5RequiredError):
            d.inherit_assembly([self.path], self.path)

    def test_disabled_policy_fails_closed(self):
        with patch.object(d, 'REQUIRED', False), self.assertRaises(d.DLSS5RequiredError):
            d.preflight()

    def test_real_runtime_pinned_components(self):
        self.assertTrue(d.preflight()['required'])


if __name__ == '__main__':
    unittest.main()
