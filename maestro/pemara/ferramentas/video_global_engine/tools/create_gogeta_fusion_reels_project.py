#!/usr/bin/env python3
"""Register the owner-approved Gogeta fusion-dance anchors in Maestro.

This script is deliberately registration-only. It creates no ComfyUI job and
does not authorize GPU rendering or audio generation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


ENGINE_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ENGINE_ROOT / "projetos"
PROJECT_ID = "gogeta_fusao_danca_reels_vertical_15s"
PROJECT = PROJECTS_ROOT / PROJECT_ID
SOURCE = Path(
    r"E:\Pemara\maestro\pemara\saida\reels_fusao_goku_vegeta\anchors"
)

ANCHORS = (
    {
        "id": "anchor_01",
        "source": "anchor_01_danca.png",
        "title": "Danca da fusao em aproximacao",
        "visible_characters": ["Goku", "Vegeta"],
        "prompt": (
            "Goku e Vegeta em live action cinematografico executam a Danca da "
            "Fusao, de corpo inteiro, ainda antes do contato dos dedos, na cratera "
            "noturna com energia laranja e azul."
        ),
    },
    {
        "id": "anchor_02",
        "source": "anchor_02_contato_fusao.png",
        "title": "Contato dos dedos e ignicao",
        "visible_characters": ["Goku", "Vegeta"],
        "prompt": (
            "Goku e Vegeta completam a pose tradicional da Danca da Fusao; um "
            "unico par de indicadores toca o centro e inicia uma estrela branco-dourada."
        ),
    },
    {
        "id": "anchor_03",
        "source": "anchor_03_gogeta_base.png",
        "title": "Gogeta nasce em forma base",
        "visible_characters": ["Gogeta"],
        "prompt": (
            "Gogeta live action em forma base, cabelo preto e traje Metamoran, "
            "pousa em tres apoios na mesma cratera depois da fusao."
        ),
    },
    {
        "id": "anchor_04",
        "source": "anchor_04_gogeta_super_saiyajin.png",
        "title": "Gogeta Super Saiyajin tradicional",
        "visible_characters": ["Gogeta"],
        "prompt": (
            "O mesmo Gogeta conclui a transformacao em Super Saiyajin tradicional, "
            "com cabelo dourado, olhos azul-esverdeados, aura colossal e dano persistente."
        ),
    },
)

GLOBAL_NEGATIVE = [
    "no crossfade",
    "no freeze frame",
    "no static tail",
    "no living photo",
    "no simple zoom only",
    "no face morphing",
    "no body melting",
    "no costume morphing",
    "no duplicate character",
    "no extra limbs or fingers",
    "no identity drift",
    "no environment reset",
    "no generated text",
    "no watermark",
    "no native audio",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def replace_tree_path(value: object, old: str, new: str) -> object:
    """Replace one canonical path inside every string of a JSON-compatible tree."""

    if isinstance(value, dict):
        return {key: replace_tree_path(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_tree_path(item, old, new) for item in value]
    if isinstance(value, str):
        return value.replace(old, new)
    return value


def normalize_anchor(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        normalized = ImageOps.fit(
            rgb,
            (720, 1280),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        normalized.save(destination, format="PNG", optimize=True)
    with Image.open(destination) as check:
        check.load()
        if check.size != (720, 1280) or check.mode != "RGB":
            raise RuntimeError(f"Ancora normalizada invalida: {destination}")


def anchor_sidecar(
    *,
    anchor: dict[str, object],
    original_path: Path,
    normalized_path: Path,
    approved_at: str,
    final_project: Path,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "type": "approved_story_anchor_metadata",
        "anchor_id": anchor["id"],
        "title": anchor["title"],
        "created_at": approved_at,
        "approved_at": approved_at,
        "approval_source": "owner_message_in_codex",
        "approval_evidence": "Imagens aprovado jogar os takes no maestro",
        "original_file": str(
            (final_project / "refs" / "approved_originals" / original_path.name).resolve()
        ),
        "original_sha256": sha256(original_path),
        "image_file": str((final_project / "keyframes" / normalized_path.name).resolve()),
        "image_sha256": sha256(normalized_path),
        "copy_integrity": "source_preserved_and_normalized_copy_hashed",
        "normalization": {
            "source_width": 941,
            "source_height": 1672,
            "output_width": 720,
            "output_height": 1280,
            "method": "Pillow ImageOps.fit Lanczos center crop-resample",
            "reason": "Maestro requires mathematically exact 9:16 anchors",
        },
        "width": 720,
        "height": 1280,
        "mode": "RGB",
        "model": "OpenAI built-in image generation",
        "generator": "Codex built-in imagegen",
        "workflow": "owner-approved anchor import into Maestro",
        "prompt": anchor["prompt"],
        "negative": ", ".join(GLOBAL_NEGATIVE),
        "visible_characters": anchor["visible_characters"],
        "validation_status": "approved_for_video",
        "approval_required_before_video": False,
        "human_review": {
            "decision": "APPROVED",
            "source": "owner_message_in_codex",
            "explicit_human_confirmation": True,
        },
        "visual_qc": {
            "status": "APPROVED",
            "opened_at_original_resolution": True,
            "vertical_composition": True,
            "identity_continuity": True,
            "anatomy_readable": True,
            "actual_visible_characters": anchor["visible_characters"],
        },
    }


def motion_contract(
    *,
    camera: str,
    perspective: str,
    foreground: str,
    midground: str,
    background: str,
    differential: str,
    overlap: str,
    event: str,
    elements: list[str],
    start: str,
    middle: str,
    end: str,
    changed: str,
    exit_or_cut: str,
    entry_motion: str,
    exit_motion: str,
    early: str,
    middle_motion: str,
    late: str,
) -> dict[str, object]:
    return {
        "camera_evidence": {
            "movement": camera,
            "physical_translation": True,
            "perspective_change": perspective,
        },
        "real_depth": {
            "foreground": foreground,
            "midground": midground,
            "background": background,
            "differential_motion": differential,
            "occlusion_or_scale_change": overlap,
        },
        "internal_action": {
            "primary_event": event,
            "independent_elements": elements,
            "camera_independent": True,
        },
        "progression": {
            "start": start,
            "middle": middle,
            "end": end,
            "end_state_change": changed,
            "exit_or_cut": exit_or_cut,
        },
        "continuity": {
            "editorial_method": "single_continuous_take",
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "entry_motion": entry_motion,
            "exit_motion": exit_motion,
            "interval_motion": {
                "early_0_30": early,
                "middle_30_70": middle_motion,
                "late_70_100": late,
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        },
    }


def take_definitions(final_project: Path) -> list[dict[str, object]]:
    keyframe = lambda number: str(
        (final_project / "keyframes" / f"anchor_{number:02d}.png").resolve()
    )
    metadata = lambda number: str(
        (final_project / "keyframes" / f"anchor_{number:02d}.json").resolve()
    )

    common_generation = {
        "profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
        "width": 720,
        "height": 1280,
        "fps": 24,
        "frames": 124,
        "steps": 20,
        "guidance": 1.0,
        "start_end_frame_enabled": True,
        "require_approved_end_frame": True,
        "maestro_job_enabled": True,
        "visual_only_pass": True,
        "native_audio_authorized": False,
        "review_fps": 60,
        "review_duration_seconds": 5.0,
        "review_interpolator": "RIFE 4.6",
        "review_encoder": "h264_nvenc",
        "review_delivery_required_before_ready": True,
    }

    specs = [
        {
            "id": "T01",
            "slug": "danca_ate_contato",
            "title": "Danca da fusao ate o contato",
            "objective": "Executar a coreografia legivel e terminar no contato exato dos dedos.",
            "start_anchor": 1,
            "end_anchor": 2,
            "characters": ["Goku", "Vegeta"],
            "animation_prompt": (
                "Create one continuous five-second MiniMax H3 first/last-frame vertical "
                "9:16 ultra-photorealistic live-action take using the exact approved anchors. "
                "Preserve the same human Goku and Vegeta, faces, black hair, costumes, body "
                "proportions, crater, moon and orange-blue palette. Camera performs a physical "
                "low semicircular dolly with real foreground-to-background parallax. Timeline "
                "0-30%: both fighters continue the synchronized Fusion Dance with grounded footwork, "
                "cloth recoil and dust moving under each step. Timeline 30-70%: arms sweep through "
                "the mirrored choreography while energy ribbons accelerate toward center and rocks "
                "orbit at separate depths. Timeline 70-100%: their outer legs rise and exactly one "
                "pair of index fingertips meets at center; a compact white-gold ignition is born "
                "without hiding hands, faces or anatomy. End in the supplied contact frame while "
                "camera, dust, cloth and energy remain in motion. No pause, no repeated step, no "
                "face morph, no body merge, no Gogeta, no gold hair, no crossfade or static tail."
            ),
            "story_purpose": "Transformar rivalidade em sincronizacao fisica perfeita.",
            "dramatic_question": "Eles conseguirao sincronizar o gesto final sem perder a forma?",
            "story_change": "Dois lutadores separados em movimento terminam no primeiro contato energetico.",
            "motion_beats": {
                "start": "A coreografia continua com passos espelhados e camera em arco.",
                "middle": "Bracos convergem enquanto energia e detritos aceleram em profundidade.",
                "end": "Um unico par de indicadores toca o centro e inicia a fusao.",
            },
            "reaction": "Ambos sustentam concentracao e os corpos absorvem a pressao crescente.",
            "cut_motivation": "Entregar o contato ainda em expansao para o take da fusao.",
            "duration_reason": "Cinco segundos acomodam coreografia, convergencia e ignicao sem repeticao.",
            "distinct_story_events": 3,
            "contract": motion_contract(
                camera="Low physical semicircular dolly moving left-to-right around both fighters.",
                perspective="Foreground rocks cross the fighters while their overlap and crater horizon change visibly.",
                foreground="Loose rocks and dust cross close to the lens in the lower vertical frame.",
                midground="Goku and Vegeta perform the mirrored full-body Fusion Dance.",
                background="Moonlit crater walls and distant mountains shift more slowly behind them.",
                differential="Foreground debris moves fastest, both fighters move at medium rate, mountains move slowest.",
                overlap="The camera arc changes which arm overlaps the energy center before the fingertips meet.",
                event="The synchronized dance resolves into one precise fingertip contact and energy ignition.",
                elements=["Both bodies execute independent grounded choreography and cloth recoil.", "Rocks orbit while dust expands independently from the camera."],
                start="Goku and Vegeta approach the final mirrored dance position.",
                middle="Their arms and outer legs align while orange and blue energy converges.",
                end="The fingertips touch and a white-gold fusion nucleus begins to expand.",
                changed="Physical contact and a new fusion-energy nucleus now exist at center.",
                exit_or_cut="Hard cut on the expanding nucleus into T02 with the same outward energy velocity.",
                entry_motion="Bodies, clothing, dust and camera already move into the last dance phrase.",
                exit_motion="The nucleus, rocks, clothing and dolly continue accelerating into the fusion take.",
                early="Feet cross and plant while camera arcs and foreground rubble sweeps laterally.",
                middle_motion="Arms converge, outer legs rise and energy ribbons tighten around the center.",
                late="Fingertips connect and the nucleus expands while every visible layer remains moving.",
            ),
        },
        {
            "id": "T02",
            "slug": "fusao_ate_gogeta_base",
            "title": "Fusao fisica e nascimento de Gogeta",
            "objective": "Fundir duas silhuetas por causa e consequencia e revelar Gogeta base sem morph grotesco.",
            "start_anchor": 2,
            "end_anchor": 3,
            "characters": ["Goku", "Vegeta", "Gogeta"],
            "animation_prompt": (
                "Create one continuous five-second MiniMax H3 first/last-frame vertical 9:16 "
                "ultra-photorealistic live-action fusion event using the exact approved anchors. "
                "This is a physical cause-and-consequence transformation, never a face dissolve or "
                "melting morph. Preserve the crater, moon, costume materials and orange-blue-white "
                "lighting. Camera trucks diagonally through real foreground debris and then cranes "
                "slightly down toward the landing point. Timeline 0-30%: the fingertip nucleus expands "
                "and pulls the two still-readable separate silhouettes toward the central axis; cloth, "
                "hair, rocks and dust inherit their prior velocities. Timeline 30-70%: the two silhouettes "
                "rotate once around the white-gold core and converge into exactly one stable humanoid "
                "silhouette; do not show blended faces, extra limbs or liquid bodies. Timeline 70-100%: "
                "the light column contracts and one black-haired base-form Gogeta drops out, lands in "
                "three-point stance and creates new persistent radial cracks. End in the supplied Gogeta "
                "base frame while dust, sash, rocks and camera keep moving. No gold hair, no Super Saiyan, "
                "no body duplication, no flash-only substitution, no crossfade and no static tail."
            ),
            "story_purpose": "Mostrar a fusao como evento fisico continuo e revelar a nova identidade.",
            "dramatic_question": "A energia formara um unico guerreiro estavel?",
            "story_change": "Dois corpos separados convergem e terminam como um Gogeta base em pouso.",
            "motion_beats": {
                "start": "O nucleo nasce no contato e puxa as duas silhuetas.",
                "middle": "As silhuetas orbitam e convergem em uma unica forma legivel.",
                "end": "Gogeta base sai da coluna e fratura o solo ao pousar.",
            },
            "reaction": "O ambiente responde com pressao, poeira, rochas e rachadura persistente.",
            "cut_motivation": "Cortar quando Gogeta estabiliza o pouso e inicia o levantamento.",
            "duration_reason": "Cinco segundos separam atracao, convergencia e pouso sem usar morph ou clarão vazio.",
            "distinct_story_events": 3,
            "contract": motion_contract(
                camera="Diagonal physical truck through debris followed by a short downward crane toward the landing point.",
                perspective="The fusion core passes behind foreground rocks and grows relative to the crater before Gogeta lands nearer camera.",
                foreground="Fast fragments and a dust wave cross the lens without hiding the central silhouettes.",
                midground="Two silhouettes converge into one stable Gogeta silhouette and descend.",
                background="Crater walls, moon and mountains remain continuous while the energy column splits clouds.",
                differential="Close fragments move rapidly, the fusion core and body move moderately, distant terrain shifts slowly.",
                overlap="Foreground debris briefly overlaps the energy rim while the central anatomy remains visible and scale changes coherently.",
                event="Two separate bodies are pulled into a fusion core and one base-form Gogeta lands with physical impact.",
                elements=["Two silhouettes orbit and converge under the energy pull.", "Dust, rocks and the blue sash continue with separate inertia."],
                start="The fingertip nucleus expands around two separate fighters.",
                middle="Two readable silhouettes converge around a white-gold axis without facial blending.",
                end="One black-haired Gogeta lands and leaves new radial cracks in the crater.",
                changed="The body count changes irreversibly from two fighters to one stable fused fighter and the ground is newly fractured.",
                exit_or_cut="Hard cut on Gogeta beginning to rise, handing upward body and debris velocity into T03.",
                entry_motion="The expanding nucleus, dolly, bodies and debris inherit outward and inward velocities from T01.",
                exit_motion="Gogeta rises from impact while dust, sash and rocks continue upward into the power-up take.",
                early="The core pulls both bodies inward while the camera trucks and debris crosses depth planes.",
                middle_motion="Silhouettes orbit once, converge and stabilize as the energy column contracts.",
                late="Gogeta descends, strikes the ground and begins rising while damage and debris keep progressing.",
            ),
        },
        {
            "id": "T03",
            "slug": "gogeta_base_ate_super_saiyajin",
            "title": "Gogeta base ate Super Saiyajin",
            "objective": "Dar leitura suficiente da forma base e executar a transformacao tradicional sem deformar identidade ou roupa.",
            "start_anchor": 3,
            "end_anchor": 4,
            "characters": ["Gogeta"],
            "animation_prompt": (
                "Create one continuous five-second MiniMax H3 first/last-frame vertical 9:16 "
                "ultra-photorealistic live-action transformation using the exact approved anchors. "
                "Preserve the same single Gogeta face, body proportions, Metamoran vest, white pants, "
                "blue sash, boots, crater and moon. Camera begins with a low physical orbit as Gogeta "
                "rises, then cranes and dollies backward under the shockwave; never use a digital zoom. "
                "Timeline 0-30%: Gogeta remains unmistakably base form with black hair while standing "
                "from the crouch; dust, sash and rocks continue from the landing. Timeline 30-70%: golden "
                "energy ignites from the feet upward, new cracks spread, hair volume stiffens lock by lock "
                "and changes black to bronze-lit to gold without changing skull, face or costume. Timeline "
                "70-100%: teal eyes lock, blue-white lightning branches, the golden aura expands through "
                "all depth planes and the camera retreats with the pressure wave. End in the supplied "
                "traditional Super Saiyan frame while aura, lightning, rocks, clothing and camera remain "
                "active. Exactly one Gogeta throughout. No face replacement, liquid hair, extra person, "
                "costume change, crossfade, freeze, static pose or environment reset."
            ),
            "story_purpose": "Entregar o payoff de poder preservando identidade e leitura da forma base.",
            "dramatic_question": "Gogeta conseguira elevar o poder sem perder controle ou identidade?",
            "story_change": "Gogeta base de cabelo preto termina como Super Saiyajin dourado com dano ambiental ampliado.",
            "motion_beats": {
                "start": "Gogeta base levanta-se com cabelo preto e o impacto ainda ativo.",
                "middle": "Energia sobe, solo racha e cabelo muda progressivamente sem deformar o rosto.",
                "end": "Aura dourada, olhos azul-esverdeados e raios completam a transformacao.",
            },
            "reaction": "O corpo sustenta a pressao e o ambiente e projetado para fora em multiplas profundidades.",
            "cut_motivation": "Encerrar no pico da onda de choque com aura ainda preenchendo a tela.",
            "duration_reason": "Cinco segundos preservam a forma base, mostram progressao fisica e entregam o payoff sem pose morta.",
            "distinct_story_events": 3,
            "contract": motion_contract(
                camera="Low physical orbit transitioning into a backward dolly and short crane under the pressure wave.",
                perspective="Gogeta rises relative to foreground boulders while the camera retreat reveals widening crater damage.",
                foreground="Boulders, dust and sparks accelerate toward and past the lens.",
                midground="One Gogeta rises, braces and transforms without changing costume or facial identity.",
                background="Crater walls, mountains and storm clouds split progressively behind the golden column.",
                differential="Foreground rocks move fastest, Gogeta and aura expand at medium rate, distant clouds separate slowly.",
                overlap="The retreating camera reveals more radial cracks while aura layers wrap behind and in front of the stable silhouette.",
                event="One base-form Gogeta powers up progressively into traditional Super Saiyan and permanently damages the crater.",
                elements=["Gogeta rises and clenches both fists while his sash and clothing whip.", "Rocks lift, cracks spread and clouds divide independently from the camera."],
                start="Black-haired base-form Gogeta begins rising from the landing crouch.",
                middle="Energy climbs from feet to hair while cracks and levitating rocks escalate.",
                end="Golden-haired Super Saiyan Gogeta holds the power peak inside an expanding shockwave.",
                changed="Hair and eyes are transformed, aura is fully active and crater damage has expanded irreversibly.",
                exit_or_cut="Hard cut at the pressure-wave peak while aura and debris are still moving outward.",
                entry_motion="Gogeta, sash, dust, rocks and camera inherit upward motion from the landing in T02.",
                exit_motion="Aura, lightning, rocks and camera continue outward at the final Reels cut.",
                early="Gogeta rises in base form while camera orbits and residual landing debris climbs.",
                middle_motion="Golden energy travels upward, hair stiffens progressively and radial cracks spread.",
                late="Eyes lock teal, lightning branches and the shockwave drives camera and debris outward.",
            ),
        },
    ]

    takes: list[dict[str, object]] = []
    for index, spec in enumerate(specs):
        start_number = int(spec["start_anchor"])
        end_number = int(spec["end_anchor"])
        start_file = keyframe(start_number)
        end_file = keyframe(end_number)
        take = {
            "id": spec["id"],
            "slug": spec["slug"],
            "title": spec["title"],
            "objective": spec["objective"],
            "characters": spec["characters"],
            "status": "PLANNED",
            "maestro_status": "PLANNED",
            "timeline_start_seconds": index * 5.0,
            "target_duration_seconds": 5.0,
            "animation_prompt": spec["animation_prompt"],
            "render_authorized": False,
            "video_generation": dict(common_generation),
            "shot_contract": {
                "story_purpose": spec["story_purpose"],
                "dramatic_question": spec["dramatic_question"],
                "story_change": spec["story_change"],
                "motion_beats": spec["motion_beats"],
                "reaction": spec["reaction"],
                "cut_motivation": spec["cut_motivation"],
                "duration_reason": spec["duration_reason"],
                "distinct_story_events": spec["distinct_story_events"],
                "camera": {
                    "movement": spec["contract"]["camera_evidence"]["movement"],
                    "physical_translation": True,
                    "lens": "35 mm live-action vertical framing",
                    "focus": "full-body identity lock with readable hands and layered depth",
                },
                "keyframes": {
                    "start": f"keyframes/anchor_{start_number:02d}.png",
                    "end": f"keyframes/anchor_{end_number:02d}.png",
                    "approved": True,
                    "approval_source": "explicit owner approval in Codex",
                },
                "visual_references": {
                    "start_frame_file": start_file,
                    "start_frame_approved": True,
                    "end_frame_file": end_file,
                    "end_frame_approved": True,
                    "shared_boundary_contract": "approved end anchor is reused as the next take start anchor",
                },
                "variants": {"duration_seconds": 5.0},
                "negative_rules": GLOBAL_NEGATIVE,
                "transition_motion_contract": spec["contract"],
            },
            "transition": {"is_transition": False},
            "base_image": {
                "status": "approved_for_video",
                "file": start_file,
                "metadata": metadata(start_number),
                "model": "OpenAI built-in image generation",
                "image_sha256": sha256(final_project / "keyframes" / f"anchor_{start_number:02d}.png"),
                "approved_at": now_iso(),
                "approval_source": "owner_message_in_codex",
                "prompt": next(a["prompt"] for a in ANCHORS if a["id"] == f"anchor_{start_number:02d}"),
            },
            "qc": {
                "status": "anchors_approved_video_not_generated",
                "human_anchor_approval": "approved_by_owner",
                "human_visual_approval": "pending_generated_video_playback",
                "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK_AND_OWNER_DIRECTIVE",
                "transition_motion_gate": {
                    "status": "pending_video_generation",
                    "evident_camera": False,
                    "real_depth": False,
                    "internal_action": False,
                    "clear_progression": False,
                    "continuous_action": False,
                    "motion_across_all_intervals": False,
                    "moving_anchor_context": False,
                    "no_crossfade": True,
                    "no_freeze": True,
                    "no_static_tail": True,
                    "no_reset": False,
                    "evidence": "Awaiting generated MP4 and human visual inspection.",
                },
            },
            "audio_direction": {
                "delivery_required": False,
                "strategy": "visual_only_until_explicit_owner_directive",
                "status": "blocked_until_picture_lock_and_owner_directive",
                "native_audio_authorized": False,
                "human_listening_required": False,
            },
            "video": {"status": "planned"},
        }
        if spec["id"] == "T01":
            take["shot_contract"]["human_visibility_contract"] = {
                "allowed_humans": ["Goku", "Vegeta"],
                "allowed_non_humans": [],
                "exact_human_count": 2,
            }
        elif spec["id"] == "T03":
            take["shot_contract"]["human_visibility_contract"] = {
                "allowed_humans": ["Gogeta"],
                "allowed_non_humans": [],
                "exact_human_count": 1,
            }
        takes.append(take)
    return takes


def main() -> int:
    if PROJECT.exists():
        raise SystemExit(f"Projeto ja existe; nenhuma sobrescrita foi feita: {PROJECT}")
    required = [SOURCE / str(anchor["source"]) for anchor in ANCHORS]
    required.extend([SOURCE / "qc_contact_sheet.png", SOURCE / "PROMPTS.md"])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Arquivos fonte ausentes: " + ", ".join(missing))

    staging = PROJECTS_ROOT / f".{PROJECT_ID}.staging.{uuid.uuid4().hex[:8]}"
    if staging.exists():
        raise SystemExit(f"Staging inesperadamente existente: {staging}")
    for directory in (
        "input",
        "refs/approved_originals",
        "keyframes",
        "takes",
        "edit",
        "qc",
        "audio",
        "output",
        "logs",
        "prompts",
        "training_exports",
    ):
        (staging / directory).mkdir(parents=True, exist_ok=True)

    approved_at = now_iso()
    anchor_records = []
    for anchor in ANCHORS:
        original = SOURCE / str(anchor["source"])
        preserved = staging / "refs" / "approved_originals" / original.name
        shutil.copy2(original, preserved)
        number = int(str(anchor["id"]).rsplit("_", 1)[-1])
        normalized = staging / "keyframes" / f"anchor_{number:02d}.png"
        normalize_anchor(original, normalized)
        sidecar = anchor_sidecar(
            anchor=anchor,
            original_path=original,
            normalized_path=normalized,
            approved_at=approved_at,
            final_project=PROJECT,
        )
        write_json(staging / "keyframes" / f"anchor_{number:02d}.json", sidecar)
        anchor_records.append(
            {
                "id": anchor["id"],
                "title": anchor["title"],
                "file": f"keyframes/anchor_{number:02d}.png",
                "metadata": f"keyframes/anchor_{number:02d}.json",
                "width": 720,
                "height": 1280,
                "sha256": sha256(normalized),
                "status": "APPROVED_FOR_VIDEO",
                "approved_at": approved_at,
            }
        )

    shutil.copy2(SOURCE / "qc_contact_sheet.png", staging / "qc" / "approved_anchors_contact_sheet.png")
    shutil.copy2(SOURCE / "PROMPTS.md", staging / "prompts" / "SOURCE_ANCHOR_PROMPTS.md")

    takes = take_definitions(staging)
    # Paths persisted in Maestro must point to the final canonical project, not staging.
    staging_text = str(staging.resolve())
    project_text = str(PROJECT.resolve())
    takes = replace_tree_path(takes, staging_text, project_text)

    continuous_contract = {
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
    universal_gate = {
        "required": True,
        "policy_version": "2.0",
        "pillars": [
            "evident_camera",
            "real_depth",
            "internal_action",
            "clear_progression",
        ],
        "contract_gate": "python tools/transition_motion_gate.py production_manifest.json --stage contract",
        "approval_gate": "python tools/transition_motion_gate.py production_manifest.json --stage approval",
    }

    project_manifest = {
        "schema_version": "1.2",
        "project_id": PROJECT_ID,
        "title": "Gogeta - Danca da Fusao - Reels vertical 15s",
        "idea": "Goku e Vegeta fazem a danca da fusao; Gogeta nasce base e vira Super Saiyajin tradicional.",
        "objective": "Produzir um Reels live action cinematografico de 15 segundos com VFX exagerado e transicoes fisicas continuas.",
        "audience": "publico de videos curtos e fantasia de artes marciais",
        "duration_target_seconds": 15.0,
        "aspect_ratio": "9:16",
        "preview_resolution": "720x1280",
        "final_resolution": "1080x1920",
        "fps_preview": 60,
        "fps_final": 60,
        "created_at": approved_at,
        "updated_at": approved_at,
        "maestro_status": "IN_PROGRESS",
        "status": "IN_PROGRESS",
        "render_authorized": False,
        "take_queue": "take_queue.json",
        "style": {
            "primary": "ultra_photorealistic_live_action_blockbuster",
            "palette": ["moonlight blue", "energy orange", "fusion white-gold", "Super Saiyan gold"],
            "mood": ["epic", "concentrated", "explosive", "triumphant"],
        },
        "audio": {
            "directive_status": "awaiting_owner_directive",
            "authority": "owner_only",
            "default_without_directive": "visual_only",
            "mode": "visual_only",
            "music_provider": None,
            "voice_provider": None,
        },
        "identity_bible": {
            "characters": ["Goku", "Vegeta", "Gogeta base", "Gogeta Super Saiyajin tradicional"],
            "fixed_objects": ["cratera noturna", "lua no alto a esquerda", "traje Metamoran de Gogeta"],
            "forbidden_changes": ["face replacement", "costume replacement", "extra character", "environment reset"],
        },
        "global_negative_rules": GLOBAL_NEGATIVE,
        "model_formula": {
            "base_image": "owner-approved OpenAI built-in image generation anchors",
            "video_preview": "MiniMax H3 FL2VA pruned INT8 ConvRot + Qwen3-VL-32B, vertical 720x1280/24",
            "prompt_contract": "official h3-prompt-writing local pinned",
            "motion_review": "RIFE 4.6 native 24 to CFR 60 after generated take",
            "video_final": "human-approved RealESRGAN x2 75/25, 1080x1920/60",
        },
        "primary_orchestration_policy": "minimax_h3_take_contract@2026-08-16",
        "continuous_action_contract": continuous_contract,
        "universal_orchestration": True,
        "approved_anchors": anchor_records,
        "owner_approval": {
            "status": "APPROVED",
            "approved_at": approved_at,
            "evidence": "Imagens aprovado jogar os takes no maestro",
            "scope": "four still anchors only; video and audio remain ungenerated",
        },
    }

    take_queue = {
        "schema_version": "1.5",
        "project_id": PROJECT_ID,
        "methodology": "three_minimax_h3_vertical_5s_first_last_human_qc_serial_then_15s_reels",
        "status": "READY_FOR_MANUAL_VIDEO_GENERATION",
        "updated_at": approved_at,
        "render_authorized": False,
        "primary_orchestration_policy": "minimax_h3_take_contract@2026-08-16",
        "engine_policy": {
            "primary_take_orchestration": {
                "status": "ACTIVE_UNTIL_OWNER_OVERRIDE",
                "generation_profile": "minimax_h3_fl2va_int8_vertical_720x1280p24",
                "backend": "ComfyUI MiniMax H3 official local workflow",
                "text_encoder": "Qwen3-VL-32B MiniMax H3 NVFP4 AWQ",
                "conditioning_profile": "identity_locked_first_last_frame",
            },
            "review_motion_pipeline": {
                "enabled": True,
                "source_fps": 24,
                "delivery_fps": 60,
                "interpolator": "RIFE 4.6",
                "encoder": "h264_nvenc",
                "upscale_allowed_before_human_approval": False,
            },
            "audio_directive": {
                "authority": "owner_only",
                "default_without_explicit_directive": "visual_only",
                "native_generation_without_directive": "forbidden",
                "mix_without_directive": "forbidden",
            },
        },
        "assembly": {
            "preview": {"width": 720, "height": 1280, "fps": 60, "format": "mp4"},
            "final": {"width": 1080, "height": 1920, "fps": 60, "format": "mp4"},
            "target_duration_seconds": 15.0,
            "native_h3_frames_per_take": 124,
            "native_h3_effective_seconds_per_take": 124 / 24,
            "edit_rule": "trim only moving intervals to 15.0s; never freeze, crossfade or hold",
        },
        "universal_transition_motion_gate": universal_gate,
        "continuous_action_contract": continuous_contract,
        "global_negative_rules": GLOBAL_NEGATIVE,
        "takes": takes,
    }

    production_manifest = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "sequence_id": "fusion_dance_to_super_saiyan_vertical_15s",
        "status": "CONTRACT_APPROVED_ANCHORS_READY_VIDEO_NOT_GENERATED",
        "created_at": approved_at,
        "updated_at": approved_at,
        "render_authorized": False,
        "universal_transition_motion_gate": universal_gate,
        "continuous_action_contract": continuous_contract,
        "takes": [
            {
                "id": take["id"],
                "slug": take["slug"],
                "is_transition": False,
                "shot_contract": take["shot_contract"],
                "qc": take["qc"],
            }
            for take in takes
        ],
    }

    write_json(staging / "project_manifest.json", project_manifest)
    write_json(staging / "take_queue.json", take_queue)
    write_json(staging / "production_manifest.json", production_manifest)
    for take in takes:
        (staging / "prompts" / f"{take['id']}.md").write_text(
            f"# {take['title']}\n\n{take['animation_prompt']}\n",
            encoding="utf-8",
        )
    (staging / "FIXLOG.md").write_text(
        "# FIXLOG\n\n"
        f"## {approved_at} - registro inicial no Maestro\n\n"
        "- Quatro imagens aprovadas pelo proprietario foram preservadas em refs/approved_originals.\n"
        "- Copias tecnicas foram normalizadas para PNG RGB 720x1280, proporcao 9:16 exata.\n"
        "- Tres takes H3 verticais de cinco segundos foram registrados com ancoras inicial/final compartilhadas.\n"
        "- Contratos de camera, profundidade, acao interna, progressao e movimento integral foram adicionados.\n"
        "- Renderizacao e audio permanecem nao autorizados; nenhum job de GPU foi criado.\n",
        encoding="utf-8",
    )
    shutil.copy2(SOURCE / "anchors_manifest.json", staging / "refs" / "source_anchors_manifest.json")

    staging.replace(PROJECT)
    result = {
        "ok": True,
        "project_id": PROJECT_ID,
        "project_dir": str(PROJECT),
        "anchors": len(anchor_records),
        "takes": len(takes),
        "render_authorized": False,
        "audio_mode": "visual_only",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
