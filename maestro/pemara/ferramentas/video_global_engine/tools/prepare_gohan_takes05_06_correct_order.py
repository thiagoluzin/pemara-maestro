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
COMBAT_REGISTRY = PROJECT / "qc" / "approved_take05_combat_multianchor_registry.json"
TZ = ZoneInfo("America/Sao_Paulo")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def anchor(raw: dict) -> dict:
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
    main_anchors = read(MAIN_REGISTRY)["anchors"]
    combat_anchors = read(COMBAT_REGISTRY)["anchors"]
    anchors = {
        "F": anchor(main_anchors["F"]),
        "G": anchor(main_anchors["G"]),
        "H": anchor(main_anchors["H"]),
        "I": anchor(main_anchors["I"]),
        "K1": anchor(combat_anchors["K1"]),
        "K2": anchor(combat_anchors["K2"]),
        "K3": anchor(combat_anchors["K3"]),
    }
    replaced_ids = {"05A", "05B", "05C", "05D", "06A", "06B"}
    queue["takes"] = [take for take in queue["takes"] if str(take.get("id")) not in replaced_ids]
    main05 = next(take for take in queue["takes"] if str(take.get("id")) == "05")
    main06 = next(take for take in queue["takes"] if str(take.get("id")) == "06")
    for take in (main05, main06):
        take["render_authorized"] = False
        take["video_generation"]["render_authorized"] = False
        take["status"] = "INTERNAL_SEGMENTS_PENDING"
        take["maestro_status"] = "READY"
        take["maestro_last_job_id"] = ""
        take["maestro_last_error"] = ""
        take["video"] = {
            "status": "pending_internal_microsegments",
            "output_active": "",
            "output_preview": "",
        }
    main05["internal_anchors"] = [
        {**copy.deepcopy(anchors[label]), "label": label}
        for label in ("K1", "K2", "K3")
    ]
    main06["internal_anchors"] = [{**copy.deepcopy(anchors["G"]), "label": "G"}]

    def make(parent: dict, micro_id: str, name: str, start: str, end: str,
             prompt: str, early: str, middle: str, late: str) -> dict:
        return base.micro_take(
            parent, micro_id, name, anchors[start], anchors[end], start, end,
            prompt, early, middle, late,
        )

    micros = [
        make(
            main05, "05A", "INTERNAL 05A — recuperação e parry F-K1", "F", "K1",
            (
                "One uninterrupted photorealistic live-action 5.125-second recovery-and-parry segment between the exact approved frames. "
                "Completely tailless Perfect Cell inherits upward displacement, stabilizes only through momentum and throws one immediate counter. SSJ2 Gohan pursues, crosses real distance and catches the counter in a moving parry without resetting. "
                "The camera cranes after the launch then dives into a close physical orbit; foreground rubble, armor, cloth and lightning keep independent inertia. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, third rear blade, duplicated body, extra limb, held launch pose, turn-taking, freeze or internal cut."
            ),
            "Cell is already displaced upward while Gohan and the crane camera continue the chase.",
            "Cell stabilizes through inertia and counters; Gohan closes real distance as debris crosses several depth planes.",
            "Gohan reaches the approved moving parry with both bodies and camera still translating.",
        ),
        make(
            main05, "05B", "INTERNAL 05B — parry e golpe no corpo K1-K2", "K1", "K2",
            (
                "One uninterrupted photorealistic live-action 5.125-second combat segment between the exact approved frames. "
                "SSJ2 Gohan converts the moving parry into one heavy body punch that visibly bends and displaces completely tailless Perfect Cell. Cell attempts to rotate out but never receives a free pause. "
                "A close physical orbit crosses foreground masonry while cloth, armor, dust and lightning react to contact. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, extra limb, fused hands, repeated punch loop, slow motion, static contact, freeze or internal cut."
            ),
            "The approved parry continues with both fighters already crossing the frame.",
            "Gohan changes angle and drives one heavy body punch with visible recoil, reaction and displacement.",
            "The contact reaches the approved body-punch geometry while the camera and debris continue beyond it.",
        ),
        make(
            main05, "05C", "INTERNAL 05C — transferência e joelhada K2-K3", "K2", "K3",
            (
                "One uninterrupted photorealistic live-action 5.125-second rising-impact segment between the exact approved frames. "
                "SSJ2 Gohan follows the body punch through, changes height and drives a rising knee that lifts completely tailless Perfect Cell onto a new vector. "
                "The camera drops under the action and swings upward; terrain damage, dust, cloth, armor and lightning progress every second. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, duplicate fighter, extra limb, repeated punch, static tableau, slow pose, freeze or internal cut."
            ),
            "The body punch follow-through keeps Cell displaced and Gohan advancing.",
            "Gohan changes level under Cell's guard while the camera physically drops and foreground debris changes overlap.",
            "The rising knee reaches the approved active impact and sends Cell onto a visibly different vector.",
        ),
        make(
            main05, "05D", "INTERNAL 05D — joelhada e pressão K3-H", "K3", "H",
            (
                "One uninterrupted photorealistic live-action 5.125-second pressure handoff between the exact approved frames. "
                "The rising knee continues to displace completely tailless Perfect Cell; SSJ2 Gohan overtakes him, denies one desperate guard and ends physically pressing him at close range without stopping. "
                "The camera banks from the rising blow into a fast lateral arc as rocks, dust, armor and aura cross separate depth planes. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, duplicate body, repeated loop, turn-taking, victory pose, freeze, static ending or internal cut."
            ),
            "Cell inherits the knee's upward-sideways vector while Gohan immediately pursues.",
            "Gohan overtakes Cell and denies one moving guard through a new impact angle and progressive terrain damage.",
            "Both reach the approved close-pressure geometry with bodies, debris and camera still moving into Take 06.",
        ),
        make(
            main06, "06A", "INTERNAL 06A — pressão e lançamento H-G", "H", "G",
            (
                "One uninterrupted photorealistic live-action 5.125-second launch segment between the exact approved frames. "
                "SSJ2 Gohan continues the inherited close pressure with two escalating heavy contacts, then one decisive blow launches completely tailless Perfect Cell across the ruined arena and through a stone breach. "
                "The camera moves from close orbit into a deep chase; foreground rock, midground fighters and distant walls change scale and overlap continuously. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, duplicated limb, repeated punch loop, pause before launch, static flight, freeze or internal cut."
            ),
            "Gohan and Cell are already locked in moving close pressure as the camera arcs beside them.",
            "Two distinct contacts increase displacement, height and terrain damage without a turn-taking pause.",
            "The decisive launch sends Cell through the approved moving breach while Gohan and camera pursue.",
        ),
        make(
            main06, "06B", "INTERNAL 06B — perseguição e Kamehameha G-I", "G", "I",
            (
                "One uninterrupted photorealistic live-action 5.125-second finishing segment between the exact approved frames. "
                "Completely tailless Perfect Cell is already flying through the breach. SSJ2 Gohan catches the same vector, lands one final redirecting impact, gathers blue-white energy only during motion and fires an immediate powerful Kamehameha that carries Cell into the mountain. "
                "The mountain face ruptures while debris, dust, beam light, aura and the pursuing camera remain active through the last frame. "
                "No animation, anime, cel shading, game render, plastic CGI, tail, beam passing through Gohan, long charge pose, duplicate Cell, static explosion, freeze, gore or internal cut."
            ),
            "Cell and Gohan inherit the wall-breach chase with high depth velocity and moving foreground rubble.",
            "Gohan catches, redirects and gathers energy without stopping while the camera banks toward the mountain corridor.",
            "The immediate Kamehameha carries Cell into the approved active mountain rupture with all layers still moving.",
        ),
    ]
    queue["takes"].extend(micros)
    queue["updated_at"] = now
    queue["overnight_generation"]["canceled_inverted_jobs"] = {
        "05A": "73c34637780346e685470254c2811beb",
        "05B": "1b06742cd4ea4897b2fe28b3d6a59ee7",
        "06": "a71516b8b0434d3b9bf89f788676fae8",
    }
    queue["overnight_generation"]["corrected_story_chain"] = {
        "take05": ["F", "K1", "K2", "K3", "H"],
        "take06": ["H", "G", "I"],
        "reason": "pressure must precede launch and Kamehameha",
    }
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
        "take05_microsegments": ["05A", "05B", "05C", "05D"],
        "take06_microsegments": ["06A", "06B"],
        "take05_chain": ["F", "K1", "K2", "K3", "H"],
        "take06_chain": ["H", "G", "I"],
        "auto_approval": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
