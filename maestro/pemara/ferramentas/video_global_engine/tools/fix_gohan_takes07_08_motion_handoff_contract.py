from __future__ import annotations

import json
import sys
from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ENGINE_ROOT.parents[1]
STUDIO_SERVICE = REPO_ROOT / "services" / "studio"
sys.path.insert(0, str(STUDIO_SERVICE))

from video_projects import _atomic_json_write, _queue, utc_now  # noqa: E402


PROJECT = ENGINE_ROOT / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"


INTERVALS = {
    "07": {
        "entry_motion": "Cell e Gohan atravessam os destrocos da parede ainda em velocidade.",
        "exit_motion": "Cell desliza para tras com a guarda comprimida enquanto Gohan continua avancando.",
        "early_0_30": "Cell contra-ataca durante a queda; Gohan fecha distancia e intercepta sem pausa.",
        "middle_30_70": "Joelho, bloqueio, golpe no corpo e direto curto mudam progressivamente a vantagem.",
        "late_70_100": "Gohan pressiona a guarda e Cell recua; camera, corpos, raio, poeira e pedras seguem ativos no corte.",
    },
    "08": {
        "entry_motion": "Gohan herda o avanco e Cell ainda recua com a guarda comprimida.",
        "exit_motion": "O feixe continua empurrando Cell na cratera enquanto a montanha ainda se rompe.",
        "early_0_30": "Gohan completa dois golpes distintos e a guarda de Cell cede sem reset.",
        "middle_30_70": "Um unico chute lanca Cell por distancia legivel atraves do vale; a camera persegue lateralmente.",
        "late_70_100": "Gohan dispara um Kamehameha unico que captura Cell e abre a cratera; feixe, rochas e camera seguem em velocidade.",
    },
}


def main() -> None:
    queue_path = PROJECT / "take_queue.json"
    queue = _queue(PROJECT)
    by_id = {str(item.get("id") or ""): item for item in queue.get("takes", []) if isinstance(item, dict)}
    now = utc_now()
    for take_id, evidence in INTERVALS.items():
        take = by_id[take_id]
        contract = take.setdefault("shot_contract", {}).setdefault("transition_motion_contract", {})
        continuity = contract.setdefault("continuity", {})
        continuity.update({
            "editorial_method": "generated_action_connector",
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "entry_motion": evidence["entry_motion"],
            "exit_motion": evidence["exit_motion"],
            "interval_motion": {
                "early_0_30": evidence["early_0_30"],
                "middle_30_70": evidence["middle_30_70"],
                "late_70_100": evidence["late_70_100"],
            },
            "moving_anchor_context": {
                "start_has_motion_before_and_after": True,
                "start_source": "Approved moving boundary inherited from the preceding take with explicit entry velocity.",
                "end_has_motion_before_and_after": True,
                "end_source": "Owner-approved generated boundary with explicit exit velocity into the next action or active cut.",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        })
        take["maestro_updated_at"] = now
    queue["updated_at"] = now
    _atomic_json_write(queue_path, queue)
    print(json.dumps({"ok": True, "takes": ["07", "08"], "motionHandoff": True}, indent=2))


if __name__ == "__main__":
    main()
