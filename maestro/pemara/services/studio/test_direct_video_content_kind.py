"""Direct requests carry explicit type before GPU admission; finishing stays mandatory."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
import main
import dlss5_finishing as finishing


class DirectVideoContentKindTests(unittest.TestCase):
    def test_form_type_reaches_job_spec(self):
        for kind in ('animation', 'live_action', 'mixed'):
            with self.subTest(kind=kind), patch.object(main, '_is_internal_request', return_value=True), patch.object(main, '_start_generative_job', return_value='fixture') as start:
                response = TestClient(main.app).post('/api/generative/job', data={'prompt': 'Teste', 'mode': 'video', 'engine_id': 'minimax_h3', 'content_kind': kind})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(start.call_args.args[0]['content_kind'], kind)

    def test_normalization_preserves_type_without_inference(self):
        spec = {'mode': 'video', 'engine_id': 'minimax_h3', 'prompt': 'Teste', 'h3_quality_profile': 'h3_production', 'content_kind': 'mixed', 'steps': 10, 'fps': 24, 'frames': 243, 'video_duration': 10}
        with patch.object(main, '_resolve_video_engine', return_value=(SimpleNamespace(id='minimax_h3'), main.MINIMAX_H3_MODEL_NAME)):
            self.assertEqual(main._normalize_generative_job_spec(spec)['content_kind'], 'mixed')
            spec['content_kind'] = 'bad-type'
            with self.assertRaises(ValueError):
                main._normalize_generative_job_spec(spec)

    def test_missing_type_stops_before_engine_and_gpu(self):
        with patch.object(main, '_normalize_generative_job_spec', return_value={'mode': 'video', 'content_kind': 'unknown'}), patch.object(main, '_video_engine_registry_live') as registry, patch.object(main, '_persist_job_input') as persist:
            with self.assertRaisesRegex(ValueError, 'tipo do vídeo'):
                main._start_generative_job({})
            registry.assert_not_called()
            persist.assert_not_called()

    def test_finishing_uses_request_scoped_type(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            source.write_bytes(b'fixture-video')
            @finishing.content_policy.with_content_kind
            def run():
                return main._finish_required_media(source, lease_job_id='fixture')
            with patch.object(finishing, 'staging_receipt', return_value=None), patch.object(finishing, 'valid_receipt', return_value=None), patch.object(main, '_GPU_LEASE_REGISTRY'), patch.object(main, '_comfy_request', return_value={}), patch.object(finishing, 'finish_file', return_value={'technical_pass': True}) as finish:
                run(content_kind='animation')
                self.assertEqual(finish.call_args.kwargs['content_kind'], 'animation')
                self.assertEqual(finishing.content_policy.current_kind(), 'unknown')

    def test_video_executes_full_frame_finishing_and_preserves_native(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            source.write_bytes(b'original-video')
            def video(native, dest, log):
                self.assertEqual(native.read_bytes(), b'original-video')
                dest.write_bytes(b'treated-video')
                return {'frame_count_preserved': True}
            with patch.object(finishing, 'valid_receipt', return_value=None), patch.object(finishing, 'preflight', return_value={}), patch.object(finishing, '_video', side_effect=video) as execute:
                receipt = finishing.finish_file(source, content_kind='live_action')
            execute.assert_called_once()
            self.assertTrue(receipt['technical_pass'])
            self.assertEqual(receipt['coverage_percent'], 100)
            self.assertFalse(receipt['automatic_masks'])
            self.assertEqual(Path(receipt['source']).read_bytes(), b'original-video')
            self.assertEqual(source.read_bytes(), b'treated-video')
            self.assertEqual(receipt['owner_approval'], 'PENDING')

    def test_runtime_failure_never_releases_untreated_video(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            source.write_bytes(b'original-video')
            with patch.object(finishing, 'valid_receipt', return_value=None), patch.object(finishing, 'preflight', side_effect=finishing.DLSS5RequiredError('runtime ausente')), patch.object(finishing, '_video') as execute:
                with self.assertRaises(finishing.DLSS5RequiredError):
                    finishing.finish_file(source, content_kind='animation')
                execute.assert_not_called()
                self.assertEqual(source.read_bytes(), b'original-video')
                self.assertFalse(finishing.receipt_path(source).exists())


if __name__ == '__main__':
    unittest.main()
