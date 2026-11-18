"""Reversible local installation/inventory. No service calls or GPU execution."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
RUNTIME = Path("D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara")
USER = Path("D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user/default/workflows")
NODE_ROOT = RUNTIME / "custom_nodes/pemara_h3_face_refine"
sys.path.insert(0, str(WORKSPACE / "services/studio"))
from h3_face_refine import NODE, SAGE_GUARD, ensure_face_refine, policy


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data, receipt):
    path = Path(path)
    old = path.read_bytes() if path.exists() else None
    content = data if isinstance(data, bytes) else data.encode("utf-8")
    if old == content:
        return
    backup = None
    if old is not None:
        backup = ROOT / "rollback" / (hashlib.sha256(str(path).encode()).hexdigest()[:12] + "_" + path.name)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(old)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".face-refine.tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    receipt.append({"path": str(path), "before": hashlib.sha256(old).hexdigest() if old is not None else None,
                    "after": sha(path), "backup": str(backup) if backup else None})


def is_api(data):
    return isinstance(data, dict) and bool(data) and all(isinstance(v, dict) and "class_type" in v for v in data.values())


def frontend_refine(data):
    """Insert one visible adapter per native H3 video; preserve every old widget."""
    graph = deepcopy(data)
    nodes = {str(n["id"]): n for n in graph.get("nodes", [])}
    links = {x[0]: x for x in graph.get("links", [])}
    api = {}
    for nid, n in nodes.items():
        values = {}
        for inp in n.get("inputs", []):
            link = links.get(inp.get("link"))
            if link:
                values[inp["name"]] = [str(link[1]), link[2]]
        kind = n["type"]
        widgets = n.get("widgets_values") or []
        if kind in {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo"}:
            if "prompt" not in values:
                values["prompt"] = widgets[0] if widgets else ""
        if kind == "RandomNoise":
            values.setdefault("noise_seed", widgets[0] if widgets else 0)
        if kind == "CreateVideo":
            values.setdefault("fps", widgets[0] if widgets else 24.)
        if kind in {"SaveVideo", "VHS_VideoCombine"}:
            if kind == "SaveVideo":
                values.setdefault("filename_prefix", widgets[0] if widgets else "PEMARA_H3")
            elif isinstance(widgets, dict):
                values.update({key: value for key, value in widgets.items() if key not in values})
        api[nid] = {"class_type": kind, "inputs": values}
    updated = ensure_face_refine(api)
    added = [(key, n) for key, n in updated.items() if key not in api]
    next_node = max((int(key) for key in nodes if key.isdigit()), default=0)+1
    next_link = max(links, default=0)+1
    for key, n in added:
        nid = next_node; next_node += 1
        values = n["inputs"]
        if n['class_type'] == SAGE_GUARD:
            origin, output = values['model']
            source_node = nodes[origin]
            outgoing = source_node['outputs'][output].get('links') or []
            reroute = [link_id for link_id in outgoing
                       if link_id in links and
                       updated[str(links[link_id][3])].get('inputs', {}).get('model') == [key, 0]]
            pos = source_node.get('pos', [0, 0])
            fresh = {'id': nid, 'type': SAGE_GUARD, 'title': 'PEMARA — Sage: sequencia longa',
                     'pos': [pos[0] + 340, pos[1] + 220], 'size': [320, 100],
                     'flags': {}, 'order': len(nodes), 'mode': 0,
                     'inputs': [{'name': 'model', 'type': 'MODEL', 'link': next_link}],
                     'outputs': [{'name': 'MODEL', 'type': 'MODEL', 'links': reroute, 'slot_index': 0}],
                     'properties': {'Node name for S&R': SAGE_GUARD},
                     'widgets_values': [values['head_chunks']]}
            source_node['outputs'][output]['links'] = [x for x in outgoing if x not in reroute] + [next_link]
            graph['links'].append([next_link, int(origin), output, nid, 0, 'MODEL'])
            next_link += 1
            for link_id in reroute:
                links[link_id][1:3] = [nid, 0]
            graph['nodes'].append(fresh)
            nodes[str(nid)] = fresh
            continue
        input_names = [("images", "IMAGE"), ("clip", "CLIP"), ("vae", "VAE")]
        if "audio" in values:
            input_names.append(("audio", "AUDIO"))
        widget_names = ["source_prompt", "fps", "seed", "filename_prefix", "enabled", "steps", "denoise", "canvas_size", "detector", "confidence"]
        for name in widget_names:
            if isinstance(values[name], list):
                input_names.append((name, {"source_prompt":"STRING", "fps":"FLOAT", "seed":"INT", "filename_prefix":"STRING"}[name]))
        target_id = key.removeprefix("pemara_face_refine_")
        target = nodes[target_id]
        pos = target.get("pos", [1800, 0])
        fresh = {"id": nid, "type": NODE, "title": "PEMARA — Face Refine (original preservado)",
                 "pos": [pos[0]-470, pos[1]+300], "size": [420, 420], "flags": {}, "order": len(nodes), "mode": 0,
                 "inputs": [{"name": name, "type": dtype, "link": None} for name,dtype in input_names],
                 "outputs": [{"name":"refined_images", "type":"IMAGE", "links":[], "slot_index":0},
                             {"name":"report", "type":"STRING", "links":[], "slot_index":1}],
                 "properties": {"Node name for S&R": NODE},
                 "widgets_values": [values[name] if not isinstance(values[name], list) else "" for name in widget_names]}
        for slot, inp in enumerate(fresh["inputs"]):
            origin, output = values[inp["name"]]
            inp["link"] = next_link
            nodes[origin]["outputs"][output].setdefault("links", [])
            if nodes[origin]["outputs"][output]["links"] is None:
                nodes[origin]["outputs"][output]["links"] = []
            nodes[origin]["outputs"][output]["links"].append(next_link)
            graph["links"].append([next_link, int(origin), output, nid, slot, inp["type"]])
            next_link += 1
        field = "images"
        target_slot = next(i for i,x in enumerate(target["inputs"]) if x["name"] == field)
        old_link_id = target["inputs"][target_slot]["link"]
        old_link = links[old_link_id]
        nodes[str(old_link[1])]["outputs"][old_link[2]]["links"].remove(old_link_id)
        old_link[1:3] = [nid, 0]
        fresh["outputs"][0]["links"].append(old_link_id)
        graph["nodes"].append(fresh)
        nodes[str(nid)] = fresh
    graph["last_node_id"] = max(graph.get("last_node_id", 0), next_node-1)
    graph["last_link_id"] = max(graph.get("last_link_id", 0), next_link-1)
    if added:
        graph.setdefault("extra", {})["pemara_face_refine"] = policy()
    return graph, len(added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.install:
        raise SystemExit("Face Refine retired by owner. Installation is disabled.")
    changes, inventory = [], []
    if args.install:
        for name in ("__init__.py", "nodes.py", "stable_sage.py"):
            write(NODE_ROOT/name, (ROOT/"node"/name).read_bytes(), changes)
        write(NODE_ROOT/"graph.py", (WORKSPACE/"services/studio/h3_face_refine.py").read_bytes(), changes)
        write(NODE_ROOT/"upstream/__init__.py", b"# Pinned unmodified T8 source modules. GPL-3.0-or-later.\n", changes)
        for name in ("core.py", "sampling.py", "face_refine_advanced.py"):
            write(NODE_ROOT/"upstream"/name, (ROOT/"t8_source/h3_t8"/name).read_bytes(), changes)
        write(NODE_ROOT/"LICENSE", (ROOT/"t8_source/LICENSE").read_bytes(), changes)
        write(NODE_ROOT/"UPSTREAM.json", json.dumps({"repository":"https://github.com/T8mars/comfyui-minimax-h3-audio-T8",
              "commit":"772ce05a4531fe5452e277a649ff4dab9fc03418", "license":"GPL-3.0-or-later",
              "files":{name:sha(ROOT/"t8_source/h3_t8"/name) for name in ("core.py","sampling.py","face_refine_advanced.py")}},indent=2),changes)
    roots = [USER, WORKSPACE/"ferramentas/h3_upgrades_20260927/workflows",
             WORKSPACE/"ferramentas/video_global_engine/workflows/minimax_h3_live_action"]
    roots.extend(RUNTIME.joinpath("custom_nodes").glob("creative_os_h3_*/workflows"))
    roots.extend(RUNTIME.joinpath("custom_nodes").glob("creative_os_h3_*/example_workflows"))
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            if any(part in {"rollback", "archive", "receipts", ".git"} for part in path.parts):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                if is_api(data):
                    transformed = ensure_face_refine(data)
                    has_h3 = any(n.get("class_type") in {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo"} for n in data.values())
                    if has_h3:
                        # Old extension templates predate the native dynamic-combo
                        # codec input. Preserve the requested codec when migrating.
                        for node in transformed.values():
                            if node.get("class_type") == "SaveVideo":
                                values = node["inputs"]
                                values.setdefault("format.codec", values.pop("codec", "h264"))
                    added = sum(n.get("class_type")==NODE for n in transformed.values())
                    kind = "api"
                elif isinstance(data,dict) and isinstance(data.get("nodes"),list):
                    has_h3 = any(n.get("type") in {"MiniMaxH3ImageToVideo","MiniMaxH3ReferenceToVideo"} for n in data["nodes"])
                    transformed, _ = frontend_refine(data)
                    added = sum(n.get("type")==NODE for n in transformed["nodes"])
                    kind = "frontend"
                elif isinstance(data,dict) and data.get("engine")=="minimax_h3":
                    transformed=deepcopy(data); transformed["faceRefine"]=policy()
                    required=transformed.get("nodeContract",{}).get("required",[])
                    if required and NODE not in required: required.append(NODE)
                    has_h3,added,kind=True,1,"descriptor"
                else:
                    continue
                if not has_h3:
                    continue
                record={"path":str(path),"kind":kind,"face_refine_nodes":added,"status":"covered" if added else "runtime_hook_required"}
                if args.install and transformed!=data:
                    write(path,json.dumps(transformed,ensure_ascii=False,indent=2)+"\n",changes)
                inventory.append(record)
            except Exception as exc:
                inventory.append({"path":str(path),"status":"error","error":str(exc)})
    receipt={"time":time.time(),"policy":policy(),"inventory":inventory,"changes":changes,
             "historical_media_and_project_jobs":"preserved; new submissions covered by runtime hook"}
    (ROOT/"receipts").mkdir(exist_ok=True)
    previous_path=ROOT/"receipts/deployment.json"
    if args.install and previous_path.exists():
        previous=json.loads(previous_path.read_text(encoding="utf-8"))
        combined={x["path"]:x for x in previous.get("changes",[])}
        for item in changes:
            if item["path"] in combined:
                combined[item["path"]]["after"]=item["after"]
            else:
                combined[item["path"]]=item
        receipt["changes"]=list(combined.values())
    (ROOT/"receipts"/("deployment.json" if args.install else "inventory.json")).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"workflows":len(inventory),"covered":sum(x["status"]=="covered" for x in inventory),
                     "errors":[x for x in inventory if x["status"]=="error"],"changes":len(changes)},ensure_ascii=False))


if __name__ == "__main__":
    main()
