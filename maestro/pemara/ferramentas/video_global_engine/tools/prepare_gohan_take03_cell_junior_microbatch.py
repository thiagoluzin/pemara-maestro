from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import prepare_gohan_overnight_vejito_batch as base


PROJECT = base.PROJECT
QUEUE_PATH = PROJECT / "take_queue.json"
PRODUCTION_PATH = PROJECT / "production_manifest.json"
PROJECT_PATH = PROJECT / "project_manifest.json"
MAIN_REGISTRY = PROJECT / "qc" / "approved_anchor_registry.json"
JUNIOR_REGISTRY = PROJECT / "qc" / "approved_cell_junior_multianchor_registry.json"
TZ = ZoneInfo("America/Sao_Paulo")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def anchor_record(raw: dict) -> dict:
    return {
        "file": raw["file"],
        "metadata": raw["metadata"],
        "sha256": raw["sha256"],
        "status": "approved_for_video",
    }


def main() -> None:
    now = datetime.now(TZ).isoformat()
    queue = read(QUEUE_PATH)
    production = read(PRODUCTION_PATH)
    project = read(PROJECT_PATH)
    main_registry = read(MAIN_REGISTRY)["anchors"]
    junior_registry = read(JUNIOR_REGISTRY)["anchors"]
    anchors = {
        "D": anchor_record(main_registry["D"]),
        "J1": anchor_record(junior_registry["J1"]),
        "J2": anchor_record(junior_registry["J2"]),
        "J3": anchor_record(junior_registry["J3"]),
        "J4": anchor_record(junior_registry["J4"]),
        "E": anchor_record(main_registry["E"]),
    }
    queue["takes"] = [
        take for take in queue["takes"]
        if str(take.get("id")) not in {"03A", "03B", "03C", "03D", "03E"}
    ]
    main_take = next(take for take in queue["takes"] if str(take.get("id")) == "03")
    main_take["render_authorized"] = False
    main_take["video_generation"]["render_authorized"] = False
    main_take["status"] = "INTERNAL_SEGMENTS_PENDING"
    main_take["maestro_status"] = "READY"
    main_take["maestro_last_job_id"] = ""
    main_take["maestro_last_error"] = ""
    main_take["video"] = {
        "status": "pending_internal_microsegments",
        "output_active": "",
        "output_preview": "",
    }
    main_take["internal_anchors"] = [
        {**copy.deepcopy(anchors[label]), "label": label}
        for label in ("J1", "J2", "J3", "J4")
    ]

    def make(micro_id: str, name: str, start: str, end: str, prompt: str,
             early: str, middle: str, late: str) -> dict:
        return base.micro_take(
            main_take, micro_id, name, anchors[start], anchors[end], start, end,
            prompt, early, middle, late,
        )

    microtakes = [
        make(
            "03A", "INTERNAL 03A — arrancada SSJ2 D-J1", "D", "J1",
            (
                "One uninterrupted photorealistic live-action 5.125-second launch between the exact approved frames. "
                "SSJ2 Gohan explodes out of the transformation and crosses real arena distance toward exactly two compact child-sized cyan-blue Cell Juniors. "
                "Full-size completely tailless Perfect Cell remains behind and is never duplicated or transformed into a Junior. "
                "The camera drops from a short orbit into a fast ground-skimming pursuit; rocks, cloth, aura and background shift on separate depth planes. "
                "No animation, anime, cel shading, game render, plastic CGI, green Junior, full-size green clone, tail, duplicate Gohan, extra limb, pose hold, freeze or internal cut."
            ),
            "Gohan inherits rising debris and immediately leans into a real accelerating launch.",
            "The physical camera chases low as Gohan crosses the arena and two small blue Juniors enter on separate vectors.",
            "Gohan and exactly two compact blue Juniors reach the approved moving interception geometry without stopping.",
        ),
        make(
            "03B", "INTERNAL 03B — primeiro Junior J1-J2", "J1", "J2",
            (
                "One uninterrupted photorealistic live-action 5.125-second first-impact segment between the exact approved frames. "
                "Exactly two compact child-sized cyan-blue Cell Juniors attack from different directions. SSJ2 Gohan evades the nearer attack and lands one heavy directional counter on the first Junior while the second keeps moving independently. "
                "The camera trucks and arcs through flying foreground rubble; the impact changes body position, terrain and depth. "
                "No full-size green Cell clone, no animation, anime, cel shading, game render, plastic CGI, tail, third Junior, repeated punch, turn-taking, freeze, gore or internal cut."
            ),
            "Two small blue Juniors close from different vectors as Gohan advances through the center.",
            "Gohan slips the nearer attack and drives one legible heavy counter through the first Junior's trajectory.",
            "The first impact reaches approved contact while the second blue Junior and camera remain in independent motion.",
        ),
        make(
            "03C", "INTERNAL 03C — transferência ao segundo J2-J3", "J2", "J3",
            (
                "One uninterrupted photorealistic live-action 5.125-second transfer segment between the exact approved frames. "
                "The first compact cyan-blue Cell Junior is irreversibly thrown out of the fight without gore; SSJ2 Gohan converts the same follow-through into a rapid intercept of the second compact cyan-blue Junior. "
                "The camera crosses behind foreground debris and changes height as impacts travel through dust, clothing and shattered ground. "
                "No full-size green clone, no Perfect Cell replacing a Junior, no animation, anime, cel shading, game render, plastic CGI, tail, duplicate fighter, repeated impact, pause, freeze or internal cut."
            ),
            "The first impact continues immediately and throws the first small blue Junior away from the active corridor.",
            "Gohan uses the same rotation to cross real distance toward the independently moving second blue Junior.",
            "The second interception reaches the approved new contact geometry while all depth planes remain active.",
        ),
        make(
            "03D", "INTERNAL 03D — segundo Junior e pivô J3-J4", "J3", "J4",
            (
                "One uninterrupted photorealistic live-action 5.125-second second-impact segment between the exact approved frames. "
                "SSJ2 Gohan completes one decisive heavy strike on the last compact cyan-blue Cell Junior, sending it away without blood, then uses the follow-through to pivot toward full-size completely tailless Perfect Cell. "
                "Blue energy fragments, rocks and dust separate across three depth planes while the camera physically swings with Gohan. "
                "No green Junior, no extra full-size Cell, no animation, anime, cel shading, game render, plastic CGI, tail, repeated punch, static victory pose, freeze or internal cut."
            ),
            "The second approved impact continues with both bodies and the camera crossing real distance.",
            "The last small blue Junior is sent out of the fight as terrain and blue energy fragments change the arena.",
            "Gohan converts the impact into the approved active pivot toward tailless full-size Cell without posing.",
        ),
        make(
            "03E", "INTERNAL 03E — perseguição ao Cell J4-E", "J4", "E",
            (
                "One uninterrupted photorealistic live-action 5.125-second pursuit handoff between the exact approved frames. "
                "Both compact blue Cell Juniors are gone from the fight. SSJ2 Gohan accelerates directly toward the one and only full-size completely tailless green Perfect Cell, who retreats and prepares a compact energy counter. "
                "Gohan, Cell, debris and a low arcing camera keep moving into the next take; perspective and overlap change every second. "
                "No surviving Junior, no full-size green clones, no animation, anime, cel shading, game render, plastic CGI, tail, extra fighter, energy passing through Gohan, static pose, freeze or internal cut."
            ),
            "Gohan inherits the pivot while the last blue energy debris clears behind him.",
            "He crosses the broken arena toward the single tailless full-size Cell as the camera arcs low through rubble.",
            "Gohan and Cell reach the approved active chase geometry that hands directly into the energy-slap take.",
        ),
    ]
    queue["takes"].extend(microtakes)
    queue["updated_at"] = now
    queue["overnight_generation"]["cell_junior_direct_job_canceled"] = (
        "152c96dba9de43ce81e91cf72177e2de"
    )
    queue["overnight_generation"]["cell_junior_microsegments"] = [
        "03A", "03B", "03C", "03D", "03E"
    ]
    queue["overnight_generation"]["job_order"] = [
        "01A", "01B", "02", "04", "05A", "05B", "06",
        "03A", "03B", "03C", "03D", "03E",
    ]
    production["takes"] = copy.deepcopy(
        [take for take in queue["takes"] if not take.get("internal_microsegment")]
    )
    production["updated_at"] = now
    production["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    project["updated_at"] = now
    project["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    write(QUEUE_PATH, queue)
    write(PRODUCTION_PATH, production)
    write(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "parent_take": "03",
        "microsegments": [take["id"] for take in microtakes],
        "approved_anchor_chain": ["D", "J1", "J2", "J3", "J4", "E"],
        "direct_job_canceled": "152c96dba9de43ce81e91cf72177e2de",
        "auto_approval": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
