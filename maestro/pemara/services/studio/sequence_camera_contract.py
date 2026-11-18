"""Validate camera-production evidence, never classify a movie from metadata."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


class CameraContractError(ValueError):
    pass


def evidence(record):
    if not isinstance(record, dict) or not record.get('path') or not record.get('sha256'):
        raise CameraContractError('Evidencia exige caminho absoluto e SHA-256.')
    path = Path(record['path'])
    if not path.is_absolute() or not path.is_file():
        raise CameraContractError('Evidencia ausente: ' + str(path))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != record['sha256']:
        raise CameraContractError('Evidencia alterada: ' + str(path))


def review(record, label):
    if not isinstance(record, dict) or record.get('status') != 'PASS' or not record.get('reviewer') or not record.get('note'):
        raise CameraContractError(label + ': parecer pendente/reprovado.')
    if record.get('observation_mode') != 'temporal_video':
        raise CameraContractError(label + ': quadros estaticos nao comprovam movimento/ritmo.')
    evidence(record.get('artifact'))
    interval = record.get('interval_seconds')
    if not isinstance(interval, list) or len(interval) != 2 or not 0 <= interval[0] < interval[1]:
        raise CameraContractError(label + ': intervalo observado invalido.')


def _full_resolution_flow_connected(graph):
    """Recognize a real capture -> regenerate sampler dependency on one trajectory."""
    for regen_id, regen in graph.items():
        if regen.get('class_type') != 'H3FlowAlignedRegenerate':
            continue
        ri = regen.get('inputs', {})
        if ri.get('guidance_mode', 'off') == 'off' or float(ri.get('direction_weight', 0)) <= 0:
            continue
        trajectory = ri.get('trajectory')
        if not isinstance(trajectory, list) or not trajectory:
            continue
        if graph.get(trajectory[0], {}).get('class_type') != 'H3FlowTrajectory':
            continue
        captures = {key for key, node in graph.items()
                    if node.get('class_type') == 'H3TrajectoryCapture'
                    and node.get('inputs', {}).get('trajectory') == trajectory
                    and node.get('inputs', {}).get('model') == ri.get('model')}
        cg = {key for key, node in graph.items()
              if node.get('class_type') == 'BasicGuider'
              and node.get('inputs', {}).get('model', [None])[0] in captures
              and node.get('inputs', {}).get('conditioning') == ri.get('source_conditioning')}
        rg = {key for key, node in graph.items()
              if node.get('class_type') == 'BasicGuider'
              and node.get('inputs', {}).get('model') == [regen_id, 0]}
        samplers = {key: node.get('inputs', {}) for key, node in graph.items()
                    if node.get('class_type') == 'SamplerCustomAdvanced'
                    and node.get('inputs', {}).get('guider', [None])[0] in cg}
        for node in graph.values():
            ni = node.get('inputs', {})
            if node.get('class_type') != 'SamplerCustomAdvanced' or ni.get('guider', [None])[0] not in rg:
                continue
            dependency = ni.get('latent_image', [None])[0]
            if dependency in samplers and all(ni.get(k) == samplers[dependency].get(k)
                                               for k in ('noise', 'sampler', 'sigmas')):
                return True
    return False


def validate(data, *, take_id=None, stage='planning'):
    if data.get('schema_version') != '1.0' or stage not in {'planning', 'generation', 'assembly'}:
        raise CameraContractError('Contrato/etapa de camera desconhecido.')
    evidence(data.get('map'))
    spaces = data.get('spaces')
    if not isinstance(spaces, list) or not spaces or len(set(spaces)) != len(spaces):
        raise CameraContractError('Mapa exige espacos unicos.')
    cameras = {}
    for camera in data.get('cameras', []):
        if not camera.get('id') or camera['id'] in cameras or camera.get('space') not in spaces:
            raise CameraContractError('Camera sem ID unico ou espaco conhecido.')
        for field in ('axis', 'landmarks', 'purpose', 'trajectory'):
            if not camera.get(field):
                raise CameraContractError('Camera sem ' + field)
        cameras[camera['id']] = camera
    takes = data.get('takes')
    if not isinstance(takes, list) or not takes:
        raise CameraContractError('Sequencia sem takes.')
    ids = []
    for take in takes:
        tid = take.get('id')
        if not tid or tid in ids or take.get('camera_id') not in cameras:
            raise CameraContractError('Take sem ID unico ou camera do mapa.')
        ids.append(tid)
        for field in ('purpose', 'initial_state', 'final_state', 'method_id'):
            if not take.get(field):
                raise CameraContractError(tid + ': ausente ' + field)
        for state in (take['initial_state'], take['final_state']):
            if state.get('space') not in spaces or not state.get('characters') or not isinstance(state.get('body_ids'), list):
                raise CameraContractError(tid + ': estado/geografia/corpos incompletos.')
            for character in state['characters']:
                for field in ('id', 'position', 'screen_direction', 'gaze', 'action_phase', 'support', 'props'):
                    if field not in character or character[field] is None:
                        raise CameraContractError(tid + ': personagem sem ' + field)
        if take['initial_state']['body_ids'] != take['final_state']['body_ids'] and not take.get('body_change_cause'):
            raise CameraContractError(tid + ': corpo aparece/desaparece sem causa registrada.')
        failures = take.get('attempts', [])
        if len(failures) >= 2:
            a, b = failures[-2:]
            if a.get('status') == b.get('status') == 'FAIL' and a.get('failure_class') == b.get('failure_class') and a.get('method_id') == b.get('method_id'):
                if b.get('method_id') == take['method_id']:
                    raise CameraContractError(tid + ': duas falhas equivalentes; alterar metodo antes de repetir.')
                change = take.get('method_change') or {}
                if not change.get('reason'):
                    raise CameraContractError(tid + ': renomear metodo nao comprova mudanca de estrategia.')
                evidence(change.get('artifact'))
    joins = data.get('joins', [])
    if [(j.get('from'), j.get('to')) for j in joins] != list(zip(ids, ids[1:])):
        raise CameraContractError('Toda fronteira adjacente exige direcao planejada, sem saltos.')
    for join in joins:
        if join.get('decision') not in {'DIRECT_KINETIC_CUT', 'GENERATED_MOVING_CONNECTOR', 'REGENERATE_SOURCE'} or not join.get('reason'):
            raise CameraContractError('Junção sem decisao e motivo.')
        if join['decision'] == 'GENERATED_MOVING_CONNECTOR' and (data.get('generatedConnectorAllowed') is not True or not join.get('missing_causal_action')):
            raise CameraContractError('Conector sem permissao ou acao causal indispensavel.')
        flow_policy = data.get('flow_join_policy') or {}
        if flow_policy.get('id') == 'flow_different_states_connector_required_v1':
            relation = join.get('state_relation')
            if relation not in {'COMPATIBLE', 'DIFFERENT', 'UNKNOWN'}:
                raise CameraContractError('Junção exige comparacao explicita dos estados.')
            if relation == 'DIFFERENT':
                flow = join.get('flow') or {}
                if join['decision'] != 'GENERATED_MOVING_CONNECTOR' or flow.get('method') != 'minimax_h3_flow_aligned_regenerate':
                    raise CameraContractError('Estados diferentes exigem conector causal com Flow.')
                if stage == 'assembly':
                    evidence(flow.get('workflow'))
                    graph = json.loads(Path(flow['workflow']['path']).read_text(encoding='utf-8'))
                    full_resolution_flow = _full_resolution_flow_connected(graph)
                    if not full_resolution_flow and not any(str(node.get('class_type', '')).startswith(('H3PartitionedExactPrefix', 'H3Progressive', 'H3NativeSourceContinuationHandoff')) for node in graph.values()):
                        raise CameraContractError('Grafo do conector nao contem Flow real.')
                    execution = flow.get('execution') or {}
                    if execution.get('status') != 'completed' or not execution.get('prompt_id'):
                        raise CameraContractError('Flow sem execucao concluida; grafo nao basta.')
                    evidence(execution.get('artifact'))
                    if full_resolution_flow:
                        if int(execution.get('nonzero_guidance_events', 0)) <= 0:
                            raise CameraContractError('Flow em resolucao integral sem evidencia de guidance executado.')
                        evidence(execution.get('flow_metrics'))
            elif stage == 'assembly' and relation == 'UNKNOWN':
                raise CameraContractError('Compatibilidade de estados pendente.')
        if stage == 'assembly':
            if join['decision'] == 'REGENERATE_SOURCE':
                raise CameraContractError('Montagem contem fonte incompatível.')
            review(join.get('review'), 'Junção ' + join['from'] + '/' + join['to'])
    pilots = data.get('pilot_take_ids') or []
    if not pilots or any(t not in ids for t in pilots):
        raise CameraContractError('Escolher bloco piloto de maior risco.')
    if len(ids) > 1 and not any(a in pilots and b in pilots for a, b in zip(ids, ids[1:])):
        raise CameraContractError('Piloto deve incluir uma fronteira real, nao apenas um take isolado.')
    if stage == 'generation':
        if take_id not in ids:
            raise CameraContractError('Take nao pertence ao contrato.')
        if take_id not in pilots:
            review(data.get('pilot_review'), 'Bloco piloto antes do lote')
    if stage == 'assembly':
        for take in takes:
            review(take.get('review'), 'Take ' + take['id'])
        review(data.get('sequence_review'), 'Filme completo')
    return {'technical_contract_pass': True, 'stage': stage, 'take_id': take_id,
            'artistic_approval': 'NOT_INFERRED', 'owner_approval': 'NOT_INFERRED'}


def load_and_validate(path, *, take_id=None, stage='planning'):
    return validate(json.loads(Path(path).read_text(encoding='utf-8')), take_id=take_id, stage=stage)
