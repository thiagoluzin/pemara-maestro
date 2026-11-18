"""Reject P01 internally and authorize its single directed correction."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


BASE = Path(r"E:\Pemara\maestro\pemara")
STUDIO = BASE / "services" / "studio"
ENGINE = BASE / "ferramentas" / "video_global_engine"
PROJECTS = ENGINE / "projetos"
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = PROJECTS / PROJECT_ID
QUEUE_PATH = PROJECT / "take_queue.json"
PROJECT_MANIFEST_PATH = PROJECT / "project_manifest.json"
PILOT_MANIFEST_PATH = (
    PROJECT / "work" / "v5_action_first_pilot" / "production_manifest_v5_action_first.json"
)
QC_REPORT_PATH = PROJECT / "qc" / "v5_action_first_pilot" / "p01_attempt1_internal_rejection.json"
ARCHIVE = PROJECT / "archive" / "before_v5_p01_single_directed_correction"
TAKE_ID = "P01"

sys.path.insert(0, str(STUDIO))

from video_projects import _atomic_json_write, patch_take, utc_now  # noqa: E402


REASON = (
    "P01 reprovado no QC interno: a descida e o impacto existem no inicio, mas o "
    "video inventa uma cauda grande em Perfect Cell, a camera quase nao traduz no "
    "espaco e a metade final vira uma pose quase estatica com raios."
)

INSTRUCTION = (
    "Preservar integralmente o primeiro P01 como rollback. Fazer a unica correcao "
    "dirigida desta rota usando a mesma ancora aprovada: impacto no inicio, depois "
    "camera baixa corre fisicamente para longe de Cell seguindo a fissura, Cell sai "
    "do quadro e Gohan continua em movimento ate cortar no meio de um avanco."
)

PROMPT = (
    "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION ACTION TAKE FROM "
    "THE EXACT APPROVED START FRAME. Preserve the exact one ordinary Super Saiyan "
    "teenage Gohan, the exact one bio-android fighter shown in the reference, Android "
    "16's intact purely mechanical head, costumes, arena and storm lighting. The "
    "bio-android has a permanently clean pelvis silhouette and exactly two rigid upper-"
    "back wing plates; no other rear anatomy exists. 0-30%: continue all start-frame "
    "velocity immediately. The already-descending boot completes exactly one impact "
    "on the mechanical head within the first second. Metal, ceramic and circuits burst "
    "sideways while Gohan keeps sprinting and the low camera is physically knocked "
    "sideways. 30-70%: never hold the impact composition. The camera rapidly dollies "
    "left at ground level, follows the racing floor crack away from the bio-android and "
    "overtakes foreground fragments. The bio-android exits completely off screen right. "
    "Gohan crosses real distance toward the camera, then plants through the shockwave as "
    "the camera passes him and changes perspective by a strong sixty-degree arc. Dust, "
    "stones, clothing, hair and the floor crack retain independent velocities. 70-100%: "
    "Gohan does not pose. Gold pressure expands once, the first blue-white electrical "
    "arc travels across the arena, and Gohan immediately launches forward past the moving "
    "camera toward the off-screen opponent. Cut in the middle of that forward launch while "
    "Gohan, lightning, debris, dust and camera still carry obvious velocity. FORBIDDEN: "
    "bio-android tail, stinger, tentacle, cable or rear appendage; living photo; static "
    "hold; freeze tail; centered final pose; early completed state; boot reset; repeated "
    "stomp; tear or liquid effect; blood; gore; duplicate character; anime; game render; "
    "crossfade; zoom-only camera; text; logo; watermark."
)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    queue = read_json(QUEUE_PATH)
    take = next(
        item for item in queue.get("takes", [])
        if isinstance(item, dict) and str(item.get("id")) == TAKE_ID
    )
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    rejected_output = Path(str(video.get("output_active") or ""))
    if not rejected_output.is_file() or not rejected_output.resolve().is_relative_to(PROJECT.resolve()):
        raise FileNotFoundError("P01 gerado nao foi encontrado dentro do projeto.")
    rejected_hash = sha256(rejected_output)

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for source in (QUEUE_PATH, PROJECT_MANIFEST_PATH, PILOT_MANIFEST_PATH):
        target = ARCHIVE / source.name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)

    latest_requests = take.get("maestro_director_requests")
    latest = (
        latest_requests[-1]
        if isinstance(latest_requests, list)
        and latest_requests
        and isinstance(latest_requests[-1], dict)
        else {}
    )
    if not (
        str(take.get("maestro_status") or "").upper() == "REJECTED"
        and str(latest.get("reason") or "") == REASON
    ):
        patch_take(
            PROJECTS,
            PROJECT_ID,
            TAKE_ID,
            {
                "status": "REJECTED",
                "notes": (
                    "Primeiro P01 reprovado no QC interno por cauda, camera quase "
                    "estatica e final em pose. Arquivo preservado; correcao unica dirigida."
                ),
                "directorRequest": {
                    "category": "PROGRESSION",
                    "reason": REASON,
                    "renderInstruction": INSTRUCTION,
                },
            },
        )

    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == TAKE_ID)
    video = take.get("video") if isinstance(take.get("video"), dict) else {}
    video["candidate_status"] = "REJECTED_INTERNAL_QC_PRESERVED"
    video["internal_rejection"] = {
        "output": str(rejected_output.resolve()),
        "sha256": rejected_hash,
        "reason": REASON,
        "contact_sheet": "qc/v5_action_first_pilot/p01_contact_2fps.jpg",
        "tail_sheet": "qc/v5_action_first_pilot/p01_tail_frames100_123.jpg",
        "freeze_detect_0_35s": "no literal freeze event; visual near-static tail still failed",
    }
    take["video"] = video
    take["animation_prompt"] = PROMPT
    take["status"] = "VIDEO_PENDING_GENERATION"
    take["maestro_status"] = "READY"
    take["render_authorized"] = True
    take["role"] = "v5_action_first_pilot_single_directed_correction"
    take["maestro_notes"] = (
        "Correcao dirigida unica do P01. O primeiro MP4 permanece preservado. "
        "Se esta tentativa falhar, encerrar prompt-only H3 e mudar o controle/rota."
    )
    generation = take.get("video_generation") if isinstance(take.get("video_generation"), dict) else {}
    generation.update({
        "prompt": PROMPT,
        "render_authorized": True,
        "start_end_frame_enabled": False,
        "require_approved_start_frame": True,
        "require_approved_end_frame": False,
        "fps": 24,
        "frames": 124,
        "steps": 20,
        "guidance": 1.0,
        "visual_only_pass": True,
        "native_audio_authorized": False,
    })
    take["video_generation"] = generation
    shot = take.get("shot_contract") if isinstance(take.get("shot_contract"), dict) else {}
    shot["story_change"] = (
        "Downstroke ativo vira impacto mecanico; a camera abandona Cell, segue a "
        "fissura e termina com Gohan lancando-se para frente."
    )
    shot["reaction"] = (
        "Gohan atravessa a onda de choque, planta por um instante funcional e volta a avancar."
    )
    shot["cut_motivation"] = "Cortar no meio do avanco de Gohan, nunca numa pose concluida."
    shot["motion_beats"] = {
        "start": "Impacto mecanico unico no primeiro segundo com camera expulsa lateralmente.",
        "middle": "Camera corre pela fissura; Cell sai do quadro e Gohan cruza distancia real.",
        "end": "Primeiro arco aparece e Gohan dispara para frente passando pela camera movel.",
    }
    transition = shot.get("transition_motion_contract") if isinstance(shot.get("transition_motion_contract"), dict) else {}
    transition["camera_evidence"] = {
        "movement": "Impact knocks the low camera left; it races along the crack, passes Gohan and arcs sixty degrees.",
        "physical_translation": True,
        "perspective_change": "Foreground fragments, Gohan and ruined walls reorder and change scale continuously.",
    }
    transition["real_depth"] = {
        "foreground": "mechanical fragments, stones and crack overtake the lens",
        "midground": "Gohan crosses distance and the bio-android exits frame right",
        "background": "arena walls and clouds shift slowest during the lateral chase",
        "differential_motion": "fragments fastest, Gohan medium, distant ruins slowest",
        "occlusion_or_scale_change": "camera passes debris and Gohan with strong overlap changes",
    }
    transition["internal_action"] = {
        "primary_event": "One impact becomes one ground chase and one renewed Gohan launch.",
        "independent_elements": [
            "Gohan body, hair and clothing cross the camera path",
            "fragments, dust, floor crack and lightning retain separate vectors",
        ],
        "camera_independent": True,
    }
    transition["progression"] = {
        "start": "active downstroke completes one impact",
        "middle": "impact propagates into crack chase while Cell exits",
        "end": "Gohan converts anger into a renewed forward launch",
        "end_state_change": "mechanical head becomes debris and stationary pursuit becomes renewed attack",
        "exit_or_cut": "mid-launch directional handoff",
    }
    continuity = transition.get("continuity") if isinstance(transition.get("continuity"), dict) else {}
    continuity.update({
        "editorial_method": "single_continuous_take",
        "continuous_action": True,
        "motion_handoff": True,
        "action_occupies_full_duration": True,
        "entry_motion": "downstroke, sprint, debris and low camera continue on frame one",
        "exit_motion": "Gohan, lightning, debris and camera retain forward/lateral velocity",
        "interval_motion": {
            "early_0_30": "impact and lateral camera displacement",
            "middle_30_70": "ground-level crack chase away from Cell and past Gohan",
            "late_70_100": "first lightning and Gohan launch through the moving camera path",
        },
        "crossfade_frames": 0,
        "freeze_frames": 0,
        "static_hold_frames": 0,
    })
    transition["continuity"] = continuity
    shot["transition_motion_contract"] = transition
    take["shot_contract"] = shot
    direction = take.get("direction_contract") if isinstance(take.get("direction_contract"), dict) else {}
    direction.update({
        "story_change": shot["story_change"],
        "reaction": shot["reaction"],
        "cut_motivation": shot["cut_motivation"],
        "beats": [
            {"start": 0.0, "end": 1.55, "action": "Impacto unico e camera expulsa lateralmente."},
            {"start": 1.55, "end": 3.62, "action": "Camera persegue a fissura enquanto Cell sai e Gohan cruza distancia."},
            {"start": 3.62, "end": 5.166667, "action": "Primeiro arco e avanco de Gohan atraves do corte."},
        ],
        "direction_status": "approved_for_video",
    })
    take["direction_contract"] = direction
    qc = take.get("qc") if isinstance(take.get("qc"), dict) else {}
    qc["status"] = "single_directed_correction_authorized_pending_generation"
    qc["human_visual_approval"] = "pending_video_review"
    qc["previous_candidate"] = video["internal_rejection"]
    gate = qc.get("transition_motion_gate") if isinstance(qc.get("transition_motion_gate"), dict) else {}
    gate.update({
        "status": "contract_pass_pending_corrected_video_qc",
        "evident_camera": False,
        "real_depth": False,
        "internal_action": False,
        "clear_progression": False,
        "continuous_action": False,
        "motion_across_all_intervals": False,
        "no_crossfade": True,
        "no_freeze": False,
        "no_static_tail": False,
        "no_reset": False,
        "evidence": "pending corrected generated MP4",
    })
    qc["transition_motion_gate"] = gate
    take["qc"] = qc
    take["directed_correction"] = {
        "attempt": 1,
        "reason": REASON,
        "method": "same approved action anchor; rewritten spatial route and off-screen Cell",
        "previous_output": str(rejected_output.resolve()),
        "previous_sha256": rejected_hash,
        "further_prompt_only_attempt_authorized": False,
    }
    take["maestro_updated_at"] = utc_now()
    queue["status"] = "V5_ACTION_FIRST_P01_SINGLE_CORRECTION_READY"
    queue["updated_at"] = utc_now()
    _atomic_json_write(QUEUE_PATH, queue)

    manifest = read_json(PROJECT_MANIFEST_PATH)
    manifest["status"] = "V5_ACTION_FIRST_P01_SINGLE_CORRECTION_IN_PRODUCTION"
    manifest["directed_correction_v5_action_first"]["attempt"] = 1
    manifest["directed_correction_v5_action_first"]["previous_output"] = str(rejected_output.resolve())
    manifest["directed_correction_v5_action_first"]["previous_sha256"] = rejected_hash
    manifest["updated_at"] = utc_now()
    _atomic_json_write(PROJECT_MANIFEST_PATH, manifest)

    pilot_manifest = read_json(PILOT_MANIFEST_PATH)
    pilot_manifest["takes"] = [take]
    pilot_manifest["route_revision"] = {
        "attempt": "P01C1",
        "previous": "P01 attempt 1 rejected internally for Cell tail, weak camera and near-static second half",
        "prompt_only_attempts_remaining_after_this": 0,
    }
    pilot_manifest["updated_at"] = utc_now()
    _atomic_json_write(PILOT_MANIFEST_PATH, pilot_manifest)

    report = {
        "take_id": TAKE_ID,
        "status": "REJECTED_INTERNAL_QC_PRESERVED",
        "output": str(rejected_output.resolve()),
        "sha256": rejected_hash.upper(),
        "ffprobe": {"width": 1280, "height": 720, "fps": 24, "frames": 124, "duration_seconds": 5.166667},
        "freeze_detect": {"threshold_seconds": 0.35, "literal_event": False},
        "visual_failures": [
            "large Cell tail/rear appendage appears in the second half",
            "camera does not show strong physical translation",
            "late interval becomes a near-static lightning pose",
            "clear progression and useful full-duration motion fail",
        ],
        "preserved": True,
        "directed_correction": "P01C1 authorized",
    }
    _atomic_json_write(QC_REPORT_PATH, report)
    print(json.dumps({
        "ok": True,
        "rejectedOutput": str(rejected_output.resolve()),
        "sha256": rejected_hash.upper(),
        "correction": "P01C1",
        "status": take["maestro_status"],
        "furtherPromptOnlyAttemptsAfterThis": 0,
        "qcReport": str(QC_REPORT_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
