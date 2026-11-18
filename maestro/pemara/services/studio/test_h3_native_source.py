from copy import deepcopy
import pytest
from h3_acceleration import SAMPLING_CONSUMERS, model_chain
from h3_native_source import NODE, validate_native_source
from h3_workflow import ensure_h3_sage_attention
from test_h3_acceleration import source as base_source


def source():
    graph = base_source()
    graph['vdn'] = {'class_type': 'ApplyVDNH3', 'inputs': {'model': ['load', 0], 'strength': 1.0}}
    for key in ('guide', 'schedule'):
        graph[key]['inputs']['model'] = ['vdn', 0]
    return graph


def test_continuum_and_scheduler_share_initial_model_and_exact_av_policy():
    graph = source()
    graph['continuum'] = {'class_type': 'H3ContinuumSamplerV34', 'inputs': {'model': ['vdn', 0]}}
    ensure_h3_sage_attention(graph)
    links = [graph[key]['inputs']['model'] for key in ('guide', 'schedule', 'continuum')]
    assert links[0] == links[1] == links[2]
    flow = graph[links[0][0]]
    assert flow['class_type'] == NODE
    assert flow['inputs']['source_prefix_projection'] == 'native_source_carry'
    assert flow['inputs']['audio_guided_overlap_mode'] == 'sampler_mask_exact_timestep'
    assert flow['inputs']['uniform_source_detail_transport'] is True
    assert [n['class_type'] for _, n in model_chain(graph, links[0][0])][:2] == [NODE, 'SpectrumApplyMiniMaxH3']
    assert ensure_h3_sage_attention(deepcopy(graph)) == graph


def test_native_split_model_and_bicubic_fallback_are_rejected():
    graph = ensure_h3_sage_attention(source())
    key = graph['guide']['inputs']['model'][0]
    broken = deepcopy(graph)
    broken['schedule']['inputs']['model'] = graph[key]['inputs']['model']
    with pytest.raises(ValueError, match='MODEL_PATH'):
        validate_native_source(broken, SAMPLING_CONSUMERS)
    graph[key]['inputs']['source_prefix_projection'] = 'latent_bicubic'
    with pytest.raises(ValueError, match='CARRY_REQUIRED'):
        validate_native_source(graph, SAMPLING_CONSUMERS)


def test_explicit_historical_flow_is_not_migrated_to_native_carry():
    graph = source()
    graph['legacy'] = {'class_type': 'H3PartitionedExactPrefixDiagnosticHandoff',
                       'inputs': {'model': ['load', 0], 'spatial_stage_control': 'progressive_uniform_source'}}
    for key in ('guide', 'schedule'):
        graph[key]['inputs']['model'] = ['legacy', 0]
    ensure_h3_sage_attention(graph)
    assert not any(n['class_type'] == NODE for n in graph.values())
    assert graph['legacy']['inputs']['spatial_stage_control'] == 'progressive_uniform_source'


def test_direct_take_keeps_base_h3_without_unqualified_continuation():
    graph = ensure_h3_sage_attention(base_source())
    assert not any(n['class_type'] == NODE for n in graph.values())
    assert [n['class_type'] for _, n in model_chain(graph, graph['guide']['inputs']['model'][0])][:3] == [
        'SpectrumApplyMiniMaxH3', 'PemaraH3SageLongSequencePatch', 'MiniMaxH3MemoryEfficientSageAttentionPatch']
    assert ensure_h3_sage_attention(deepcopy(graph)) == graph


def test_continuation_without_vdn_is_rejected_before_submission():
    graph = base_source()
    graph['continuum'] = {'class_type': 'H3ContinuumSamplerV34', 'inputs': {'model': ['load', 0]}}
    with pytest.raises(ValueError, match='VDN_REQUIRED'):
        ensure_h3_sage_attention(graph)


def test_imported_native_source_does_not_silently_fall_back_without_vdn():
    graph = ensure_h3_sage_attention(source())
    for node in graph.values():
        if node.get('inputs', {}).get('model') == ['vdn', 0]:
            node['inputs']['model'] = ['load', 0]
    del graph['vdn']
    with pytest.raises(ValueError, match='VDN_REQUIRED'):
        validate_native_source(graph, SAMPLING_CONSUMERS)
    with pytest.raises(ValueError, match='VDN_REQUIRED'):
        ensure_h3_sage_attention(deepcopy(graph))


def test_disconnected_or_disabled_vdn_cannot_qualify_flow():
    graph = base_source()
    graph['orphan_vdn'] = {'class_type': 'ApplyVDNH3', 'inputs': {'model': ['load', 0], 'strength': 1}}
    ensure_h3_sage_attention(graph)
    assert not any(n['class_type'] == NODE for n in graph.values())
    graph = source()
    graph['vdn']['inputs']['strength'] = 0
    with pytest.raises(ValueError, match='VDN_REQUIRED'):
        ensure_h3_sage_attention(graph)
