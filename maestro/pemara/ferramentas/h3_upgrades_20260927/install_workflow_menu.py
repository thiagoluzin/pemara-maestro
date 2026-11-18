"""Create editable ComfyUI graphs from the exact MCP-validated API graphs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMAS = json.loads((ROOT / "receipts/node_catalog.json").read_text(encoding="utf-8"))
MENU = Path("D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user/default/workflows/PEMARA_H3_UPGRADES")
MENU.mkdir(parents=True, exist_ok=True)

for api_path in sorted((ROOT / "workflows").glob("0[1-4]*.api.json")):
    if "_smoke" in api_path.name:
        continue
    graph = json.loads(api_path.read_text(encoding="utf-8"))
    nodes, by_id, links = [], {}, []
    for index, (nid, api) in enumerate(graph.items()):
        kind, values = api["class_type"], api["inputs"]
        schema = SCHEMAS[kind]
        inputs, widgets = [], []
        for inp in schema["inputs"]:
            name = inp["name"]
            if inp["type"] == "COMFY_AUTOGROW_V3":
                continue
            if inp["is_link"]:
                if inp["required"] or name in values:
                    inputs.append({"name": name, "type": inp["type"], "link": None})
            else:
                value = values.get(name, inp["options"].get("default"))
                if value is None and inp.get("choices"):
                    value = inp["choices"][0]
                widgets.append(value)
                if kind == "RandomNoise" and name == "noise_seed":
                    widgets.append("fixed")
        for name, value in values.items():
            if "." in name and isinstance(value, list):
                source = graph[value[0]]
                output = SCHEMAS[source["class_type"]]["outputs"][value[1]]
                inputs.append({"name": name, "type": output["type"], "link": None})
        if kind == "SaveVideo":
            widgets = [values["filename_prefix"], "mp4", "h264"]
        if kind == "PreviewAny":
            widgets = [""]
        out = [{"name": x["name"], "type": x["type"], "links": [], "slot_index": i}
               for i, x in enumerate(schema["outputs"])]
        n = {"id": int(nid), "type": kind, "pos": [(index % 4) * 470, (index // 4) * 410],
             "size": [420, 320 if kind.startswith("MiniMaxH3") else 180], "flags": {},
             "order": index, "mode": 0, "inputs": inputs, "outputs": out,
             "properties": {"Node name for S&R": kind}, "widgets_values": widgets}
        nodes.append(n)
        by_id[nid] = n
    for nid, api in graph.items():
        for slot, inp in enumerate(by_id[nid]["inputs"]):
            value = api["inputs"].get(inp["name"])
            if not isinstance(value, list):
                continue
            link_id = len(links) + 1
            inp["link"] = link_id
            by_id[value[0]]["outputs"][value[1]]["links"].append(link_id)
            links.append([link_id, int(value[0]), value[1], int(nid), slot, inp["type"]])
    note_id = max(int(nid) for nid in graph) + 1
    nodes.append({"id": note_id, "type": "Note", "pos": [-490, 0], "size": [440, 300],
                  "flags": {}, "order": len(nodes), "mode": 0, "inputs": [], "outputs": [],
                  "properties": {}, "widgets_values": [
                      "PEMARA H3 upgrades 2026-09-27. Separate test route; owner artistic review pending. "
                      "SageAttention required. Native audio is OFF. PDD: euler, its own SIGMAS, "
                      "8 evaluations, shift 12/3; no Turbo or caches. ControlNet 2.0: 40 steps, "
                      "pose guide from the official ComfyUI example. Do not combine PDD and ControlNet "
                      "without a new compatibility test. API graph in the deployment package is the execution source."]})
    frontend = {"last_node_id": note_id, "last_link_id": len(links), "nodes": nodes,
                "links": links, "groups": [], "config": {}, "extra": {}, "version": 0.4}
    filename = api_path.name.replace(".api.json", ".json")
    data = json.dumps(frontend, indent=2)
    (ROOT / "workflows" / filename).write_text(data, encoding="utf-8")
    (MENU / filename).write_text(data, encoding="utf-8")
    print(MENU / filename)
