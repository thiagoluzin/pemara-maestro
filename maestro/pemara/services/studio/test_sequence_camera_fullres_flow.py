from copy import deepcopy
from sequence_camera_contract import _full_resolution_flow_connected


def graph():
    return {
        'trajectory': {'class_type': 'H3FlowTrajectory', 'inputs': {}},
        'capture': {'class_type': 'H3TrajectoryCapture', 'inputs': {'model': ['base', 0], 'trajectory': ['trajectory', 0]}},
        'regen': {'class_type': 'H3FlowAlignedRegenerate', 'inputs': {'model': ['base', 0], 'trajectory': ['trajectory', 0], 'guidance_mode': 'direction', 'direction_weight': .35, 'source_conditioning': ['source', 0]}},
        'cg': {'class_type': 'BasicGuider', 'inputs': {'model': ['capture', 0], 'conditioning': ['source', 0]}},
        'rg': {'class_type': 'BasicGuider', 'inputs': {'model': ['regen', 0], 'conditioning': ['target', 0]}},
        'cs': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'guider': ['cg', 0], 'noise': ['noise', 0], 'sampler': ['solver', 0], 'sigmas': ['sigmas', 0], 'latent_image': ['empty', 0]}},
        'rs': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'guider': ['rg', 0], 'noise': ['noise', 0], 'sampler': ['solver', 0], 'sigmas': ['sigmas', 0], 'latent_image': ['cs', 0]}},
    }


def test_full_resolution_flow_requires_capture_dependency_and_matching_trajectory():
    valid = graph()
    assert _full_resolution_flow_connected(valid)
    for node, field, value in [('rs', 'latent_image', ['empty', 0]), ('capture', 'trajectory', ['other', 0]), ('regen', 'guidance_mode', 'off'), ('rs', 'noise', ['different', 0]), ('capture', 'model', ['other_model', 0]), ('cg', 'conditioning', ['different_condition', 0])]:
        invalid = deepcopy(valid)
        invalid[node]['inputs'][field] = value
        assert not _full_resolution_flow_connected(invalid)


def test_orphan_flow_node_is_not_execution_evidence():
    assert not _full_resolution_flow_connected({'regen': {'class_type': 'H3FlowAlignedRegenerate', 'inputs': {}}})
