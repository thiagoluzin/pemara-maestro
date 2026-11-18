from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT_ID = "gohan_ssj2_take04_cells_jr_multi_anchor_v2"
PROJECT = ENGINE_ROOT / "projetos" / PROJECT_ID
QC = {
    "04C2": {
        "freeze_start_seconds": 4.625,
        "visual": "Sem rabo e sem Cell verde/adulto; primeiro Junior vira fragmentos e o segundo recebe o golpe.",
        "motion": "Camera e profundidade legiveis; excluir cauda congelada.",
    },
    "04D1": {
        "freeze_start_seconds": 4.458333,
        "visual": "Junior permanece pequeno e azul enquanto perde material; sem rabo, crescimento ou Cell verde/adulto.",
        "motion": "Progressao interna legivel, mas deslocamento de camera e discreto; exige revisao do proprietario.",
    },
    "04D2": {
        "freeze_start_seconds": 4.458333,
        "visual": "Junior desaparece em energia azul e termina somente com Gohan; nenhum Cell verde/adulto reaparece.",
        "motion": "Giro, dissolucao e mudanca de perspectiva legiveis; excluir cauda congelada.",
    },
}


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    production_path = PROJECT / "production_manifest.json"
    queue = _queue(PROJECT)
    takes = queue.get("takes")
    if not isinstance(takes, list):
        raise ValueError("Fila de takes invalida.")
    by_id = {str(take.get("id") or ""): take for take in takes if isinstance(take, dict)}
    now = utc_now()
    recorded: dict[str, dict] = {}
    for take_id, result in QC.items():
        take = by_id.get(take_id)
        if not isinstance(take, dict):
            raise ValueError(f"Take ausente: {take_id}")
        if str(take.get("maestro_status") or "").upper() != "READY":
            raise ValueError(f"{take_id} ainda nao esta READY.")
        video = take.get("video") if isinstance(take.get("video"), dict) else {}
        preview = str(video.get("output_preview") or video.get("output_active") or "")
        preview_path = Path(preview)
        if not preview_path.is_absolute():
            preview_path = PROJECT / preview_path
        if not preview_path.is_file():
            raise FileNotFoundError(f"Preview ausente de {take_id}: {preview_path}")
        take["render_authorized"] = False
        take["render_block_reason"] = "Candidato gerado; aguardando revisao visual do proprietario no Maestro."
        take["maestro_notes"] = (
            f"QC interno: {result['visual']} {result['motion']} "
            f"Freeze detectado a partir de {result['freeze_start_seconds']:.3f}s; nao usar essa cauda na montagem."
        )
        qc = take.setdefault("qc", {})
        qc.update({
            "status": "video_pending_human_review",
            "human_visual_approval": "pending",
            "internal_visual_qc": {
                "status": "candidate_passes_requested_character_fix_pending_owner",
                "checked_at": now,
                "no_green_or_adult_cell": True,
                "no_cell_junior_tail_visible_in_sampled_frames": True,
                "observation": result["visual"],
            },
            "transition_motion_gate": {
                "status": "pending_owner_full_motion_review",
                "freeze_start_seconds": result["freeze_start_seconds"],
                "editorial_rule": "hard cut before freeze; crossfade, hold and static tail forbidden",
                "observation": result["motion"],
            },
        })
        take["maestro_updated_at"] = now
        recorded[take_id] = {
            "preview": preview_path.as_posix(),
            "freeze_start_seconds": result["freeze_start_seconds"],
        }

    queue.update({
        "status": "WAITING_C2_D_CORRECTION_VIDEO_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
    })
    _atomic_json_write(queue_path, queue)

    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    production.update({
        "status": "WAITING_C2_D_CORRECTION_VIDEO_OWNER_REVIEW",
        "render_authorized": False,
        "updated_at": now,
        "active_correction_batch_qc": {
            "status": "pending_owner_review",
            "takes": recorded,
            "requested_fix": "no Cell Junior tail and no green/adult Cell substitution",
            "internal_result": "requested character defects absent in sampled frames",
        },
    })
    if isinstance(production.get("video_generation"), dict):
        production["video_generation"]["render_authorized"] = False
    _atomic_json_write(production_path, production)

    print(json.dumps({
        "ok": True,
        "projectId": PROJECT_ID,
        "status": "pending_owner_review",
        "takes": recorded,
        "renderAuthorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
