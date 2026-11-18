"""Cadastra no Maestro as transicoes restantes de Ritmos da Revolta.

Cada projeto recebe 12 blocos de legenda e tres fotos-base ineditas por bloco.
As imagens sao contratadas como Qwen Image texto-para-imagem: nenhuma arte
existente em assets/transicoes e usada como entrada ou referencia visual.

O script e idempotente:
- cria apenas projetos ausentes;
- nunca sobrescreve um projeto que nao tenha sido criado por este fluxo;
- nao recria pedidos ANCHOR que ja existam;
- nao aprova imagens nem takes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


VIDEO_ENGINE_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = (VIDEO_ENGINE_ROOT / "projetos").resolve()
GAME_ROOT = Path(r"E:\Pemara\Ritmos da Revolta").resolve()
CAPTION_SOURCE = GAME_ROOT / "js" / "config" / "index.js"
DEFAULT_STUDIO_URL = "http://127.0.0.1:8029"
PIPELINE_ORIGIN = "ritmos_remaining_transitions_qwen_text_only_v1"

QWEN_MODEL = "qwen_image_2512_fp8_e4m3fn.safetensors"
QWEN_LORA = "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"
IMAGE_WIDTH = 1536
IMAGE_HEIGHT = 864
IMAGE_STEPS = 4
IMAGE_GUIDANCE = 1.0

NEGATIVE_RULES = [
    "person",
    "people",
    "human",
    "character",
    "hero",
    "villain",
    "boss",
    "monster",
    "creature",
    "animal",
    "body",
    "face",
    "portrait",
    "humanoid silhouette",
    "human shadow",
    "mannequin",
    "statue shaped like a person",
    "robot",
    "android",
    "mech",
    "vehicle",
    "tractor",
    "readable text",
    "letters",
    "numbers",
    "subtitle",
    "caption",
    "logo",
    "watermark",
    "UI",
    "picture frame",
    "photo frame",
    "decorative border",
    "poster",
    "card",
    "inset image",
    "split screen",
    "collage",
    "comic panel",
    "black bars",
    "letterbox",
    "pillarbox",
    "photorealism",
    "3D render",
    "pixel art",
    "blurry",
    "muddy",
    "warped architecture",
    "duplicated objects",
]
NEGATIVE = ", ".join(NEGATIVE_RULES)

SHOT_VARIANTS = {
    "A": {
        "role": "establishing_event",
        "viewpoint": (
            "Use a wide establishing viewpoint with a strong foreground threshold, "
            "a readable middle-ground event and a deep background destination. "
            "Show the environmental event just beginning."
        ),
        "camera": (
            "Slow physical dolly forward with clear foreground, middle-ground and "
            "background parallax."
        ),
        "progression": "The caption event begins and creates a visible directional cue.",
    },
    "B": {
        "role": "material_detail",
        "viewpoint": (
            "Use a genuinely different low three-quarter or lateral viewpoint, not a "
            "crop of the establishing shot. Put one material detail in the near "
            "foreground while the same environment remains legible behind it. "
            "Show the environmental event at its midpoint."
        ),
        "camera": (
            "Lateral physical track around the foreground motif while the background "
            "moves at a different rate."
        ),
        "progression": "The physical material reaction advances and exposes hidden depth.",
    },
    "C": {
        "role": "consequence_transition",
        "viewpoint": (
            "Use a new elevated, rear or opposite-side viewpoint that reveals the "
            "consequence of the caption and a clear route toward the next beat. "
            "Show the environmental event at its strongest state."
        ),
        "camera": (
            "Crane or pull back through layered geometry, ending with momentum toward "
            "the next hard cut."
        ),
        "progression": "The event reaches a clear consequence and points toward the next scene.",
    },
}


PROJECTS: list[dict[str, Any]] = [
    {
        "project_id": "transicao_f3_f4_fabrica_ritmos_qwen",
        "title": "Ritmos da Revolta — Transição F3→F4",
        "sequence_id": "fabrica_de_ritmos_f3_f4",
        "music": GAME_ROOT / "assets" / "sounds" / "music" / "Cold_Steel_Exhale.mp3",
        "duration_fallback": 177.35,
        "seed_base": 534000,
        "seed_overrides": {"S01A": 534039},
        "palette": "cold blue steel, oxidized orange, fading violet forest light and restrained teal accents",
        "story_flow": "empty corrupted clearing -> industrial threshold -> dormant rhythm factory -> full mechanical awakening",
        "slides": [
            (
                "A clareira ficou vazia, mas o silêncio não voltou.",
                "An absolutely empty corrupted-forest clearing after conflict. The only visible forms are trees, wet roots, bare soil, shallow puddles and violet fog. Concentric ripples cross the puddles and loose leaves tremble under a low infrasonic rumble whose source remains completely off-screen.",
            ),
            (
                "Entre raízes mortas, o metal começou a aparecer.",
                "Dead roots split the damp soil and reveal long bands of cold blue steel, rivets and old rust emerging from beneath the forest floor.",
            ),
            (
                "A trilha terminou diante de um portão industrial.",
                "A narrow dead-forest trail ends at a monumental closed industrial gate embedded in rock and roots, with pipes and warning lamps but no signage.",
            ),
            (
                "A floresta ficou do lado de fora da última luz roxa.",
                "The industrial threshold seen from inside: the forest recedes beyond the gate under one last violet glow while cold factory darkness takes over.",
            ),
            (
                "A Fábrica de Ritmos dormia em aço azul.",
                "A vast dormant rhythm factory of blue steel, conveyors, flywheels, pipes and silent speaker arrays, all empty and unpowered.",
            ),
            (
                "Luzes de aviso piscaram como um pulso mecânico.",
                "Rows of amber warning lamps pulse in sequence through the empty blue-steel factory, reflecting on grates, pipes and oil-dark floors.",
            ),
            (
                "Painéis rachados acordaram sem tocar música.",
                "Cracked analog control panels wake across an empty operations bay; unlabeled meters, blank screens and cold switches glow without readable symbols.",
            ),
            (
                "O núcleo da fábrica respirou vapor e ferrugem.",
                "The factory core: huge turbines and pressure vessels exhale white steam through rusted seams under cold blue machinery.",
            ),
            (
                "O chão de grade conduzia para o coração da máquina.",
                "A deep grated walkway crosses pipes and rotating shafts toward a distant central machine glowing through steam.",
            ),
            (
                "Alto-falantes mudos esperavam uma ordem impossível.",
                "Towering silent industrial speaker stacks face an empty production floor, their cones motionless beneath cables and warning lights.",
            ),
            (
                "O corredor abriu espaço para o próximo confronto.",
                "A narrowing machine corridor opens into a large empty circular confrontation floor marked only by light, grates and surrounding machinery.",
            ),
            (
                "A fábrica inteira pareceu ligar de uma só vez.",
                "The entire empty rhythm factory surges awake at once: blue power races through conduits, amber lamps ignite and steam floods layered machinery.",
            ),
        ],
    },
    {
        "project_id": "transicao_f4_f5_cavernas_amaldicoadas_qwen",
        "title": "Ritmos da Revolta — Transição F4→F5",
        "sequence_id": "cavernas_amaldicoadas_f4_f5",
        "music": GAME_ROOT / "assets" / "sounds" / "music" / "Weight_of_the_Iron_Pulse.mp3",
        "duration_fallback": 176.25,
        "seed_base": 545000,
        "seed_overrides": {
            "S05A": 545151,
            "S05B": 545152,
            "S08A": 545181,
            "S08B": 545182,
            "S08C": 545183,
        },
        "palette": "dying industrial amber, wet black stone, cold teal crystal light and sparse toxic green",
        "story_flow": "factory shutdown -> descent below machinery -> ancient wet ruins -> cursed cavern chamber",
        "slides": [
            (
                "As engrenagens pararam de girar.",
                "An empty factory mechanism after shutdown; enormous gears sit perfectly still while residual sparks and steam fade through blue steel.",
            ),
            (
                "Debaixo da fábrica, um corredor descia para a pedra.",
                "A maintenance passage beneath the factory slopes steeply downward, changing from bolted steel to wet natural stone.",
            ),
            (
                "O metal terminou onde a caverna começou.",
                "A precise boundary where the last steel plates, rails and pipes end at a raw cavern mouth of damp black rock.",
            ),
            (
                "A água pingava sobre trilhos que ninguém usava.",
                "Abandoned narrow-gauge rails disappear into darkness while water drips from stalactites and rings across shallow puddles.",
            ),
            (
                "Ruínas antigas surgiram entre paredes úmidas.",
                "Ancient broken arches built only from plain geometric stone blocks and collapsed undecorated masonry emerge from wet cave walls. Every surface is empty architecture: no statues, reliefs, faces, bodies, effigies or figurative ornament.",
            ),
            (
                "Cristais frios iluminaram o caminho sem canto.",
                "Clusters of cold teal crystals illuminate a winding empty path through damp stone, mineral dust and thin mist.",
            ),
            (
                "A caverna abriu sua primeira grande garganta.",
                "A colossal vertical cave throat opens beneath a narrow ledge, revealing layered rock, distant crystal light and immense depth.",
            ),
            (
                "Pedras quebradas guardavam uma história sem nome.",
                "Weathered broken slabs with completely blank, rough, scraped-flat faces lie among collapsed foundations on the cavern floor. The stones carry history only through cracks, erosion and missing pieces, with no carvings, glyphs, reliefs or inscriptions.",
            ),
            (
                "A luz verde respirava pelas veias minerais.",
                "Toxic green light pulses through branching mineral veins inside dark wet rock, reflected in water and crystal edges.",
            ),
            (
                "A câmara principal apareceu atrás da névoa fria.",
                "Cold mist parts to reveal an enormous main cavern chamber with ancient platforms, teal crystals and a deep central floor.",
            ),
            (
                "O chão estava limpo demais para um lugar esquecido.",
                "An unnaturally clean circular patch of stone interrupts the debris-filled cavern, surrounded by mist, ruins and mineral light.",
            ),
            (
                "As Cavernas Amaldiçoadas abriram passagem.",
                "The cursed caverns form a vast open passage beyond the main chamber as rock seams, crystals and green mineral light align toward the darkness.",
            ),
        ],
    },
    {
        "project_id": "transicao_f5_f6_torre_tenebra_qwen",
        "title": "Ritmos da Revolta — Transição F5→F6",
        "sequence_id": "torre_do_tenebra_f5_f6",
        "music": GAME_ROOT / "assets" / "sounds" / "music" / "Water_Under_The_Server.mp3",
        "duration_fallback": 173.61,
        "seed_base": 556000,
        "seed_overrides": {
            "S01A": 556111,
            "S01B": 556112,
            "S01C": 556113,
            "S04A": 556241,
            "S04B": 556242,
            "S04C": 556243,
        },
        "palette": "cold teal stone, sick digital green, concrete gray, smoke black and distant city-fire orange",
        "story_flow": "crystal blackout -> digital corruption in stone -> vertical tower ascent -> burning broadcast floor",
        "slides": [
            (
                "Os cristais da caverna perderam o brilho.",
                "Opaque matte black-teal mineral shards sit inert across wet stone and black water, almost lost in darkness and lit only by a weak distant orange fire reflection. Their surfaces are soot-coated, non-luminous and completely without cyan emission or bright edges.",
            ),
            (
                "Uma estática verde entrou pelas veias da pedra.",
                "Sick green digital interference travels through mineral veins in the rock like a broken signal, without symbols or text.",
            ),
            (
                "Um eixo antigo subia até as fundações da torre.",
                "An ancient vertical service shaft rises from the cavern into massive concrete tower foundations, crossed by cables, ladders and elevator rails.",
            ),
            (
                "O elevador inferior abriu para concreto e silêncio.",
                "A heavy lower freight elevator stands open onto an empty brutalist concrete service level. The door head and surrounding walls are plain unmarked concrete slabs, while every control surface is featureless dark metal without illumination. Bare pipes and simple green ceiling tubes provide the only light.",
            ),
            (
                "Lá em cima, a cidade queimava atrás dos vidros partidos.",
                "From a high empty tower floor, shattered windows reveal a distant city burning orange beneath smoke and a dark sky.",
            ),
            (
                "Servidores acesos chiavam sem formar palavras.",
                "Rows of active server cabinets hiss in an empty machine room; indicator lights flicker randomly with no readable interface.",
            ),
            (
                "O corredor corporativo parecia mais longo a cada passo.",
                "An empty corporate corridor stretches through forced perspective, repeating doors, glass partitions and green ceiling lights toward impossible depth.",
            ),
            (
                "As salas de transmissão piscavam em verde doente.",
                "Abandoned broadcast rooms flash with sick green signal light through studio glass, cables and blank monitors.",
            ),
            (
                "O fogo refletia em telas que ninguém controlava.",
                "Orange city fire reflects across many uncontrolled blank screens and cracked glass in an empty command area.",
            ),
            (
                "A torre mostrou o andar onde o ruído mandava.",
                "The tower's central broadcast floor opens around a dense signal core of cables, server fans, blank displays and vibrating architecture.",
            ),
            (
                "O chão carbonizado abriu uma arena sem aplausos.",
                "A burned corporate floor collapses into a broad empty arena surrounded by charred beams, smoke and silent screens.",
            ),
            (
                "A Torre do Tenebra esperava no alto da cidade.",
                "The upper tower rises above the burning city as a severe black-and-concrete broadcast citadel, its highest empty floors glowing green.",
            ),
        ],
    },
    {
        "project_id": "transicao_f6_f7_trono_tenebra_qwen",
        "title": "Ritmos da Revolta — Transição F6→F7",
        "sequence_id": "trono_do_tenebra_f6_f7",
        "music": GAME_ROOT / "assets" / "sounds" / "music" / "Trono_do_Tenebra.mp3",
        "duration_fallback": 177.45,
        "seed_base": 567000,
        "seed_overrides": {
            "S01A": 567311,
            "S01B": 567312,
            "S01C": 567313,
            "S02A": 567121,
            "S02B": 567122,
            "S02C": 567123,
        },
        "palette": "charcoal black, television white-gray, electric violet, deep red signal tears and cold steel",
        "story_flow": "tower power loss -> broadcast void -> static cathedral -> empty final throne architecture",
        "slides": [
            (
                "A sala superior da torre apagou suas últimas chamas.",
                "An abandoned upper tower mechanical hall is completely cold, soaked and dark after a disaster. Matte soot-black steel, black glass, pale gray steam, damp ash and faint violet fluorescent fixtures fill the empty space. The entire image uses a uniform cool gray-and-violet palette, and every wall and floor surface remains dark with zero warm-colored light source anywhere.",
            ),
            (
                "As janelas trocaram a cidade por estática.",
                "The actual tall architectural window panes of an empty tower hall are filled edge-to-edge with turbulent white-gray analog static instead of any exterior view. The static belongs only inside the windows; there are no televisions, monitors, screens or visible city skyline.",
            ),
            (
                "Pedaços da torre começaram a flutuar no vazio.",
                "Broken slabs, beams and glass fragments detach from the empty tower and float into a surrounding black broadcast void.",
            ),
            (
                "O chão virou uma plataforma de transmissão quebrada.",
                "The former floor becomes a fractured broadcast platform of steel, cables and static-lit gaps suspended over darkness.",
            ),
            (
                "Um corredor de ruído abriu caminho no escuro.",
                "A corridor made of layered static bands and broken signal geometry opens through the black void, with no figures or symbols.",
            ),
            (
                "Monólitos partidos responderam com energia roxa.",
                "Broken abstract monoliths around the empty path answer one another with electric violet arcs and deep red signal tears.",
            ),
            (
                "Ao longe, um trono vazio tomou forma.",
                "A distant empty throne-like architectural structure condenses from static on a raised platform, clearly unoccupied and non-humanoid.",
            ),
            (
                "A estática se organizou como uma catedral sem voz.",
                "Television static aligns into vast cathedral-like vaults, ribs and signal windows around an empty central aisle.",
            ),
            (
                "O vazio finalmente parou de se mover.",
                "The black broadcast void becomes unnaturally still; suspended debris, static bands and violet dust freeze around the empty route.",
            ),
            (
                "Cada rachadura roxa parecia escutar.",
                "Thin violet cracks spread through the platform and monoliths, converging toward the empty center like a listening network.",
            ),
            (
                "A plataforma final esperava sem plateia.",
                "A vast final platform stands completely empty under static vaults, violet fractures and distant red signal seams.",
            ),
            (
                "O Trono do Tenebra abriu o último compasso.",
                "The unoccupied throne architecture fully opens as concentric signal rings, violet power and fractured black stone establish the final arena.",
            ),
        ],
    },
    {
        "project_id": "cutscene_final_maestro_qwen",
        "title": "Ritmos da Revolta — Cutscene Final",
        "sequence_id": "despedida_do_maestro_final",
        "music": GAME_ROOT / "assets" / "sounds" / "music" / "ending_inst.mp3",
        "duration_fallback": 180.0,
        "seed_base": 578000,
        "seed_overrides": {
            "S02A": 578121,
            "S02B": 578122,
            "S02C": 578123,
            "S11B": 578212,
        },
        "palette": "exhausted black and violet giving way slowly to warm gold, soft pink, silver-gray and fragile natural color",
        "story_flow": "silent aftermath -> spectral control breaks -> forgiveness represented by light -> color and rhythm return",
        "slides": [
            (
                "A última nota de Tenebra morreu antes de tocar o chão.",
                "An empty throne chamber after the final battle; the last visible sound ripple fades in midair above a cracked dais before reaching the floor.",
            ),
            (
                "O Chapéu do Espectro perdeu o domínio sobre a sombra.",
                "A small empty wide-brim black felt hat lies collapsed, flattened and completely inert on a cracked stone dais. Ordinary diffuse light returns as a simple soft shadow recedes across the floor; the hat has no face, skull shape, tendrils, appendages or levitation.",
            ),
            (
                "Dentro da escuridão, alguém ainda lembrava o nome das filhas.",
                "A fragile warm core of light survives inside receding darkness, answering two small distant pools of silver-gray and soft pink light; no figures.",
            ),
            (
                "Maestro: \"Gray... Pinki... me perdoem...\"",
                "On an empty ruined stage, one weak warm central light reaches toward two unoccupied microphone positions marked only by silver-gray and soft pink illumination.",
            ),
            (
                "Pinki: \"Pai!\"",
                "A ribbon of soft pink stage light races across the empty floor toward the fragile warm central glow, bending around broken cables and debris.",
            ),
            (
                "Gray: \"Nós ouvimos você.\"",
                "A restrained silver-gray beam crosses the empty stage threshold and joins the pink light near the fading warm glow.",
            ),
            (
                "Maestro: \"Eu tentei proteger vocês... e esqueci de escutar.\"",
                "The warm central signal extends through two empty microphone stands, but its light passes through them and begins breaking into delicate particles.",
            ),
            (
                "Maestro: \"Vivam. Façam o mundo cantar sem mim.\"",
                "The warm light dissolves above two empty pools of gray and pink illumination while dormant instruments and cables begin to regain a faint pulse.",
            ),
            (
                "O Chapéu do Espectro se estilhaçou em silêncio.",
                "The abandoned Spectral Hat fractures completely; black shards rise and transform into pale dust without explosion or impact text.",
            ),
            (
                "A cor voltou primeiro às pequenas coisas.",
                "Color returns to tiny environmental details first: one stage bulb, a cable sheath, a small flower through cracked concrete and glass reflections.",
            ),
            (
                "Gray: \"Então vamos fazer o mundo cantar de novo.\"",
                "A single continuous environmental vista connects the wounded street, studio doorway, forest edge, factory, cavern and distant tower through light and perspective, never as panels.",
            ),
            (
                "O ritmo nunca morre. Apenas espera para ser ouvido novamente.",
                "An empty stage waits in calm darkness while warm golden particles linger at center and one subtle pulse travels through cables toward the wider world.",
            ),
        ],
    },
]


def utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_duration(path: Path, fallback: float) -> float:
    if not path.is_file():
        return fallback
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return round(float(result.stdout.strip()), 6)
    except (OSError, ValueError, subprocess.SubprocessError):
        return fallback


def validate_caption_source() -> None:
    source = CAPTION_SOURCE.read_text(encoding="utf-8")
    missing = [
        caption
        for project in PROJECTS
        for caption, _visual in project["slides"]
        if caption not in source
    ]
    if missing:
        raise RuntimeError(
            "As seguintes legendas nao conferem com a fonte canonica: "
            + "; ".join(missing)
        )


def image_prompt(
    project: dict[str, Any],
    slide_number: int,
    caption: str,
    visual: str,
    variant_id: str,
) -> str:
    variant = SHOT_VARIANTS[variant_id]
    return (
        "Generate a completely new full-bleed 16:9 cinematic environment frame for "
        "the dark 2D beat-em-up game Ritmos da Revolta. The canonical narrative text "
        "has already been translated into the purely visual environmental direction "
        "below; do not render or reproduce the source sentence. Do not inspect, reuse, "
        "edit, imitate, trace or compose from any existing transition image. "
        f"Environmental interpretation: {visual} Palette: {project['palette']}. "
        f"Shot {slide_number:02d}{variant_id}: {variant['viewpoint']} "
        "Modern hand-painted 2D anime game cutscene art, crisp controlled linework, "
        "layered painterly cel shading, dramatic but readable lighting, textured "
        "materials, strong atmospheric perspective, clear foreground/middle-ground/"
        "background separation, coherent architecture and object scale. Render one "
        "continuous edge-to-edge scene, never a frame within a frame. The scene is "
        "uninhabited. Every visible form must belong to scenery, architecture, "
        "vegetation, geological material, light or explicitly described inanimate "
        "equipment. Keep open ground visually empty unless the environmental "
        "interpretation explicitly names an object there. Do not print the caption "
        "or any other readable text, "
        "letters, numbers, logo, watermark or interface. Not photorealistic, not 3D "
        "and not pixel art."
    )


def build_take(
    project: dict[str, Any],
    duration: float,
    slide_number: int,
    caption: str,
    visual: str,
    variant_id: str,
) -> dict[str, Any]:
    variant = SHOT_VARIANTS[variant_id]
    variant_index = {"A": 1, "B": 2, "C": 3}[variant_id]
    take_id = f"S{slide_number:02d}{variant_id}"
    seed = int(
        project.get("seed_overrides", {}).get(
            take_id,
            int(project["seed_base"]) + slide_number * 10 + variant_index,
        )
    )
    prompt = image_prompt(project, slide_number, caption, visual, variant_id)
    negative = NEGATIVE
    if (
        project["project_id"] == "transicao_f5_f6_torre_tenebra_qwen"
        and slide_number == 1
    ):
        negative += (
            ", glowing crystal, luminous crystal, bioluminescence, cyan emission, "
            "bright turquoise crystal, neon mineral"
        )
    if (
        project["project_id"] == "transicao_f5_f6_torre_tenebra_qwen"
        and slide_number == 4
    ):
        negative += (
            ", signage, sign, exit sign, wayfinding, pictogram, icon, glyph, "
            "placard, label, illuminated indicator panel"
        )
    if (
        project["project_id"] == "transicao_f4_f5_cavernas_amaldicoadas_qwen"
        and slide_number in {5, 8}
    ):
        negative += (
            ", statue, effigy, bas-relief, human relief, carved face, carved body, "
            "carved figure, figurative ornament, glyph, rune, inscription"
        )
    if (
        project["project_id"] == "transicao_f6_f7_trono_tenebra_qwen"
        and slide_number == 1
    ):
        negative += (
            ", fire, flame, active ember, orange blaze, orange light, warm light, "
            "yellow light, burning floor, burning wall"
        )
    if (
        project["project_id"] == "transicao_f6_f7_trono_tenebra_qwen"
        and slide_number == 2
    ):
        negative += (
            ", television, TV set, monitor, freestanding screen, screen tower, "
            "city skyline, exterior city view"
        )
    if project["project_id"] == "cutscene_final_maestro_qwen" and slide_number == 2:
        negative += (
            ", tentacle, skull, eye, mouth, floating hat, levitating hat, "
            "organic appendage, living hat, monster hat"
        )
    if project["project_id"] == "cutscene_final_maestro_qwen" and slide_number == 11:
        negative += (
            ", multiple views, montage, image grid, inset scene, storyboard layout"
        )
    action = f"{visual} {variant['progression']}"
    return {
        "id": take_id,
        "slug": f"slide_{slide_number:02d}_{variant['role']}",
        "name": f"{take_id} — slide_{slide_number:02d}_{variant['role']}",
        "canonical_slide": slide_number,
        "caption": caption,
        "objective": action,
        "target_duration_seconds": round(duration / 36.0, 6),
        "maestro_status": "PLANNED",
        "maestro_notes": (
            "Foto-base inédita solicitada ao Qwen Image; somente legenda e direção "
            "textual, sem reaproveitamento das imagens atuais."
        ),
        "base_image": {
            "status": "required_new_qwen_image",
            "file": "",
            "metadata": "",
            "source_approved_image": "",
            "generation_mode": "text_to_image",
            "source_policy": "canonical_caption_and_text_direction_only",
            "prompt": prompt,
            "negative": negative,
            "model": QWEN_MODEL,
            "lora": QWEN_LORA,
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "steps": IMAGE_STEPS,
            "guidance": IMAGE_GUIDANCE,
            "seed": seed,
            "required_objects": {
                "canonical_caption": caption,
                "environmental_interpretation": visual,
                "full_bleed_16_9": True,
                "characters_forbidden": True,
            },
        },
        "shot_contract": {
            "subject": "new empty environmental scene generated only from canonical text",
            "action": action,
            "scene": visual,
            "camera": {"movement": variant["camera"]},
            "motion_beats": {
                "start": "approved new Qwen Image anchor",
                "middle": "physical environmental reaction plus independent depth motion",
                "end": variant["progression"],
            },
            "negative_rules": NEGATIVE_RULES,
        },
        "animation_prompt": (
            f"Animate only the approved empty environment for {take_id}. "
            f"{variant['camera']} Environmental action: {action} Preserve the exact "
            "approved objects, architecture, palette and lighting. Prove depth through "
            "differential foreground, middle-ground and background motion. Do not add "
            "people, characters, creatures, faces, silhouettes, readable text, logos "
            "or extra objects."
        ),
        "video_generation": {
            "model": "wan2.2_i2v_high_noise_14B_Q5_K_M.gguf",
            "model_pair": [
                "wan2.2_i2v_high_noise_14B_Q5_K_M.gguf",
                "wan2.2_i2v_low_noise_14B_Q5_K_M.gguf",
            ],
            "width": 768,
            "height": 432,
            "fps": 24,
            "frames": 121,
            "steps": 20,
            "guidance": 4.5,
            "seed": seed + 500000,
            "profile": "wan22_fun_camera_v1",
            "authorization": "blocked_until_explicit_user_video_generation_request",
        },
        "video": {"status": "planned"},
        "qc": {
            "status": "waiting_text_generated_anchor",
            "transition_motion_gate": {
                "required": True,
                "pillars": [
                    "evident_camera",
                    "real_depth",
                    "internal_action",
                    "clear_progression",
                ],
            },
        },
        "maestro_last_job_id": "",
        "maestro_last_error": "",
        "maestro_updated_at": utc_now(),
        "maestro_director_requests": [],
    }


def project_payloads(project: dict[str, Any], duration: float) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    now = utc_now()
    takes: list[dict[str, Any]] = []
    slide_plan: list[dict[str, Any]] = []
    for slide_number, (caption, visual) in enumerate(project["slides"], start=1):
        slide_takes = [
            build_take(project, duration, slide_number, caption, visual, variant_id)
            for variant_id in ("A", "B", "C")
        ]
        takes.extend(slide_takes)
        slide_plan.append(
            {
                "slide": slide_number,
                "caption": caption,
                "environmental_interpretation": visual,
                "takes": [
                    {
                        "id": take["id"],
                        "role": take["slug"],
                        "seed": take["base_image"]["seed"],
                        "prompt": take["base_image"]["prompt"],
                    }
                    for take in slide_takes
                ],
            }
        )

    queue = {
        "schema_version": "2.0",
        "project_id": project["project_id"],
        "pipeline_origin": PIPELINE_ORIGIN,
        "methodology": "three_text_generated_qwen_anchors_per_caption_then_human_review",
        "status": "anchor_preproduction_ready",
        "updated_at": now,
        "generation_locked": True,
        "anchor_generation_authorized": True,
        "video_generation_authorized": False,
        "global_negative_rules": NEGATIVE_RULES,
        "universal_transition_motion_gate": {
            "required": True,
            "pillars": [
                "evident_camera",
                "real_depth",
                "internal_action",
                "clear_progression",
            ],
        },
        "takes": takes,
    }
    direction = {
        "schema_version": "1.0",
        "project_id": project["project_id"],
        "pipeline_origin": PIPELINE_ORIGIN,
        "source_caption_file": CAPTION_SOURCE.as_posix(),
        "source_policy": (
            "Only canonical captions and written environmental direction are used. "
            "Existing transition images are forbidden as generation inputs or references."
        ),
        "image_model": QWEN_MODEL,
        "image_lora": QWEN_LORA,
        "image_geometry": f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        "negative": NEGATIVE,
        "slides": slide_plan,
    }
    production = {
        "schema_version": "1.0",
        "project_id": project["project_id"],
        "sequence_id": project["sequence_id"],
        "pipeline_origin": PIPELINE_ORIGIN,
        "status": "anchor_preproduction_ready",
        "created_at": now,
        "anchor_generation_authorized": True,
        "video_generation_authorized": False,
        "authorization": (
            "Pedido explicito do usuario em 2026-07-27 para gerar do zero no Qwen "
            "Image todas as transicoes restantes ate o final do jogo."
        ),
        "duration_target_seconds": duration,
        "canonical_slide_count": 12,
        "planned_anchor_count": 36,
        "planned_microtake_count": 36,
        "story_flow": project["story_flow"],
        "source_assets": {
            "caption_source": CAPTION_SOURCE.as_posix(),
            "audio": project["music"].as_posix(),
            "audio_sha256": sha256(project["music"]) if project["music"].is_file() else "",
            "official_anchor_root": None,
            "new_still_images_required": True,
            "existing_transition_images_policy": "forbidden_as_input_or_reference",
        },
        "direction": {
            "qwen_anchor_plan": "direction/qwen_anchor_plan.json",
            "caption_policy": (
                "Caption remains in game code and is never rendered inside the image."
            ),
            "environment_only": True,
        },
        "image_generation": {
            "method": "Qwen Image 2512 text-to-image from canonical caption",
            "model": QWEN_MODEL,
            "lora": QWEN_LORA,
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "steps": IMAGE_STEPS,
            "guidance": IMAGE_GUIDANCE,
            "variants_per_caption": 3,
            "human_review_required": True,
            "automatic_approval": False,
        },
        "video_generation": {
            "method": "Wan2.2 after anchor approval and a separate explicit request",
            "authorization": "locked",
        },
    }
    return queue, direction, production


def refresh_unrendered_contracts(
    project_dir: Path,
    project: dict[str, Any],
    duration: float,
) -> int:
    """Atualiza somente prompts ainda sem candidata, preservando fila e decisões."""

    queue_path = project_dir / "take_queue.json"
    current = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    expected, direction, _production = project_payloads(project, duration)
    expected_by_id = {
        str(take.get("id") or ""): take
        for take in expected["takes"]
        if isinstance(take, dict)
    }
    refreshed = 0
    for take in current.get("takes", []):
        if not isinstance(take, dict):
            continue
        expected_take = expected_by_id.get(str(take.get("id") or ""))
        if expected_take is None:
            continue
        base = take.get("base_image") if isinstance(take.get("base_image"), dict) else {}
        if str(base.get("file") or "").strip():
            continue
        base_status = str(base.get("status") or "").lower()
        if base_status not in {
            "required_new_qwen_image",
            "needs_derived_anchor",
            "required",
            "",
        }:
            continue

        expected_base = expected_take["base_image"]
        preserved_base = {
            key: base[key]
            for key in (
                "status",
                "file",
                "metadata",
                "source_approved_metadata",
                "last_rejected_candidate",
            )
            if key in base
        }
        base.update(expected_base)
        base.update(preserved_base)
        take["base_image"] = base
        for field in (
            "caption",
            "objective",
            "shot_contract",
            "animation_prompt",
            "video_generation",
        ):
            take[field] = expected_take[field]
        take["maestro_updated_at"] = utc_now()
        refreshed += 1

    if refreshed:
        current["updated_at"] = utc_now()
        atomic_json(queue_path, current)
    atomic_json(project_dir / "direction" / "qwen_anchor_plan.json", direction)
    return refreshed


def ensure_project(
    session: requests.Session,
    studio_url: str,
    project: dict[str, Any],
    duration: float,
) -> Path:
    project_dir = (PROJECTS_ROOT / project["project_id"]).resolve()
    if project_dir.parent != PROJECTS_ROOT:
        raise ValueError(f"project_id invalido: {project['project_id']}")
    created = False
    if not project_dir.exists():
        objective = (
            "Criar 36 fotos-base inéditas no Qwen Image (3 por legenda), usando "
            "somente as 12 legendas canônicas e direção ambiental textual; nenhuma "
            f"imagem atual será reutilizada. [{PIPELINE_ORIGIN}]"
        )
        response = session.post(
            f"{studio_url}/api/video-projects",
            json={
                "projectId": project["project_id"],
                "name": project["title"],
                "objective": objective,
                "durationSeconds": duration,
            },
            timeout=60,
        )
        response.raise_for_status()
        created = True

    manifest_path = project_dir / "project_manifest.json"
    queue_path = project_dir / "take_queue.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    queue_existing = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    existing_origin = str(
        queue_existing.get("pipeline_origin")
        or manifest.get("pipeline_origin")
        or ""
    )
    if not created and existing_origin != PIPELINE_ORIGIN:
        raise RuntimeError(
            f"Projeto existente fora deste fluxo; preservado sem alteracao: {project_dir}"
        )

    if not queue_existing.get("takes"):
        queue, direction, production = project_payloads(project, duration)
        atomic_json(queue_path, queue)
        atomic_json(project_dir / "direction" / "qwen_anchor_plan.json", direction)
        atomic_json(project_dir / "production_manifest.json", production)
        manifest.update(
            {
                "pipeline_origin": PIPELINE_ORIGIN,
                "duration_target_seconds": duration,
                "updated_at": utc_now(),
                "maestro_status": "PLANNED",
                "planned_anchor_count": 36,
                "source_policy": "canonical_caption_and_text_direction_only",
                "image_generation": production["image_generation"],
            }
        )
        atomic_json(manifest_path, manifest)
        readme = (
            f"# {project['title']}\n\n"
            "Projeto de 36 fotos-base inéditas: três enquadramentos por cada uma das "
            "12 legendas canônicas.\n\n"
            "- Gerador: Qwen Image 2512 + Lightning 4 steps.\n"
            "- Entrada visual: nenhuma.\n"
            "- Fonte narrativa: `E:/Pemara/Ritmos da Revolta/js/config/index.js`.\n"
            "- Imagens antigas em `assets/transicoes`: proibidas como entrada ou referência.\n"
            "- Regra: cenário ambiental vazio; sem personagens, silhuetas ou texto na arte.\n"
            "- Aprovação: sempre humana no Maestro; o executor não aprova automaticamente.\n"
            "- Vídeo: bloqueado até outro pedido explícito do usuário.\n"
        )
        (project_dir / "README.md").write_text(readme, encoding="utf-8", newline="\n")
        fixlog = (
            f"# FIXLOG\n\n## {utc_now()} — Cadastro inicial\n\n"
            "- Criado projeto canônico com 12 legendas e 36 fotos-base planejadas.\n"
            "- Prompts derivados somente de texto; imagens anteriores excluídas do pipeline.\n"
            "- Qwen Image texto-para-imagem autorizado; vídeo permanece bloqueado.\n"
            "- Nenhum take ou candidato foi aprovado automaticamente.\n"
        )
        (project_dir / "FIXLOG.md").write_text(fixlog, encoding="utf-8", newline="\n")
    else:
        refresh_unrendered_contracts(project_dir, project, duration)
    return project_dir


def ensure_anchor_requests(
    session: requests.Session,
    studio_url: str,
    project: dict[str, Any],
    project_dir: Path,
) -> list[str]:
    queue_path = project_dir / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    created_request_ids: list[str] = []
    for take in queue.get("takes", []):
        requests_list = (
            take.get("maestro_director_requests")
            if isinstance(take.get("maestro_director_requests"), list)
            else []
        )
        if any(
            isinstance(item, dict)
            and str(item.get("category") or "").upper() == "ANCHOR"
            for item in requests_list
        ):
            continue
        take_id = str(take.get("id") or "")
        response = session.patch(
            f"{studio_url}/api/video-projects/{project['project_id']}/takes/{take_id}",
            json={
                "directorRequest": {
                    "category": "ANCHOR",
                    "reason": (
                        "Gerar do zero no Qwen Image usando apenas a legenda canônica "
                        "e o prompt textual salvo; não reutilizar nem consultar as "
                        "imagens atuais."
                    ),
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        request_view = payload.get("directorRequest") or {}
        request_id = str(request_view.get("requestId") or "").strip()
        if request_id:
            created_request_ids.append(request_id)
    return created_request_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MAESTRO_STUDIO_URL", DEFAULT_STUDIO_URL),
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Cria os projetos e prompts sem registrar pedidos ANCHOR.",
    )
    args = parser.parse_args()

    validate_caption_source()
    studio_url = str(args.base_url).rstrip("/")
    session = requests.Session()
    created_requests: dict[str, list[str]] = {}
    for project in PROJECTS:
        duration = audio_duration(project["music"], project["duration_fallback"])
        project_dir = ensure_project(session, studio_url, project, duration)
        request_ids = (
            []
            if args.create_only
            else ensure_anchor_requests(session, studio_url, project, project_dir)
        )
        created_requests[project["project_id"]] = request_ids
        print(
            f"{project['project_id']}: 36 takes, "
            f"{len(request_ids)} novos pedidos ANCHOR, duracao={duration:.3f}s"
        )

    print(json.dumps({"createdRequestIds": created_requests}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
