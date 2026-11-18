from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projetos" / "vejito_super_boo_minimax_h3_8x8s"
PHYSICS = (
    "The pink beam passes between them with obvious body clearance, strikes the rock wall behind them, "
    "and creates a directional pressure wave, cloth recoil, dust, flying fragments and a persistent crater; "
    "the beam never intersects or passes through either body."
)
M01_PROMPT = (
    "Create one continuous eight-second MiniMax H3 first/last-frame photorealistic live-action take using the exact approved boundary images. "
    "Goku and Vegeta remain two separate black-haired adult human fighters for the entire take; Super Boo remains one pink humanoid behind them. "
    "No fusion, no Vegetto, no Super Saiyan, no gold hair and no body substitution. "
    "Camera: low lateral physical dolly through foreground debris, then a short diagonal push toward the Potara without crossing the action axis. "
    "Timeline 0-25%: Goku opens his palm to reveal the two green-and-gold Potara while Vegeta refuses and Boo raises one hand. "
    f"Timeline 25-60%: Boo fires once; {PHYSICS} Goku throws exactly one earring and Vegeta catches it while both recoil naturally from the pressure wave. "
    "Timeline 60-100%: Goku and Vegeta each place one Potara on opposite ears while staying separate and black-haired; the earrings begin a faint green glow only in the final moment. "
    "End exactly in the supplied frame with both separate fighters holding the earrings at their ears and the damaged rock wall behind them. "
    "No robotic pause, repeated throw, repeated beam, pose reset, living photo, duplicate person, text, logo or static final second."
)
M02_PROMPT = (
    "Create one continuous eight-second MiniMax H3 first/last-frame photorealistic live-action take using the exact approved boundary images. "
    "Begin with separate black-haired Goku and Vegeta wearing the Potara; end with exactly one black-haired base-form Vegetto wearing both gold Potara earrings. "
    "No Super Saiyan and no gold hair anywhere in this take. Super Boo remains one pink humanoid. "
    "Timeline 0-25%: both earrings activate and pull the two fighters off balance while Boo's elastic arm misses with visible clearance. "
    "Timeline 25-65%: the bodies converge inside one white-gold energy core; limbs remain briefly readable at the boundary and never duplicate. "
    "Timeline 65-100%: base-form Vegetto emerges directly into Boo's incoming strike, blocks once and captures the same wrist while sliding over broken ground. "
    "Camera: incomplete physical orbit into the convergence, plunge through the halo, then low tracking beside the slide. "
    "Foreground debris, cloth and Boo's arm move independently; the fusion pressure leaves a permanent radial crater. "
    "No presentation pose, no second fusion, no identity swap, no extra body, no repeated strike, no reset, no text or logo."
)


def load(name: str) -> dict:
    return json.loads((PROJECT / name).read_text(encoding="utf-8"))


def save(name: str, value: dict) -> None:
    (PROJECT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    queue = load("take_queue.json")
    production = load("production_manifest.json")
    project = load("project_manifest.json")
    queue_by_id = {item["id"]: item for item in queue["takes"]}
    prod_by_id = {item["id"]: item for item in production["takes"]}
    anchor01 = str((PROJECT / "keyframes" / "anchor_01.png").resolve())

    m01 = queue_by_id["M01"]
    if isinstance(m01.get("video"), dict):
        m01.setdefault("superseded_video_candidates", []).append({
            "reason": "AUTO_REJECT_PREMATURE_SUPER_SAIYAN_BEFORE_FUSION",
            "archived_at": timestamp,
            "video": copy.deepcopy(m01["video"]),
        })
    m01["animation_prompt"] = M01_PROMPT
    m01["status"] = "PLANNED"
    m01["maestro_status"] = "PLANNED"
    m01["qc_status"] = "waiting_corrected_minimax_h3_generation"
    m01.pop("video", None)
    m01["shot_contract"]["story_change"] = (
        "Goku reveals the Potara while Vegeta refuses and Boo attacks. -> "
        "Goku and Vegeta remain separate and black-haired while placing one Potara each; the missed beam leaves a crater behind them."
    )
    m01["shot_contract"]["motion_beats"] = {
        "start": "Goku reveals both Potara; Vegeta refuses; Boo raises one hand.",
        "middle": "One beam misses both bodies, hits rock physically, and Vegeta catches the thrown earring under the pressure wave.",
        "end": "Both separate black-haired fighters place one Potara each; faint green activation begins.",
    }
    m01["shot_contract"]["reaction"] = "Vegeta commits after the physical near miss; both bodies recoil from the rock impact pressure wave."
    m01["shot_contract"]["cut_motivation"] = "Cut on the first synchronized green activation, before any attraction or fusion."
    m01["shot_contract"]["keyframes"]["end"] = "keyframes/anchor_01.png"
    m01["shot_contract"]["visual_references"].update({
        "end_frame_file": anchor01, "end_frame_approved": True,
    })
    m01["maestro_notes"] = (
        "CORRECAO M01: exatamente 8 s; somente Goku e Vegeta separados, ambos de cabelo preto, colocando os Potara. "
        "Proibidos fusao/Vegetto/SSJ. Candidato humano sera publicado apenas em RIFE60."
    )

    p01 = prod_by_id["M01"]
    p01["generation"]["end_anchor"] = "keyframes/anchor_01.png"
    p01["generation"]["prompt"] = M01_PROMPT
    p01["generation"]["status"] = "WAITING_CORRECTED_MINIMAX_H3_GENERATION"
    p01["shot_contract"] = copy.deepcopy(m01["shot_contract"])
    p01["qc"].update({"status": "WAITING_CORRECTED_MINIMAX_H3_GENERATION", "human_visual_approval": "pending"})

    m02 = queue_by_id["M02"]
    m02["animation_prompt"] = M02_PROMPT
    m02["base_image"].update({"status": "approved_for_video", "file": anchor01, "model": "approved inherited story anchor"})
    m02["shot_contract"]["story_change"] = (
        "Separate black-haired Goku and Vegeta wear activated Potara. -> "
        "One black-haired base-form Vegetto with both Potara blocks Boo and captures his wrist."
    )
    m02["shot_contract"]["motion_beats"] = {
        "start": "Separate black-haired Goku and Vegeta wear activated Potara.",
        "middle": "The attraction pulls them into one white-gold core while Boo tries to interrupt.",
        "end": "One black-haired base Vegetto emerges, blocks once and captures Boo's wrist during the slide.",
    }
    m02["shot_contract"]["reaction"] = "Boo loses his smile and then his balance when Vegetto captures the committed wrist."
    m02["shot_contract"]["keyframes"]["start"] = "keyframes/anchor_01.png"
    m02["shot_contract"]["visual_references"].update({
        "start_frame_file": anchor01, "start_frame_approved": True,
    })
    p02 = prod_by_id["M02"]
    p02["generation"]["start_anchor"] = "keyframes/anchor_01.png"
    p02["generation"]["prompt"] = M02_PROMPT
    p02["shot_contract"] = copy.deepcopy(m02["shot_contract"])

    (PROJECT / "prompts" / "M01.md").write_text(f"# M01 - Potara sob fogo\n\n{M01_PROMPT}\n", encoding="utf-8")
    (PROJECT / "prompts" / "M02.md").write_text(f"# M02 - Nascimento de Vegetto\n\n{M02_PROMPT}\n", encoding="utf-8")
    queue["status"] = "M01_CORRECTED_POTARA_ONLY_READY_FOR_GENERATION"
    queue["updated_at"] = timestamp
    production["updated_at"] = timestamp
    project["status"] = "M01_CORRECTED_POTARA_ONLY_READY_FOR_GENERATION"
    project["updated_at"] = timestamp
    project["take_review_candidates"] = []
    save("take_queue.json", queue)
    save("production_manifest.json", production)
    save("project_manifest.json", project)
    with (PROJECT / "FIXLOG.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n## 2026-08-15 - M01 remapeado apos SSJ prematuro\n\n"
            "- O M01 8s60 tecnicamente valido foi rejeitado no QC: surgiu Super Saiyan antes da fusao.\n"
            "- M01 agora usa anchor_00 -> anchor_01 e termina apenas com Goku e Vegeta pretos colocando os Potara.\n"
            "- Atracao, fusao e nascimento de Vegetto foram movidos para M02 (anchor_01 -> anchor_03).\n"
        )
    print(json.dumps({"M01": "anchor_00 -> anchor_01, Potara only", "M02": "anchor_01 -> anchor_03, fusion birth", "review": "8s/60fps required"}, indent=2))


if __name__ == "__main__":
    main()
