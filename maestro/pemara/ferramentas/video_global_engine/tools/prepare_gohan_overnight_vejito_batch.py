from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(
    r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos"
    r"\gohan_ssj2_android16_cell_6x10s_liveaction_v1"
)
QUEUE_PATH = PROJECT / "take_queue.json"
PRODUCTION_PATH = PROJECT / "production_manifest.json"
PROJECT_PATH = PROJECT / "project_manifest.json"
REGISTRY_PATH = PROJECT / "qc" / "approved_anchor_registry.json"
BACKUP_DIR = PROJECT / "qc" / "overnight_batch_preflight_backup"
TZ = ZoneInfo("America/Sao_Paulo")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_anchors(registry: dict) -> dict[str, dict]:
    if registry.get("image_generation_used") is not False:
        raise RuntimeError("O registro nao confirma reutilizacao exclusiva das ancoras aprovadas.")
    anchors = registry.get("anchors")
    if not isinstance(anchors, dict) or set(anchors) != set("ABCDEFGHI"):
        raise RuntimeError("O conjunto aprovado precisa conter exatamente A-I.")
    verified: dict[str, dict] = {}
    for anchor_id in "ABCDEFGHI":
        item = anchors[anchor_id]
        path = Path(str(item.get("file") or "")).resolve()
        if not path.is_relative_to(PROJECT.resolve()) or not path.is_file():
            raise RuntimeError(f"Ancora {anchor_id} ausente ou fora do projeto: {path}")
        actual = sha256(path)
        expected = str(item.get("sha256") or "").lower()
        if actual != expected:
            raise RuntimeError(f"SHA divergente na ancora {anchor_id}.")
        verified[anchor_id] = copy.deepcopy(item)
    return verified


CAMERAS = {
    "01": "low gravel-level lateral track into a short physical crane rise",
    "02": "tight physical orbit expanding into a fast ground-skimming chase",
    "03": "fast lateral tracking with short arcs around three separate impacts",
    "04": "side truck past the deflection followed by a close accelerating orbit",
    "05": "close combat orbit that opens into a deep valley pursuit",
    "06": "airborne pursuit that swings to a wide mountain-impact perspective",
}


def transition_contract(take: dict, *, start_label: str, end_label: str) -> dict:
    beats = take["motion_beats"]
    return {
        "camera_evidence": {
            "movement": CAMERAS[take["parent_take_id"] if take.get("parent_take_id") else take["id"]],
            "physical_translation": True,
            "perspective_change": (
                "foreground debris changes overlap and scale against the fighters and distant arena"
            ),
        },
        "real_depth": {
            "foreground": "fast dust, stones and energy fragments crossing near lens",
            "midground": "the principal fighters complete the irreversible action",
            "background": "arena ridges, mountains and sky shift more slowly",
            "differential_motion": (
                "near debris moves fastest, bodies move at medium speed and terrain moves slowest"
            ),
            "occlusion_or_scale_change": (
                "moving bodies and debris repeatedly change overlap and apparent scale"
            ),
        },
        "internal_action": {
            "primary_event": take["story_change"],
            "independent_elements": [
                "clothing, hair and aura react independently to acceleration",
                "dust, rocks and impact light travel on separate depth planes",
            ],
            "camera_independent": True,
        },
        "progression": {
            "start": f"approved moving boundary {start_label}",
            "middle": beats["middle_30_70"],
            "end": f"approved moving boundary {end_label}",
            "end_state_change": take["story_change"],
            "exit_or_cut": take["cut_motivation"],
        },
        "continuity": {
            "editorial_method": (
                "adjacent_anchor_microsegment" if take.get("internal_microsegment") else "single_continuous_take"
            ),
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "entry_motion": beats["early_0_30"],
            "exit_motion": beats["late_70_100"],
            "interval_motion": {
                "early_0_30": beats["early_0_30"],
                "middle_30_70": beats["middle_30_70"],
                "late_70_100": beats["late_70_100"],
            },
            "moving_anchor_context": {
                "start_has_motion_before_and_after": True,
                "start_source": f"owner-approved boundary {start_label} in the shared action chain",
                "end_has_motion_before_and_after": True,
                "end_source": f"owner-approved boundary {end_label} in the shared action chain",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        },
    }


def apply_contract(take: dict, start: dict, end: dict, start_label: str, end_label: str) -> None:
    take["base_image"] = copy.deepcopy(start)
    take["end_image"] = copy.deepcopy(end)
    take["base_image"]["end_frame"] = end["file"]
    take["base_image"]["end_frame_metadata"] = end.get("metadata", "")
    take["render_authorized"] = True
    take["video_generation"]["render_authorized"] = True
    take["video_generation"]["start_end_frame_enabled"] = True
    take["video_generation"]["require_approved_start_frame"] = True
    take["video_generation"]["require_approved_end_frame"] = True
    take["video_generation"]["visual_only_pass"] = True
    take["video_generation"]["native_audio_authorized"] = False
    take["is_transition"] = True
    take["shot_contract"] = {
        "subject": take["story_purpose"],
        "action": take["story_change"],
        "scene": "deep shattered rocky Cell Games arena under a storm-dark sky",
        "camera": {
            "movement": CAMERAS[take["parent_take_id"] if take.get("parent_take_id") else take["id"]],
            "angle": "physical low three-quarter action perspective with readable geography",
            "lens": "35 mm equivalent",
            "focus": "faces and contact action retained while the camera crosses real distance",
        },
        "lighting": (
            "hard cinematic sidelight, physically integrated aura and impact light, detailed live-action materials"
        ),
        "mood": "violent irreversible escalation with controlled blockbuster spectacle",
        "motion_beats": copy.deepcopy(take["motion_beats"]),
        "visual_references": {
            "start_frame_file": start["file"],
            "start_frame_approved": True,
            "end_frame_file": end["file"],
            "end_frame_approved": True,
            "end_frame_note": (
                f"Exact owner-approved boundaries {start_label}->{end_label}; both remain part of the moving handoff."
            ),
        },
        "transition_motion_contract": transition_contract(
            take, start_label=start_label, end_label=end_label
        ),
    }


def micro_take(parent: dict, micro_id: str, name: str, start: dict, end: dict,
               start_label: str, end_label: str, prompt: str,
               early: str, middle: str, late: str) -> dict:
    take = copy.deepcopy(parent)
    take.update(
        {
            "id": micro_id,
            "slug": name.lower().replace(" ", "_"),
            "name": name,
            "title": name,
            "role": "project_final_output",
            "internal_microsegment": True,
            "catalog_visible": False,
            "parent_take_id": parent["id"],
            "status": "READY_FOR_VIDEO_GENERATION",
            "maestro_status": "READY",
            "target_duration_seconds": 5.125,
            "native_duration_seconds": 5.125,
            "distinct_story_events": 2,
            "animation_prompt": prompt,
            "motion_beats": {
                "early_0_30": early,
                "middle_30_70": middle,
                "late_70_100": late,
            },
            "video": {
                "status": "pending_generation",
                "output_active": "",
                "output_preview": "",
            },
            "release_gates": {
                "art_direction": "PENDING",
                "cinematic": "PENDING",
                "motion": "PENDING",
                "technical": "PENDING",
                "human": "NOT_APPLICABLE_INTERNAL_SEGMENT",
                "video_contact_sheet": "",
            },
        }
    )
    take["video_generation"]["frames"] = 124
    take["video_generation"]["fps"] = 24
    take["video_generation"]["width"] = 1280
    take["video_generation"]["height"] = 720
    apply_contract(take, start, end, start_label, end_label)
    return take


def main() -> None:
    now = datetime.now(TZ).isoformat()
    queue = read_json(QUEUE_PATH)
    production = read_json(PRODUCTION_PATH)
    project = read_json(PROJECT_PATH)
    registry = read_json(REGISTRY_PATH)
    anchors = verify_anchors(registry)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PRODUCTION_PATH, PROJECT_PATH):
        backup = BACKUP_DIR / source.name
        if not backup.exists():
            shutil.copy2(source, backup)

    main_takes = [take for take in queue["takes"] if not take.get("internal_microsegment")]
    if [take["id"] for take in main_takes] != ["01", "02", "03", "04", "05", "06"]:
        raise RuntimeError("A fila principal precisa conter exatamente os takes 01-06.")

    endpoints = {
        "01": ("A", "C"),
        "02": ("C", "D"),
        "03": ("D", "E"),
        "04": ("E", "F"),
        "05": ("F", "H"),
        "06": ("H", "I"),
    }
    for take in main_takes:
        start_label, end_label = endpoints[take["id"]]
        apply_contract(
            take,
            anchors[start_label],
            anchors[end_label],
            start_label,
            end_label,
        )
        take["status"] = "READY_FOR_VIDEO_GENERATION"
        take["maestro_status"] = "READY"

    by_id = {take["id"]: take for take in main_takes}
    micro_takes = [
        micro_take(
            by_id["01"], "01A", "INTERNAL 01A — fala e aproximação A-B",
            anchors["A"], anchors["B"], "A", "B",
            (
                "One uninterrupted photorealistic live-action 5.125-second shot using the exact approved first and last frames. "
                "Android 16 makes only the final restrained mouth and head movement while Gohan begins a desperate physical advance. "
                "Completely tailless Perfect Cell transfers weight and places his anatomically correct boot over the purely mechanical head, ending before the stomp. "
                "The camera physically tracks low across gravel; dust, clothing and body weight never stop. Exact practical metal and skin materials. "
                "No animation, cel shading, game render, plastic CGI, green Android 16, organic Android 16 head, tail, gore, fused hand-foot anatomy, static hold or internal cut."
            ),
            "Android 16 finishes a restrained mouth movement while Gohan advances and Cell shifts weight.",
            "The low camera crosses gravel as Cell raises one anatomically correct boot and Gohan closes distance.",
            "Cell's boot reaches the approved pre-stomp placement while every subject, dust layer and camera remains moving.",
        ),
        micro_take(
            by_id["01"], "01B", "INTERNAL 01B — esmagamento e ruptura B-C",
            anchors["B"], anchors["C"], "B", "C",
            (
                "One uninterrupted photorealistic live-action 5.125-second shot using the exact approved first and last frames. "
                "Completely tailless Perfect Cell completes one brutal downward stomp with his boot centered on Android 16's purely mechanical head. "
                "Metal pieces, dust and gravel burst without blood; Gohan reacts late, shock becoming explosive rage as the arena starts breaking upward. "
                "The camera recoils physically then cranes with the rising energy and debris, ending in active motion toward transformation. "
                "No animation, cel shading, game render, plastic CGI, tail, green Android 16, organic flesh, gore, boot beside the head, fused hand-foot anatomy, repeated stomp, still pose or internal cut."
            ),
            "Cell's centered boot is already descending while Gohan and the low camera continue their approach.",
            "A single physical stomp crushes only the mechanical head and throws parts, dust and gravel through separate depth planes.",
            "Gohan's shock becomes rising rage; ground, clothing, hair, debris and crane camera accelerate into boundary C.",
        ),
        micro_take(
            by_id["05"], "05A", "INTERNAL 05A — quebra de defesa F-G",
            anchors["F"], anchors["G"], "F", "G",
            (
                "One uninterrupted photorealistic live-action 5.125-second high-speed melee shot using the exact approved first and last frames. "
                "SSJ2 Gohan intercepts completely tailless Perfect Cell's counter, breaks his guard with two different heavy contacts and launches him across the valley. "
                "Each impact changes height, screen direction and terrain damage while a physical close orbit opens into pursuit. "
                "No animation, cel shading, game render, plastic CGI, tail, duplicated limbs, fused hands, repeated punch loop, turn-taking, slow motion, static hold or internal cut."
            ),
            "Cell attempts an immediate counter while Gohan intercepts and the close camera orbits through real space.",
            "Two distinct heavy contacts break Cell's guard and shift both fighters across changing height and direction.",
            "The launch sends Cell across the valley and Gohan pursues through the approved moving boundary G.",
        ),
        micro_take(
            by_id["05"], "05B", "INTERNAL 05B — perseguição e pressão G-H",
            anchors["G"], anchors["H"], "G", "H",
            (
                "One uninterrupted photorealistic live-action 5.125-second pursuit-combat shot using the exact approved first and last frames. "
                "Completely tailless Perfect Cell is already flying across the arena; SSJ2 Gohan catches him, redirects him with two legible heavy impacts and ends pressing him at close range without stopping. "
                "Foreground rock streaks, fighters and distant terrain move at different speeds as the camera physically chases and arcs. "
                "No animation, cel shading, game render, plastic CGI, tail, duplicated bodies or limbs, repeated punch loop, pause, slow posing, static hold or internal cut."
            ),
            "Cell and the chase camera inherit high lateral velocity while Gohan closes the remaining distance.",
            "Gohan catches and redirects Cell with two distinct impacts across depth; terrain damage progresses behind them.",
            "Gohan remains physically on top of Cell in active close pressure through approved moving boundary H.",
        ),
    ]

    # The two complex main takes are assembled only from their adjacent-anchor
    # microsegments. They remain visible, but cannot accidentally launch a weaker
    # non-adjacent single pass while the overnight batch is running.
    for main_id in ("01", "05"):
        by_id[main_id]["render_authorized"] = False
        by_id[main_id]["video_generation"]["render_authorized"] = False
        by_id[main_id]["status"] = "INTERNAL_SEGMENTS_PENDING"
        by_id[main_id]["maestro_status"] = "READY"

    continuous_policy = {
        "required": True,
        "generated_connector_required_between_takes": True,
        "crossfade_forbidden": True,
        "freeze_frame_forbidden": True,
        "static_tail_forbidden": True,
        "motion_handoff_required": True,
        "full_duration_motion_required": True,
        "three_interval_motion_required": True,
        "moving_transition_anchors_required": True,
    }
    job_order = ["01A", "01B", "02", "03", "04", "05A", "05B", "06"]
    queue["takes"] = main_takes + micro_takes
    queue["render_authorized"] = True
    queue["continuous_action_contract"] = continuous_policy
    queue["status"] = "OVERNIGHT_GENERATION_AUTHORIZED"
    queue["overnight_generation"] = {
        "authorized_at": now,
        "owner_instruction": "gere todos os takes que depois avalio, nao perde tempo, depois vejo tudo",
        "job_order": job_order,
        "gpu_policy": "serial_fifo",
        "auto_approval": False,
        "main_catalog_items": ["01", "02", "03", "04", "05", "06"],
        "internal_microsegments": ["01A", "01B", "05A", "05B"],
        "assembly_before_owner_review": False,
    }
    queue["updated_at"] = now

    # The production manifest mirrors only the six public takes. Internal work
    # remains implementation detail and is removed after assembly.
    production["takes"] = copy.deepcopy(main_takes)
    production["render_authorized"] = True
    production["continuous_action_contract"] = copy.deepcopy(continuous_policy)
    production["status"] = "OVERNIGHT_GENERATION_AUTHORIZED"
    production["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    production["updated_at"] = now

    project["render_authorized"] = True
    project["status"] = "OVERNIGHT_GENERATION_AUTHORIZED"
    project["maestro_status"] = "READY"
    project["overnight_generation"] = copy.deepcopy(queue["overnight_generation"])
    project["updated_at"] = now

    write_json(QUEUE_PATH, queue)
    write_json(PRODUCTION_PATH, production)
    write_json(PROJECT_PATH, project)
    print(json.dumps({
        "ok": True,
        "anchors_verified": list(anchors),
        "main_takes": [take["id"] for take in main_takes],
        "hidden_microsegments": [take["id"] for take in micro_takes],
        "job_order": job_order,
        "backup_dir": str(BACKUP_DIR),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
