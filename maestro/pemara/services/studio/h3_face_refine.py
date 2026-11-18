"""Owner-removed Face Refine; preserve the independent H3 Sage guard."""
from copy import deepcopy

NODE = "PemaraH3FaceRefine"
CONDITIONERS = {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo", "MiniMaxH3AudioConditioningT8"}
VIDEO_INPUTS = {"CreateVideo": "images", "VHS_VideoCombine": "images", "SaveAnimatedWEBP": "images"}
SAGE = "MiniMaxH3MemoryEfficientSageAttentionPatch"
SAGE_GUARD = "PemaraH3SageLongSequencePatch"


def _ensure_sage_guard(result):
    """Protect only the H3 Sage model path, keeping full temporal context."""
    for sage_id, node in list(result.items()):
        if node.get("class_type") != SAGE:
            continue
        guards = [key for key, item in result.items()
                  if item.get("class_type") == SAGE_GUARD
                  and item.get("inputs", {}).get("model") == [sage_id, 0]]
        if guards:
            guard_id = guards[0]
        else:
            guard_id = "pemara_sage_guard_" + str(sage_id)
            while guard_id in result:
                guard_id += "_"
            result[guard_id] = {"class_type": SAGE_GUARD,
                               "inputs": {"model": [sage_id, 0], "head_chunks": 4}}
        for key, consumer in result.items():
            if key == guard_id or key in guards:
                continue
            inputs = consumer.get("inputs", {})
            if inputs.get("model") == [sage_id, 0]:
                inputs["model"] = [guard_id, 0]
    return result


def _links(value, graph):
    if isinstance(value, (list, tuple)) and len(value) == 2 and str(value[0]) in graph and isinstance(value[1], int):
        yield str(value[0])
    elif isinstance(value, dict):
        for item in value.values():
            yield from _links(item, graph)


def ancestors(graph, start):
    found, pending = set(), [str(start)]
    while pending:
        key = pending.pop()
        if key in found or key not in graph:
            continue
        found.add(key)
        pending.extend(_links(graph[key].get("inputs", {}), graph))
    return found




def remove_face_refine(graph):
    """Remove rejected facial processing, reconnecting original image sources."""
    result = deepcopy(graph)
    retired = {key: node for key, node in result.items() if node.get("class_type") == NODE}
    def original(value):
        seen = set()
        while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in retired:
            key, slot = value
            if slot != 0 or key in seen:
                raise ValueError("Unsupported Face Refine report consumer or cyclic image source")
            seen.add(key)
            value = retired[key]["inputs"]["images"]
        return value
    for key, node in result.items():
        if key not in retired:
            node["inputs"] = {name: original(value) for name, value in node.get("inputs", {}).items()}
    for key in retired:
        del result[key]
    return result


def ensure_face_refine(graph):
    """Compatibility entry point: Face Refine removed; retain the Sage correction."""
    return _ensure_sage_guard(remove_face_refine(graph))


def policy():
    return {"enabled": False, "default": False, "node": NODE,
            "scope": "all_local_h3_video_workflows", "audioPreserved": True,
            "status": "REMOVED_BY_OWNER", "ownerApproval": "REJECTED"}
