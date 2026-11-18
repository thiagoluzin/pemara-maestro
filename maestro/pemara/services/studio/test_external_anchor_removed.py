import unittest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi.testclient import TestClient
import main


class ExternalAnchorRemovedTests(unittest.TestCase):
    def test_creative_os_photo_prepare_needs_no_analysis_receipt(self):
        spec={'mode':'video','engine_id':'minimax_h3','prompt':'owner movement','negative':''}
        with patch.object(main,'_normalize_generative_job_spec',side_effect=lambda value:value), patch.object(main,'_require_compiled_anchor_receipt',side_effect=AssertionError('No external receipt')):
            prepared=main._CREATIVE_OS.bridge.prepare(spec,{}, {'base_bytes':b'approved-photo'})
        self.assertEqual(prepared['prompt'],'owner movement')

    def test_old_analysis_endpoint_never_calls_nvidia(self):
        with patch.object(main, '_is_internal_request', return_value=True), patch.object(main, '_browser_origin_allowed', return_value=True), patch.object(main, '_nvidia_vision', side_effect=AssertionError('No image upload')) as vision, patch.object(main, '_env_value', side_effect=AssertionError('No credential lookup')):
            response=TestClient(main.app).post('/api/generative/anchor-intelligence/analyze', files={'anchor':('photo.png',b'pixels','image/png')}, data={'allow_external_processing':'true'})
        self.assertEqual(response.status_code,410)
        self.assertEqual(response.json()['code'],'EXTERNAL_ANCHOR_ANALYSIS_REMOVED')
        vision.assert_not_called()

    def test_chat_accepts_photo_without_external_receipt_even_for_old_clients(self):
        with patch.object(main,'_is_internal_request',return_value=True), patch.object(main,'_browser_origin_allowed',return_value=True), patch.object(main,'_require_compiled_anchor_receipt',side_effect=AssertionError('No receipt gate')), patch.object(main,'_run_generative',return_value={'ok':True}) as run:
            response=TestClient(main.app).post('/api/generative/chat',files={'base_image':('photo.png',b'pixels','image/png')},data={'prompt':'turn toward water','mode':'video','engine_id':'minimax_h3','anchor_contract_id':'expired','prompt_compiler_version':'obsolete'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(run.call_args.kwargs['base_image_bytes'],b'pixels')

    def test_local_compilation_does_not_require_nim_session(self):
        engine=SimpleNamespace(id='minimax_h3',compile_prompt=lambda contract,request:{'prompt':'local prompt','compiler_version':'local'})
        with patch.object(main,'_is_internal_request',return_value=True), patch.object(main,'_browser_origin_allowed',return_value=True), patch.object(main,'_video_engine_registry_live',return_value=SimpleNamespace(get=lambda _:engine)), patch.object(main,'_require_anchor_analysis_receipt',side_effect=AssertionError('No NIM session')), patch.object(main,'_register_compiled_anchor_receipt',side_effect=AssertionError('No external receipt')):
            response=TestClient(main.app).post('/api/generative/video-engines/minimax_h3/compile-prompt',json={'anchor_contract':{'local':True},'request':{}})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['compiled']['prompt'],'local prompt')
