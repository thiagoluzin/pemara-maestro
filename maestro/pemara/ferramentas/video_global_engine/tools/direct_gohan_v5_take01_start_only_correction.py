from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
QUEUE_PATH = PROJECT / "take_queue.json"
PILOT_MANIFEST_PATH = PROJECT / "work" / "v5_sequential_pilot" / "production_manifest_v5_pilot.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    queue = read_json(QUEUE_PATH)
    take = next(item for item in queue["takes"] if str(item.get("id")) == "01")
    prompt = (
        "ONE UNINTERRUPTED 5.166667-SECOND PHOTOREALISTIC LIVE-ACTION CINEMATIC TAKE FROM THE EXACT APPROVED START FRAME. "
        "This is start-frame-only generation: do not aim for or hold any supplied final pose. Preserve one teenage ordinary Super Saiyan Gohan, one completely tailless full-size Perfect Cell, Android 16 as a purely mechanical head and the established destroyed Cell Games arena. "
        "0-30%: motion begins on frame one. A low physical camera trucks fast beside Android 16's mechanical head while Perfect Cell is already transferring body weight forward and Gohan is already taking an urgent step. Android 16 finishes only a very short final mouth movement; Cell remains silent with sealed lips. "
        "30-70%: Cell continuously raises exactly one boot while his torso, hips, armor plates and planted leg visibly carry weight. Gohan accelerates into a short run. Foreground stones cross the lens, dust travels at separate depths and the ruined arena changes perspective. No one returns to idle. "
        "70-100%: the same boot reaches its peak once and immediately begins a heavy descent. The camera physically drops and accelerates beside it; Gohan keeps running; cloth, hair, armor, stones and dust retain independent velocity. End while the boot is still descending with a clear air gap above the intact mechanical head. Cut before contact and before any motion settles. "
        "FORBIDDEN: living photo, static hold, frozen tail, early completed pose, repeated boot lift, foot reset, stomp contact, crushing, Cell dialogue or lip movement, Cell tail or rear appendage, tear effect, SSJ2 transformation, crossfade, zoom-only camera, full-frame occlusion hiding a swap, blood, gore, duplicate character, anime drawing, game render, text, logo or watermark."
    )
    take.update({
        "slug": "V5_PILOTO_01B_START_ONLY_BOTA_DESCENDENTE",
        "title": "V5 PILOTO 01B — Start-only — bota termina descendendo",
        "role": "v5_sequential_pilot_start_only_correction",
        "is_transition": False,
        "transition": {"is_transition": False, "connects_to": "02 boundary selected from real moving output"},
        "animation_prompt": prompt,
        "status": "VIDEO_PENDING_GENERATION",
        "maestro_status": "READY",
        "render_authorized": True,
        "maestro_notes": "Correção dirigida única do piloto V5. Start-frame-only; nenhuma âncora final. Selecionar uma fronteira realmente móvel do resultado antes de preparar o Take 02. Candidato 01A preservado no histórico.",
        "maestro_updated_at": now,
    })
    generation = take.setdefault("video_generation", {})
    generation.update({
        "frames": 124,
        "start_end_frame_enabled": False,
        "require_approved_start_frame": True,
        "require_approved_end_frame": False,
        "render_authorized": True,
        "prompt": prompt,
    })
    qc = take.setdefault("qc", {})
    qc.update({
        "status": "v5_pilot_01b_start_only_pending_generation",
        "human_visual_approval": "pending",
        "directed_correction_attempt": 1,
        "previous_candidate": {
            "file": "takes/maestro_generated/take_01_add8b89a84ca41c1_minimax_h3_preview.mp4",
            "status": "REJECTED_INTERNAL_QC",
            "reason": "freeze starts at 4.416667 s and the shot behaves like a living photo before the late boot lift",
        },
    })
    motion_gate = qc.setdefault("transition_motion_gate", {})
    motion_gate.update({
        "status": "pending", "evident_camera": False, "real_depth": False,
        "internal_action": False, "clear_progression": False, "continuous_action": False,
        "motion_across_all_intervals": False, "moving_anchor_context": False,
        "no_crossfade": False, "no_freeze": False, "no_static_tail": False, "no_reset": False,
        "evidence": "pending start-only generated MP4 and selected moving boundary",
    })
    contract = take.setdefault("shot_contract", {})
    contract["story_change"] = "Cell já transfere peso no primeiro quadro → uma única bota termina descendo com Gohan e câmera ainda em movimento."
    contract["cut_motivation"] = "Selecionar o melhor quadro durante a descida real e usá-lo como fronteira compartilhada do Take 02."
    contract["duration_reason"] = "O render fornece uma janela de movimento; a edição termina no melhor handoff antes de qualquer hold."
    contract["motion_beats"] = {
        "start": "Cell transfere peso, Gohan avança e a câmera já percorre o chão.",
        "middle": "Uma única bota sobe continuamente enquanto a geografia muda.",
        "end": "A mesma bota começa a descida e todos os elementos ainda carregam velocidade.",
    }
    refs = contract.setdefault("visual_references", {})
    refs["end_frame_file"] = ""
    refs["end_frame_approved"] = False
    refs["end_frame_note"] = "will be selected from the real moving output after internal QC"
    transition = contract.setdefault("transition_motion_contract", {})
    transition["progression"] = {
        "start": "Cell already transfers weight while Gohan and the low camera move.",
        "middle": "The single boot rises continuously and the camera crosses real distance.",
        "end": "The same boot begins descending while Gohan, debris and camera retain velocity.",
        "end_state_change": "Cell's grounded threat becomes one irreversible active boot descent.",
        "exit_or_cut": "select a real moving frame before contact as the shared Take 02 boundary",
    }
    continuity = transition.setdefault("continuity", {})
    continuity.update({
        "editorial_method": "single_continuous_take",
        "continuous_action": True,
        "motion_handoff": True,
        "action_occupies_full_duration": True,
        "entry_motion": "Cell weight, Gohan step, dust and physical camera truck begin on frame one.",
        "exit_motion": "Boot, Gohan, debris and camera remain in motion at the selected editorial cut.",
        "interval_motion": {
            "early_0_30": "immediate weight transfer, Gohan step and physical low truck",
            "middle_30_70": "continuous single boot lift, run acceleration and three-plane parallax",
            "late_70_100": "boot peaks once and begins descending while every layer keeps velocity",
        },
        "crossfade_frames": 0,
        "freeze_frames": 0,
        "static_hold_frames": 0,
    })
    continuity.pop("moving_anchor_context", None)

    queue["status"] = "V5_SEQUENTIAL_PILOT_TAKE01B_READY"
    queue["updated_at"] = now
    atomic_json(QUEUE_PATH, queue)

    pilot = read_json(PILOT_MANIFEST_PATH)
    pilot["updated_at"] = now
    pilot["takes"] = [take, next(item for item in queue["takes"] if str(item.get("id")) == "02")]
    pilot["route_revision"] = {
        "attempt": "01B",
        "method": "start-frame-only, then select a real moving boundary before preparing Take 02",
        "previous_attempt": "01A rejected internally for static performance and frozen tail",
    }
    atomic_json(PILOT_MANIFEST_PATH, pilot)
    print(json.dumps({
        "ok": True,
        "take": take["title"],
        "startEndFrameEnabled": generation["start_end_frame_enabled"],
        "status": take["maestro_status"],
        "take02StillBlocked": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
