import copy
from pathlib import Path
import tempfile
import unittest
import sequence_camera_contract as c


class CameraSequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        artifact = self.root / 'evidence'; artifact.write_bytes(b'fixture evidence')
        import hashlib
        ref = {'path': str(artifact), 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
        state = {'space': 'hall', 'body_ids': ['Kenneth'], 'characters': [{'id': 'Jill',
            'position': 'door', 'screen_direction': 'right', 'gaze': 'zombie',
            'action_phase': 'retreat', 'support': 'left foot', 'props': ['pistol']}]}
        self.review = {'status': 'PASS', 'reviewer': 'fixture reviewer', 'note': 'fixture temporal review',
            'observation_mode': 'temporal_video', 'artifact': ref, 'interval_seconds': [0, 1]}
        self.data = {'schema_version': '1.0', 'map': ref, 'spaces': ['hall'],
            'cameras': [{'id': 'A', 'space': 'hall', 'axis': 'Jill-zombie', 'landmarks': ['door'],
                'purpose': 'show escape', 'trajectory': 'locked position'}],
            'takes': [{'id': tid, 'camera_id': 'A', 'purpose': 'escape', 'method_id': 'A',
                'initial_state': copy.deepcopy(state), 'final_state': copy.deepcopy(state),
                'review': copy.deepcopy(self.review)} for tid in ['T07', 'T08', 'T09']],
            'joins': [{'from': a, 'to': b, 'decision': 'DIRECT_KINETIC_CUT', 'reason': 'continue movement',
                'review': copy.deepcopy(self.review)} for a,b in [('T07','T08'), ('T08','T09')]],
            'pilot_take_ids': ['T07', 'T08'], 'pilot_review': copy.deepcopy(self.review),
            'sequence_review': copy.deepcopy(self.review)}

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_contract_does_not_infer_owner_approval(self):
        self.assertEqual(c.validate(self.data, stage='assembly')['owner_approval'], 'NOT_INFERRED')

    def test_missing_map_or_changed_evidence_blocks(self):
        self.data['map']['sha256'] = '0' * 64
        with self.assertRaises(c.CameraContractError): c.validate(self.data)

    def test_teleporting_body_state_requires_cause(self):
        self.data['takes'][0]['final_state']['body_ids'].append('extra corpse')
        with self.assertRaisesRegex(c.CameraContractError, 'corpo aparece'): c.validate(self.data)

    def test_skipped_boundary_is_not_a_complete_sequence(self):
        self.data['joins'].pop()
        with self.assertRaisesRegex(c.CameraContractError, 'Toda fronteira'): c.validate(self.data)

    def test_single_shot_pilot_does_not_qualify_join(self):
        self.data['pilot_take_ids'] = ['T07']
        with self.assertRaisesRegex(c.CameraContractError, 'fronteira real'): c.validate(self.data)

    def test_batch_waits_for_temporal_pilot_review(self):
        self.data['pilot_review']['observation_mode'] = 'frames_only'
        with self.assertRaisesRegex(c.CameraContractError, 'quadros estaticos'):
            c.validate(self.data, take_id='T09', stage='generation')
        c.validate(self.data, take_id='T07', stage='generation')

    def test_two_equivalent_failures_require_new_method(self):
        self.data['takes'][0]['attempts'] = [{'status': 'FAIL', 'failure_class': 'door geography',
            'method_id': 'A'}] * 2
        with self.assertRaisesRegex(c.CameraContractError, 'duas falhas'): c.validate(self.data)
        self.data['takes'][0]['method_id'] = 'new blocking'
        with self.assertRaisesRegex(c.CameraContractError, 'renomear metodo'): c.validate(self.data)
        self.data['takes'][0]['method_change'] = {'reason': 'new camera map and door blocking', 'artifact': self.data['map']}
        c.validate(self.data)

    def test_connector_requires_permission_and_missing_causal_action(self):
        self.data['joins'][0]['decision'] = 'GENERATED_MOVING_CONNECTOR'
        with self.assertRaisesRegex(c.CameraContractError, 'Conector'): c.validate(self.data)
        self.data['generatedConnectorAllowed'] = True
        self.data['joins'][0]['missing_causal_action'] = 'Jill runs to door'
        c.validate(self.data)

    def test_source_regeneration_blocks_assembly(self):
        self.data['joins'][0]['decision'] = 'REGENERATE_SOURCE'
        with self.assertRaisesRegex(c.CameraContractError, 'fonte incompat'):
            c.validate(self.data, stage='assembly')

    def require_flow_for_different_states(self):
        self.data['flow_join_policy'] = {'id': 'flow_different_states_connector_required_v1'}
        self.data['generatedConnectorAllowed'] = True
        for j in self.data['joins']: j['state_relation'] = 'COMPATIBLE'
        j = self.data['joins'][0]
        j.update(state_relation='DIFFERENT', decision='GENERATED_MOVING_CONNECTOR',
                 missing_causal_action='Move from supported crouch to doorway',
                 flow={'method': 'minimax_h3_flow_aligned_regenerate'})
        return j

    def test_different_states_cannot_use_a_dry_cut(self):
        j = self.require_flow_for_different_states(); j['decision'] = 'DIRECT_KINETIC_CUT'
        with self.assertRaisesRegex(c.CameraContractError, 'Estados diferentes'):
            c.validate(self.data)

    def test_different_states_cannot_substitute_crossfade_for_flow(self):
        j = self.require_flow_for_different_states(); j['flow']['method'] = 'crossfade'
        with self.assertRaisesRegex(c.CameraContractError, 'Estados diferentes'):
            c.validate(self.data)

    def test_unknown_state_compatibility_blocks_assembly(self):
        self.require_flow_for_different_states()
        self.data['joins'][0].update(state_relation='UNKNOWN', decision='DIRECT_KINETIC_CUT')
        with self.assertRaisesRegex(c.CameraContractError, 'Compatibilidade'):
            c.validate(self.data, stage='assembly')

    def test_flow_graph_without_actual_execution_is_not_enough(self):
        import json, hashlib
        j = self.require_flow_for_different_states()
        graph = self.root/'flow.json'
        graph.write_text(json.dumps({'flow': {'class_type': 'H3PartitionedExactPrefixDiagnosticHandoff'}}), encoding='utf-8')
        j['flow']['workflow'] = {'path': str(graph), 'sha256': hashlib.sha256(graph.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(c.CameraContractError, 'execucao concluida'):
            c.validate(self.data, stage='assembly')

    def test_maestro_readiness_exposes_missing_camera_contract(self):
        from h3_workflow import take_readiness
        result = take_readiness({'sequenceCameraRequired': True, 'takeId': 'T07'})
        gate = next(g for g in result['gates'] if g['id']=='sequence_camera')
        self.assertFalse(gate['pass']); self.assertFalse(result['ready'])

    def test_assembly_guard_rejects_unreviewed_sequence_before_encoder(self):
        import json
        from unittest.mock import patch
        from project_assembly import assemble_project, AssemblyError
        self.data['sequence_review']['status'] = 'PENDING'
        (self.root/'sequence_camera_contract.json').write_text(json.dumps(self.data),encoding='utf-8')
        with patch('project_assembly._require_h264_nvenc') as encoder:
            with self.assertRaises(AssemblyError):
                assemble_project(self.root, sources=[{'takeId':'T07'}], source_fingerprint='fixture',
                    job_id='fixture',ffmpeg='not_called',ffprobe='not_called')
        encoder.assert_not_called()


if __name__ == '__main__': unittest.main()
