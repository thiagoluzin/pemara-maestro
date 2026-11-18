from copy import deepcopy
import unittest
from unittest.mock import patch

from h3_acceleration import (PROFILE, SPECTRUM_PROFILE, SPECTRUM_NODE, SPECTRUM_SETTINGS,
                             validate_spectrum, model_chain)
from h3_workflow import ensure_h3_sage_attention, H3_QUALITY_PROFILES, FAST_H3_VARIANT


def source():
    return {
        'load': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'minimax_h3_fl2va_pruned_int8_convrot.safetensors'}},
        'guide': {'class_type': 'BasicGuider', 'inputs': {'model': ['load', 0]}},
        'schedule': {'class_type': 'BasicScheduler', 'inputs': {'model': ['load', 0], 'steps': 20}},
        'sampler': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': 'res_multistep'}},
    }


class RequiredAccelerationTests(unittest.TestCase):
    def test_patch_is_connected_ordered_enabled_and_idempotent(self):
        graph = ensure_h3_sage_attention(source())
        before = deepcopy(graph)
        self.assertTrue(validate_spectrum(graph))
        self.assertEqual(ensure_h3_sage_attention(graph), before)
        chain = model_chain(graph, graph['guide']['inputs']['model'][0])
        self.assertEqual([n['class_type'] for _, n in chain[:3]],
            [SPECTRUM_NODE, 'PemaraH3SageLongSequencePatch', 'MiniMaxH3MemoryEfficientSageAttentionPatch'])
        self.assertEqual(graph['guide']['inputs']['model'], graph['schedule']['inputs']['model'])
        self.assertEqual({k: v for k, v in chain[0][1]['inputs'].items() if k != 'model'}, SPECTRUM_SETTINGS)

    def test_disabled_disconnected_missing_and_modified_spectrum_are_rejected(self):
        for defect in ('disabled', 'missing', 'disconnected', 'audio'):
            with self.subTest(defect=defect):
                graph = ensure_h3_sage_attention(source())
                key = next(k for k, n in graph.items() if n['class_type'] == SPECTRUM_NODE)
                if defect == 'disabled': graph[key]['inputs']['enabled'] = False
                if defect == 'audio': graph[key]['inputs']['audio_blend_weight'] = 0.5
                if defect in ('missing', 'disconnected'):
                    for node in graph.values():
                        if node.get('inputs', {}).get('model') == [key, 0]:
                            node['inputs']['model'] = graph[key]['inputs']['model']
                    if defect == 'missing': del graph[key]
                with self.assertRaisesRegex(ValueError, 'H3_GRAPH_SPECTRUM'):
                    validate_spectrum(graph)

    def test_old_fbc_graph_is_migrated_without_stacking(self):
        graph = source()
        graph['fbc'] = {'class_type': 'ApplyMiniMaxH3FirstBlockCache', 'inputs': {'model': ['load', 0]}}
        graph['guide']['inputs']['model'] = ['fbc', 0]
        graph['schedule']['inputs']['model'] = ['fbc', 0]
        ensure_h3_sage_attention(graph)
        self.assertNotIn('fbc', graph)
        self.assertTrue(validate_spectrum(graph))

    def test_multiple_model_paths_preserve_other_patches(self):
        graph = source()
        graph['control'] = {'class_type': 'H3FunControlApply', 'inputs': {'model': ['load', 0], 'strength': 0.7}}
        graph['guide']['inputs']['model'] = ['control', 0]
        ensure_h3_sage_attention(graph)
        self.assertIn('control', [key for key, _ in model_chain(graph, graph['guide']['inputs']['model'][0])])
        self.assertEqual(graph['control']['inputs']['strength'], 0.7)
        self.assertTrue(validate_spectrum(graph))

    def test_other_engines_are_unchanged_and_unsupported_sampler_fails(self):
        graph = source(); graph['load']['inputs']['unet_name'] = 'ltx2.safetensors'
        before = deepcopy(graph)
        self.assertEqual(ensure_h3_sage_attention(graph), before)
        graph = source(); graph['sampler']['inputs']['sampler_name'] = 'sa_solver'
        with self.assertRaisesRegex(ValueError, 'SAMPLER_UNSUPPORTED'):
            ensure_h3_sage_attention(graph)

    def test_all_profiles_orientations_modes_and_audio_choices(self):
        import main
        for profile_id, profile in H3_QUALITY_PROFILES.items():
            for vertical in (False, True):
                for mode in ('T2VA', 'I2VA', 'FL2VA', 'L2VA', 'REF2VA'):
                    for audio in (False, True):
                        with self.subTest(profile=profile_id, vertical=vertical, mode=mode, audio=audio):
                            args = dict(prompt='test', negative='',
                                width=profile['verticalWidth'] if vertical else profile['width'],
                                height=profile['verticalHeight'] if vertical else profile['height'],
                                frames=243, steps=profile['steps'][0], seed=42, prefix='tests/required',
                                include_native_audio=audio, h3_quality_profile=profile_id)
                            if mode == 'REF2VA':
                                graph = main._build_minimax_h3_ref2va_workflow(**args, reference_image_names=['re2_v2_K1.png'])
                            else:
                                graph = main._build_minimax_h3_fl2va_workflow(**args,
                                    base_image_name='re2_v2_K1.png' if mode in ('I2VA', 'FL2VA') else '',
                                    end_image_name='re2_v2_K1.png' if mode in ('L2VA', 'FL2VA') else '')
                            self.assertTrue(validate_spectrum(graph))
                            self.assertEqual(graph['8']['inputs']['steps'], args['steps'])
                            self.assertEqual(graph['6']['inputs']['length'], 243)
                            if mode == 'REF2VA':
                                self.assertEqual(graph[graph['6']['inputs']['audio_vae'][0]]['class_type'], 'VAELoader')
                            self.assertEqual('audio' in graph['15']['inputs'], audio and not profile.get('draftOnly', False))
                            self.assertNotIn('last_frame_index', graph['6']['inputs'])
                            self.assertFalse(any(n['class_type'] == 'PemaraH3FaceRefine' for n in graph.values()))

    def test_fast_preview_and_intermediate_guide(self):
        import main
        for variant, guided in ((FAST_H3_VARIANT, False), ('base', True)):
            graph = main._build_minimax_h3_fl2va_workflow(prompt='test', negative='', width=1088,
                height=608, frames=243, steps=8 if variant == FAST_H3_VARIANT else 10, seed=42,
                prefix='tests/required', base_image_name='re2_v2_K1.png', end_image_name='',
                h3_quality_profile='h3_production', h3_model_variant=variant, enable_live_preview=True,
                guide_image_name='re2_v2_K1.png' if guided else '', guide_frame_index=120 if guided else None)
            self.assertTrue(validate_spectrum(graph))
            self.assertTrue(any(n['class_type'] == 'ModelPreviewOverrideKJ' for n in graph.values()))

    def test_embedded_sampler_paths_cannot_bypass_requirement(self):
        for kind in ('MiniMaxH3MotionDirector', 'MiniMaxH3FiniteSegmentSampler', 'KSampler', 'KSamplerAdvanced'):
            graph = source()
            graph['embedded'] = {'class_type': kind, 'inputs': {'model': ['load', 0], 'sampler_name': 'res_multistep'}}
            ensure_h3_sage_attention(graph)
            self.assertTrue(validate_spectrum(graph))
            self.assertEqual(graph['embedded']['inputs']['model'], graph['guide']['inputs']['model'])

    def test_submission_blocks_missing_runtime_components_before_prompt(self):
        import main
        graph = source()
        with patch.object(main, '_comfy_request', return_value={}) as request:
            with self.assertRaisesRegex(RuntimeError, 'H3_ACCELERATION_REQUIRED'):
                main._queue_comfy_workflow(graph, timeout=1)
        self.assertFalse(any(call.args[0] == '/prompt' for call in request.call_args_list))

    def test_readiness_requires_every_acceleration_node(self):
        import main
        def object_info(path, **kwargs):
            name = path.rsplit('/', 1)[-1]
            return {name: {}}
        with patch.object(main, '_comfy_request', side_effect=object_info):
            status = main._h3_workflow_status_live(comfy_online=True)
        for key in ('sageAttentionReady', 'sageProtectionReady', 'spectrumReady', 'spectrumRequired'):
            self.assertTrue(status['capabilities'][key])
        with patch.object(main, '_comfy_request', return_value={}):
            self.assertFalse(main._h3_workflow_status_live(comfy_online=True)['productionReady'])


if __name__ == '__main__': unittest.main()
