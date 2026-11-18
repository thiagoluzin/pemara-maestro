from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projetos" / "vejito_super_boo_minimax_h3_8x8s"
PHYSICS_RULE = (
    "Energy beams must never pass through Goku, Vegeta, Vegetto or Super Boo. "
    "Every beam either misses with readable clearance or collides with a physical surface or energy guard; "
    "the collision point must create directional pressure, body recoil, cloth response, debris, dust and persistent damage."
)


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(name: str) -> dict:
    return json.loads((PROJECT / name).read_text(encoding="utf-8"))


def save(name: str, value: dict) -> None:
    (PROJECT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def append_rule(prompt: str) -> str:
    prompt = str(prompt or "").strip()
    if PHYSICS_RULE not in prompt:
        prompt = f"{prompt} Physics gate: {PHYSICS_RULE}"
    return prompt


def main() -> None:
    timestamp = now()
    project = load("project_manifest.json")
    production = load("production_manifest.json")
    queue = load("take_queue.json")

    project["fps_preview"] = 60
    project["fps_final"] = 60
    project["updated_at"] = timestamp
    project["review_delivery_policy"] = {
        "native_generation": "MiniMax H3 24 fps, 192 frames, 8.000 seconds",
        "human_review_delivery": "RIFE 4.6 60 fps, 480 frames, exactly 8.000 seconds",
        "interpolation_required_before_maestro_ready": True,
        "software_encoding_fallback_forbidden": True,
        "encoder": "h264_nvenc",
    }
    project["automatic_reject_rules"] = [
        "duration is not exactly 8.000 seconds",
        "review candidate is not exactly 60 fps and 480 frames",
        "an energy beam passes through a body without collision or physical response",
        "identity, hair, Potara, costume or body count changes incoherently",
    ]

    production.setdefault("global_forbidden", [])
    if PHYSICS_RULE not in production["global_forbidden"]:
        production["global_forbidden"].append(PHYSICS_RULE)
    production["updated_at"] = timestamp
    production["review_delivery_contract"] = project["review_delivery_policy"]
    prod_by_id = {str(item.get("id")): item for item in production["takes"]}
    for take in queue["takes"]:
        take_id = str(take.get("id"))
        take["animation_prompt"] = append_rule(take.get("animation_prompt", ""))
        generation = take.setdefault("video_generation", {})
        generation.update(
            {
                "fps": 24,
                "frames": 192,
                "review_fps": 60,
                "review_frames": 480,
                "review_duration_seconds": 8.0,
                "review_interpolator": "RIFE 4.6",
                "review_encoder": "h264_nvenc",
                "review_delivery_required_before_ready": True,
            }
        )
        take["maestro_notes"] = (
            "Take principal H3: gerar 8 s nativos e disponibilizar para aprovacao somente apos "
            "RIFE 4.6 em 60 fps/480 quadros. Reprovar qualquer raio que atravesse um corpo sem colisao, "
            "recuo, detritos e dano persistente."
        )
        shot = take.setdefault("shot_contract", {})
        forbidden = shot.setdefault("forbidden", [])
        if PHYSICS_RULE not in forbidden:
            forbidden.append(PHYSICS_RULE)
        prod = prod_by_id[take_id]
        prod["generation"]["prompt"] = take["animation_prompt"]
        prod["generation"]["review_fps"] = 60
        prod["generation"]["review_frames"] = 480
        prod["generation"]["review_duration_seconds"] = 8.0
        prod["generation"]["review_interpolator"] = "RIFE 4.6"
        prod["generation"]["review_encoder"] = "h264_nvenc"
        prod_forbidden = prod["shot_contract"].setdefault("forbidden", [])
        if PHYSICS_RULE not in prod_forbidden:
            prod_forbidden.append(PHYSICS_RULE)
        (PROJECT / "prompts" / f"{take_id}.md").write_text(
            f"# {take_id} - {take.get('title', take_id)}\n\n{take['animation_prompt']}\n",
            encoding="utf-8",
        )

    queue["status"] = "M01_REJECTED_PHYSICS_CORRECTION_READY_8S60"
    queue["updated_at"] = timestamp
    queue["review_delivery_policy"] = project["review_delivery_policy"]
    queue["automatic_reject_rules"] = project["automatic_reject_rules"]
    save("project_manifest.json", project)
    save("production_manifest.json", production)
    save("take_queue.json", queue)
    with (PROJECT / "FIXLOG.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n## 2026-08-15 - Correcao de duracao, fisica e 60 fps\n\n"
            "- O candidato anterior de 5,16 s foi rejeitado pelo proprietario.\n"
            "- Os takes principais exigem 8,000 s; H3 gera 192 quadros a 24 fps e RIFE 4.6 entrega 480 quadros a 60 fps.\n"
            "- Raio atravessando corpos sem colisao/resposta fisica tornou-se regra de reprovacao automatica.\n"
        )
    print(json.dumps({"project": PROJECT.name, "native": "192f/24fps/8s", "review": "480f/60fps/8s", "physics_gate": True}, indent=2))


if __name__ == "__main__":
    main()
