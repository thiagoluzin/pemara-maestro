from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projetos" / "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
GOHAN_SOURCE_PROJECT = ROOT / "projetos" / "gohan_father_son_kamehameha_vertical_10s_liveaction_v1"
GOHAN_REFERENCE = GOHAN_SOURCE_PROJECT / "keyframes" / "anchor_v1_candidate.png"
ENGINE = "MiniMax H3 FL2VA pruned INT8 ConvRot"
PROFILE = "minimax_h3_fl2va_int8_cinematic_1280x720p24"


TAKES = [
    {
        "id": "01",
        "slug": "ultimas_palavras_android_16",
        "title": "As ultimas palavras do Android 16",
        "purpose": "Fazer a serenidade do Android 16 atravessar a resistencia moral de Gohan antes da crueldade de Cell.",
        "question": "Gohan aceitara que precisa lutar antes que Cell silencie o Android 16?",
        "start": "A cabeca mecanica intacta do Android 16 repousa entre fragmentos verdes; Gohan Super Saiyajin observa em choque e Cell se aproxima.",
        "middle": "Android 16 fala com serenidade sobre proteger a vida; Gohan escuta, afrouxa os punhos e uma lagrima se forma enquanto Cell entra no mesmo eixo.",
        "end": "Cell ergue a bota sobre a cabeca mecanica; Gohan percebe a intencao e avanca meio passo, tarde demais.",
        "reaction": "A expressao de Gohan passa de conflito e tristeza para alarme; Cell responde com desprezo calmo.",
        "camera": "Dolly fisico rente ao solo acompanha a cabeca do Android 16, sobe em arco curto por Cell e termina comprimindo a distancia ate Gohan.",
        "foreground": "Cabeca mecanica, pedras soltas e poeira cruzam a lente em velocidades distintas.",
        "midground": "Cell caminha e posiciona uma unica bota sem contato; placas e asas respondem ao vento.",
        "background": "Gohan permanece legivel contra as arquibancadas destruidas e o ceu de tempestade.",
        "cut": "Entregar movimento ao take seguinte no inicio da descida irreversivel da bota de Cell.",
        "events": 3,
        "damage_before": "Arena ja rachada; fragmentos verdes do corpo do Android 16 cercam a cabeca intacta.",
        "damage_after": "A bota desloca cascalho e abre uma fissura inicial ao lado da cabeca, ainda intacta.",
        "level": 1,
    },
    {
        "id": "02",
        "slug": "cell_esmaga_android_16",
        "title": "Cell esmaga o Android 16 e Gohan rompe",
        "purpose": "Transformar a execucao mecanica do Android 16 no estalo emocional irreversivel de Gohan.",
        "question": "O choque finalmente libertara a raiva que Gohan vinha contendo?",
        "start": "A bota de Cell ja desce; a cabeca mecanica do Android 16 permanece intacta e Gohan tenta reagir ao fundo.",
        "middle": "Cell pisa e quebra somente metal, ceramica e circuitos sem sangue; o impacto silencia o campo e a lagrima de Gohan cai entre poeira suspensa.",
        "end": "A lagrima toca a pedra e se desfaz; o rosto de Gohan endurece, o vento inverte e o primeiro arco eletrico rasga sua aura dourada.",
        "reaction": "Cell encara Gohan esperando desespero, mas recua o queixo ao reconhecer uma energia diferente.",
        "camera": "A camera desce junto da bota, sofre o impacto fisico, percorre a fissura pelo chao e faz um push-in real ate os olhos de Gohan.",
        "foreground": "Fragmentos roboticos, poeira e a lagrima atravessam escalas diferentes, sem gore.",
        "midground": "Cell completa o esmagamento e retira o peso sem resetar a pose.",
        "background": "Gohan recebe vento crescente; tecido, cabelo e detritos se movem independentemente.",
        "cut": "Cortar no primeiro raio branco-azulado que sai de Gohan e ilumina Cell.",
        "events": 4,
        "damage_before": "Cabeca mecanica intacta sob a bota descendente; fissura inicial no piso.",
        "damage_after": "Cabeca reduzida a componentes mecanicos e ceramicos; fissura propagada ate Gohan.",
        "level": 2,
    },
    {
        "id": "03",
        "slug": "gohan_super_saiyajin_2",
        "title": "Gohan desperta o Super Saiyajin 2",
        "purpose": "Mostrar a passagem completa de dor contida para poder controlado, com a forma SSJ2 inequivoca.",
        "question": "Cell percebeu tarde demais que provocou um guerreiro acima dele?",
        "start": "Gohan ainda e Super Saiyajin comum; um unico arco eletrico o envolve e a fissura do Android 16 chega aos seus pes.",
        "middle": "A energia sobe em coluna, o cabelo fica mais agudo e definido, relampagos branco-azulados multiplicam-se e o piso afunda sob pressao real.",
        "end": "O mesmo Gohan termina Super Saiyajin 2, olhos verde-azulados firmes, cabelo dourado mais afiado e relampagos constantes; Cell perde o sorriso.",
        "reaction": "Gohan deixa de gritar e assume silencio concentrado; Cell protege o rosto e recua um passo involuntario.",
        "camera": "Orbit fisico de cento e vinte graus ao redor de Gohan, recuo empurrado pela onda de choque e reentrada baixa quando a aura estabiliza.",
        "foreground": "Lajes levantadas, fagulhas e tecido rasgado cruzam a camera com inercia propria.",
        "midground": "Gohan transforma postura, cabelo, olhar e aura sem troca de corpo ou rosto.",
        "background": "Cell e as ruinas sofrem parallax; nuvens se abrem e a arena afunda permanentemente.",
        "cut": "Cortar quando Gohan desaparece do centro da cratera ainda em aceleracao.",
        "events": 4,
        "damage_before": "Fissura chega aos pes de Gohan; arena ainda sustenta sua silhueta.",
        "damage_after": "Cratera radial funda, lajes levantadas e corredor aberto nas nuvens permanecem visiveis.",
        "level": 3,
    },
    {
        "id": "04",
        "slug": "cell_juniors_em_um_golpe",
        "title": "Gohan elimina os Cell Juniors",
        "purpose": "Preservar a ordem canonica: Gohan demonstra a nova superioridade antes de voltar sua atencao a Cell.",
        "question": "Os Cell Juniors conseguem sequer acompanhar a velocidade do SSJ2?",
        "start": "Gohan SSJ2 sai da cratera em velocidade; dois Cell Juniors azuis atacam seus aliados fora do eixo principal.",
        "middle": "Gohan intercepta o primeiro com um golpe curto e atravessa o segundo com uma unica investida; cada impacto tem contato e consequencia separados.",
        "end": "Os dois Cell Juniors se desfazem em energia e poeira sem gore; Gohan pousa ja virando o tronco para Cell, sem pose celebratoria.",
        "reaction": "Cell acompanha atrasado e sua confianca vira irritacao; Gohan nao desvia o foco dos aliados por mais de um instante.",
        "camera": "Travelling lateral rapido atravessa colunas quebradas, chicote fisico entre os dois impactos e crane baixo que encontra Cell no novo eixo.",
        "foreground": "Colunas, cascalho e residuos azuis passam por oclusoes breves sem esconder trocas de identidade.",
        "midground": "Gohan executa dois golpes unicos, completos e assimetricos, mantendo cabelo e aura SSJ2.",
        "background": "A cratera e as ruinas do take anterior persistem; Cell muda de escala durante o giro final.",
        "cut": "Cortar quando Cell inicia a primeira investida contra Gohan ja voltado para ele.",
        "events": 4,
        "damage_before": "Cratera radial e lajes suspensas continuam no campo; aliados permanecem pressionados fora do quadro principal.",
        "damage_after": "Duas novas trilhas de impacto e colunas quebradas permanecem; os Cell Juniors nao retornam.",
        "level": 4,
    },
    {
        "id": "05",
        "slug": "gohan_domina_cell_corpo_a_corpo",
        "title": "Gohan domina Cell no corpo a corpo",
        "purpose": "Converter o poder recem-desperto em golpes pesados, legiveis e emocionalmente satisfatorios contra Cell.",
        "question": "Cell consegue atingir Gohan agora que a diferenca de velocidade foi revelada?",
        "start": "Cell investe com socos e cauda em movimento continuo; Gohan SSJ2 permanece no eixo e le o primeiro golpe.",
        "middle": "Gohan desvia por centimetros, entra por dentro da guarda e acerta um soco profundo no abdomen; Cell dobra o corpo antes do segundo impacto nas costelas.",
        "end": "Gohan sobe com um golpe curto no queixo e acompanha Cell no ar; Cell cospe apenas saliva e poeira, sem sangue ou gore.",
        "reaction": "Cell perde o ar e tenta recompor a guarda; Gohan mantem raiva controlada, sem sorriso sadico.",
        "camera": "Steadicam fisico orbita a investida, atravessa por tras de uma laje e sobe com os tres impactos sem cortes internos.",
        "foreground": "Cauda, lajes e poeira cruzam profundidades diferentes; faíscas de contato nao escondem anatomia.",
        "midground": "Cada golpe tem antecipacao curta, contato ponderado, deformacao de armadura e follow-through distinto.",
        "background": "Arquibancadas quebradas e nuvens abertas deslocam-se com parallax e recebem ondas de choque persistentes.",
        "cut": "Cortar com Cell ainda subindo e Gohan acelerando para intercepta-lo.",
        "events": 4,
        "damage_before": "Trilhas dos Cell Juniors e cratera SSJ2 permanecem no campo.",
        "damage_after": "Tres novas ondas de choque quebram o piso e deformam placas do abdomen e das costelas de Cell.",
        "level": 5,
    },
    {
        "id": "06",
        "slug": "cell_lancado_pela_arena",
        "title": "Gohan arremessa Cell pela arena",
        "purpose": "Fechar o minuto com dominio fisico inequivoco e movimento que convide a continuacao da luta.",
        "question": "A furia de Cell muda alguma coisa diante do controle absoluto de Gohan?",
        "start": "Cell ainda sobe do golpe no queixo; Gohan SSJ2 o alcanca antes de qualquer pausa.",
        "middle": "Cell dispara uma rajada curta e tenta esmagar Gohan com os dois bracos; Gohan atravessa a pressao, bloqueia, acerta o joelho no torso e gira para o chute final.",
        "end": "O chute de Gohan lanca Cell atraves de uma parede de pedra; o corpo de Cell segue em movimento entre destrocos enquanto Gohan parte em perseguicao.",
        "reaction": "Cell passa de furia a medo no instante anterior ao chute; Gohan continua concentrado e nao posa.",
        "camera": "Crane ascendente acompanha a interceptacao, mergulha junto ao joelho e faz travelling lateral ate a parede explodir para fora.",
        "foreground": "A rajada, fragmentos de carapaca e blocos de pedra atravessam a lente em camadas independentes.",
        "midground": "Bloqueio, joelho e chute formam uma cadeia causal sem repeticao ou troca de corpo.",
        "background": "A parede colapsa, revela a cratera anterior e permanece destruida na saida direcional.",
        "cut": "Encerrar aos 60 segundos com Cell ainda atravessando destrocos e Gohan em perseguicao, sem cauda estatica.",
        "events": 4,
        "damage_before": "Piso, arquibancadas e placas de Cell acumulam danos de todos os takes anteriores.",
        "damage_after": "Parede externa colapsada, corredor de destrocos aberto e Cell lancado para fora do setor central.",
        "level": 5,
    },
]


GLOBAL_STYLE = (
    "Photorealistic live-action feature film faithful to the Cell Games character silhouettes, colors, costumes and dramatic order; "
    "believable teenage human Gohan, physically convincing bio-engineered Cell and mechanical Android 16; natural pores, sweat, "
    "weathered fabric, practical creature armor enhanced by premium physically based VFX, weighted impacts and cinematic motion blur."
)

GLOBAL_FORBIDDEN = [
    "no anime drawing, cel shading, game render, cosplay fabric or plastic skin",
    "no blood, exposed flesh, gore or organic injury to Android 16; only mechanical fragments",
    "no duplicate Gohan, duplicate Cell, extra fighter, extra limb or body substitution",
    "no Goku spirit, Kamehameha, dialogue subtitles, logo, watermark or interface",
    "no instant unexplained SSJ2 before take 03 and no loss of SSJ2 lightning after take 03",
    "no robotic pauses, turn-based choreography, repeated strike, pose reset or return to idle",
    "no simple zoom-only motion, living photo, crossfade, freeze frame or static tail",
]


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transition_contract(spec: dict[str, object]) -> dict[str, object]:
    return {
        "camera_evidence": {
            "movement": spec["camera"],
            "physical_translation": True,
            "perspective_change": "Foreground moves fastest, character action moves at medium speed and ruined arena background moves slowest.",
        },
        "real_depth": {
            "foreground": spec["foreground"],
            "midground": spec["midground"],
            "background": spec["background"],
            "differential_motion": "Foreground, fighters and background maintain independently readable velocities and occlusions.",
            "occlusion_or_scale_change": "Debris and architecture briefly cross the lens while character scale changes through physical camera translation.",
        },
        "internal_action": {
            "primary_event": spec["middle"],
            "independent_elements": [
                "Hair, cloth, armor plates and bodies carry separate inertia through every impact.",
                "Dust, fragments, lightning and persistent arena damage move independently from the camera.",
            ],
            "camera_independent": True,
        },
        "progression": {
            "start": spec["start"],
            "middle": spec["middle"],
            "end": spec["end"],
            "end_state_change": f"{spec['damage_before']} -> {spec['damage_after']}",
            "exit_or_cut": spec["cut"],
        },
        "continuity": {
            "editorial_method": "generated_action_connector",
            "continuous_action": True,
            "motion_handoff": True,
            "action_occupies_full_duration": True,
            "entry_motion": spec["start"],
            "exit_motion": spec["cut"],
            "interval_motion": {
                "early_0_30": spec["start"],
                "middle_30_70": spec["middle"],
                "late_70_100": spec["end"],
            },
            "moving_anchor_context": {
                "start_has_motion_before_and_after": True,
                "start_source": "Approved moving boundary from the preceding take, or an owner-approved opening anchor with explicit entry motion.",
                "end_has_motion_before_and_after": True,
                "end_source": "Generated moving boundary that hands body, effect and camera velocity to the next take or active final cut.",
            },
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
        },
    }


def prompt_for(spec: dict[str, object]) -> str:
    return (
        "Create one uninterrupted 10.083333-second photorealistic live-action 16:9 cinematic take. "
        f"{GLOBAL_STYLE} Camera: {spec['camera']} Foreground: {spec['foreground']} "
        f"Midground: {spec['midground']} Background: {spec['background']} "
        f"Timeline 0-30%: {spec['start']} Timeline 30-70%: {spec['middle']} Timeline 70-100%: {spec['end']} "
        f"Reaction: {spec['reaction']} Preserve accumulated damage: {spec['damage_after']} "
        "Keep useful subject, environment, effects and camera motion through the final frame. "
        f"Forbidden: {'; '.join(GLOBAL_FORBIDDEN)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-candidate", type=Path, required=True)
    args = parser.parse_args()
    anchor_source = args.anchor_candidate.resolve()

    if PROJECT.exists():
        raise SystemExit(f"Projeto ja existe; nenhuma sobrescrita foi feita: {PROJECT}")
    if not anchor_source.is_file():
        raise FileNotFoundError(anchor_source)
    if not GOHAN_REFERENCE.is_file():
        raise FileNotFoundError(GOHAN_REFERENCE)

    for directory in ("audio", "deliveries", "edit", "input", "keyframes", "logs", "output", "prompts", "qc", "refs", "takes"):
        (PROJECT / directory).mkdir(parents=True, exist_ok=True)

    anchor_target = PROJECT / "keyframes" / "anchor_00_candidate.png"
    identity_target = PROJECT / "refs" / "gohan_ssj2_identity_reference_approved.png"
    shutil.copy2(anchor_source, anchor_target)
    shutil.copy2(GOHAN_REFERENCE, identity_target)
    created_at = now()

    write_json(PROJECT / "keyframes" / "anchor_00_candidate.json", {
        "asset_id": "anchor_00_candidate",
        "role": "sequence_opening_anchor_candidate",
        "image_file": str(anchor_target.resolve()),
        "sha256": sha256(anchor_target),
        "generator": "OpenAI built-in image generation",
        "generated_at": created_at,
        "status": "PENDING_OWNER_REVIEW",
        "render_authorized": False,
        "visual_qc": {
            "expected_characters": ["Gohan Super Saiyajin", "Perfect Cell", "cabeca mecanica do Android 16"],
            "no_gore_required": True,
            "cell_foot_contact": False,
        },
    })
    write_json(PROJECT / "refs" / "gohan_ssj2_identity_reference_approved.json", {
        "source_project": GOHAN_SOURCE_PROJECT.name,
        "source_file": str(GOHAN_REFERENCE.resolve()),
        "copied_file": str(identity_target.resolve()),
        "sha256": sha256(identity_target),
        "status": "APPROVED_IDENTITY_REFERENCE_ONLY",
        "restriction": "Nao e uma ancora de cena; usar somente rosto, tratamento live action, cabelo SSJ2 e tecido roxo de Gohan.",
    })

    takes = []
    queue_takes = []
    for index, spec in enumerate(TAKES):
        take_id = str(spec["id"])
        prompt = prompt_for(spec)
        (PROJECT / "prompts" / f"{take_id}.md").write_text(
            f"# {take_id} - {spec['title']}\n\n{prompt}\n", encoding="utf-8"
        )
        start_anchor = f"keyframes/anchor_{index:02d}.png"
        end_anchor = f"keyframes/anchor_{index + 1:02d}.png"
        if index == 0:
            start_anchor = "keyframes/anchor_00_candidate.png"
        contract = transition_contract(spec)
        shot_contract = {
            "story_purpose": spec["purpose"],
            "dramatic_question": spec["question"],
            "story_change": f"{spec['start']} -> {spec['end']}",
            "reaction": spec["reaction"],
            "cut_motivation": spec["cut"],
            "duration_reason": "Dez segundos comportam ao menos tres eventos novos, uma reacao legivel, camera fisica e mudanca irreversivel de personagem ou ambiente.",
            "distinct_story_events": spec["events"],
            "motion_beats": {"start": spec["start"], "middle": spec["middle"], "end": spec["end"]},
            "environment_state_before": spec["damage_before"],
            "environment_state_after": spec["damage_after"],
            "environment_damage": spec["damage_after"],
            "escalation_level": spec["level"],
            "scale_evidence": {
                "foreground": spec["foreground"],
                "midground": spec["midground"],
                "background": spec["background"],
            },
            "visual_references": {
                "gohan_identity": "refs/gohan_ssj2_identity_reference_approved.png",
                "start_frame_file": start_anchor,
                "start_frame_approved": False,
                "end_frame_file": end_anchor,
                "end_frame_approved": False,
            },
            "negative_rules": GLOBAL_FORBIDDEN,
            "transition_motion_contract": contract,
        }
        take = {
            "id": take_id,
            "slug": spec["slug"],
            "title": spec["title"],
            "role": "canonical_live_action_story_take_10s",
            "is_transition": True,
            "timeline": {
                "editorial_start_seconds": index * 10,
                "editorial_end_seconds": (index + 1) * 10,
                "editorial_duration_seconds": 10.0,
                "native_generation_duration_seconds": 10.083333,
            },
            "generation": {
                "engine": ENGINE,
                "profile": PROFILE,
                "width": 1280,
                "height": 720,
                "fps": 24,
                "frames": 243,
                "steps": 20,
                "guidance": 1.0,
                "start_end_frame_enabled": True,
                "require_approved_start_frame": True,
                "require_approved_end_frame": True,
                "render_authorized": False,
                "visual_only_pass": True,
                "native_audio_authorized": False,
                "prompt": prompt,
            },
            "shot_contract": shot_contract,
            "transition_motion_contract": contract,
            "transition": {
                "is_transition": True,
                "connects_from": "previous active-motion boundary" if index else "owner-approved opening anchor with entry motion",
                "connects_to": "next active-motion boundary" if index < len(TAKES) - 1 else "active 60-second hard cut",
            },
            "qc": {
                "status": "WAITING_APPROVED_ANCHORS",
                "human_visual_approval": "pending",
                "transition_motion_gate": {"status": "pending_generation"},
                "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK",
            },
        }
        takes.append(take)
        queue_takes.append({
            "id": take_id,
            "slug": spec["slug"],
            "title": spec["title"],
            "status": "WAITING_APPROVED_ANCHORS",
            "maestro_status": "PLANNED",
            "render_authorized": False,
            "target_duration_seconds": 10.0,
            "native_duration_seconds": 10.083333,
            "animation_prompt": prompt,
            "base_image": {
                "file": start_anchor,
                "status": "waiting_owner_qc" if index == 0 else "waiting_anchor_generation",
            },
            "end_image": {"file": end_anchor, "status": "waiting_anchor_generation"},
            "video_generation": take["generation"],
            "shot_contract": shot_contract,
            "qc": take["qc"],
            "audio_direction": {
                "strategy": "model_independent_foley_after_picture_lock",
                "status": "BLOCKED_UNTIL_PICTURE_LOCK",
                "dialogue_generation_authorized": False,
                "human_listening_required": True,
            },
        })

    continuous_action_contract = {
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
    transition_gate = {
        "required": True,
        "policy_version": "2.0",
        "pillars": ["evident_camera", "real_depth", "internal_action", "clear_progression"],
    }
    official_sources = [
        {
            "title": "The Story of Dragon Ball in 42 Panels - Part Three",
            "url": "https://en.dragon-ball-official.com/news/01_3878.html",
            "used_for": "ordem: destruicao do Android 16, despertar SSJ2, Cell Juniors e confronto com Cell",
        },
        {
            "title": "Weekly Character Showcase 40: Android 16",
            "url": "https://en.dragon-ball-official.com/news/01_839.html",
            "used_for": "natureza mecanica, personalidade pacifica, ultimas palavras e execucao por Cell",
        },
        {
            "title": "Toei Animation Dragon Ball Z episode 185",
            "url": "https://lineup.toei-anim.co.jp/ja/tv/dragonz/episode/185/",
            "used_for": "superioridade de Gohan SSJ2 e eliminacao dos Cell Juniors",
        },
    ]
    production = {
        "schema_version": "gohan_ssj2_android16_cell_6x10s_production_v1",
        "project_id": PROJECT.name,
        "sequence_id": "android16_execution_to_gohan_cell_dominance",
        "role": "canonical_live_action_fight_sequence",
        "status": "WAITING_OWNER_ANCHOR_00_REVIEW",
        "render_authorized": False,
        "updated_at": created_at,
        "sequence_stakes": "Gohan precisa aceitar a luta para impedir que Cell destrua seus amigos e a vida que o Android 16 queria proteger.",
        "editorial_target_seconds": 60.0,
        "native_source_seconds": 60.499998,
        "picture_lock_rule": "Apos QC humano, remover apenas os tres quadros excedentes de cada take para fechar 6x10.000 s; sem crossfade ou cauda estatica.",
        "global_style": GLOBAL_STYLE,
        "global_forbidden": GLOBAL_FORBIDDEN,
        "official_fidelity_sources": official_sources,
        "universal_transition_motion_gate": transition_gate,
        "continuous_action_contract": continuous_action_contract,
        "takes": takes,
    }
    queue = {
        "schema_version": "gohan_ssj2_android16_cell_6x10s_queue_v1",
        "project_id": PROJECT.name,
        "status": "WAITING_OWNER_ANCHOR_00_REVIEW",
        "updated_at": created_at,
        "render_authorized": False,
        "methodology": "six_minimax_h3_primary_10s_first_last_human_qc_serial_then_exact_60s_edit",
        "continuous_action_contract": continuous_action_contract,
        "gpu_policy": {
            "serial_only": True,
            "max_concurrent_video_jobs": 1,
            "verify_comfy_queue_vram_and_process_ownership_before_each_take": True,
            "silent_model_or_software_encoder_fallback_forbidden": True,
        },
        "anchor_policy": {
            "owner_approval_required": True,
            "opening_candidate": "keyframes/anchor_00_candidate.png",
            "shared_boundary_anchors_required": True,
            "identity_reference_is_not_scene_approval": True,
        },
        "audio_policy": {
            "status": "BLOCKED_UNTIL_PICTURE_LOCK",
            "dialogue_generation_authorized": False,
            "foley_engine_after_picture_lock": "Tencent HunyuanVideo-Foley XXL",
            "human_listening_required": True,
        },
        "takes": queue_takes,
    }
    project = {
        "schema_version": "1.0",
        "project_id": PROJECT.name,
        "title": "Gohan SSJ2 - Android 16 e Cell - live action cinematografico 60s",
        "objective": "Recriar em live action a execucao mecanica do Android 16, o despertar SSJ2 de Gohan e sua primeira dominacao sobre Cell, fiel a ordem canonica e sem gore.",
        "duration_target_seconds": 60.0,
        "aspect_ratio": "16:9",
        "preview_resolution": "1280x720",
        "final_resolution": "1920x1080",
        "fps_preview": 24,
        "fps_final": 60,
        "created_at": created_at,
        "updated_at": created_at,
        "maestro_status": "WAITING_OWNER_ANCHOR_00_REVIEW",
        "render_authorized": False,
        "render_authority": "owner approval per anchor and take in Maestro",
        "take_queue": "take_queue.json",
        "production_manifest": "production_manifest.json",
        "opening_anchor_candidate": "keyframes/anchor_00_candidate.png",
        "continuity_reference": "refs/gohan_ssj2_identity_reference_approved.png",
        "rollback": {
            "source_project_preserved": str(GOHAN_SOURCE_PROJECT.resolve()),
            "replacement_forbidden_until_owner_final_approval": True,
        },
    }
    write_json(PROJECT / "project_manifest.json", project)
    write_json(PROJECT / "production_manifest.json", production)
    write_json(PROJECT / "take_queue.json", queue)
    (PROJECT / "STATUS.md").write_text(
        "# Status\n\n"
        "- Projeto: `gohan_ssj2_android16_cell_6x10s_liveaction_v1`\n"
        "- Alvo editorial: 60 s exatos, 16:9, 6 microtakes de 10 s.\n"
        "- Estado: `WAITING_OWNER_ANCHOR_00_REVIEW`.\n"
        "- A ancora inicial e apenas candidata; nenhum render de video esta autorizado.\n"
        "- A identidade live action de Gohan foi copiada do projeto aprovado sem alterar o original.\n"
        "- Preflight em 2026-08-19: fila ComfyUI vazia, mas RTX 5090 com apenas cerca de 345 MiB livres; revalidar fila, VRAM e processos antes de qualquer inferencia.\n"
        "- Foley, dialogo, musica, upscale e montagem permanecem bloqueados ate picture lock e QC humano.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "project_id": PROJECT.name,
        "takes": len(takes),
        "editorial_seconds": 60,
        "opening_anchor": str(anchor_target.resolve()),
        "status": "WAITING_OWNER_ANCHOR_00_REVIEW",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
