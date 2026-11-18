from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "projetos" / "vejito_super_boo_ltx25_60s"
PROJECT = ROOT / "projetos" / "vejito_super_boo_minimax_h3_8x8s"
PROFILE = "minimax_h3_fl2va_int8_ltx_contract_720p24"
ENGINE = "MiniMax H3 FL2VA INT8 + Qwen3-VL-32B"
APPROVED_ANCHORS = set(range(0, 7))


TAKES = [
    {
        "id": "M01", "slug": "potara_sob_fogo", "title": "Potara sob fogo",
        "sources": ["T01", "T02"], "start": 0, "end": 2,
        "characters": ["Goku", "Vegeta", "Super Boo"],
        "purpose": "Converter a rivalidade em decisao e iniciar a fusao sob ataque real.",
        "question": "Goku e Vegeta conseguirao ativar os Potara antes de Boo interromper?",
        "start_state": "Goku revela os Potara; Vegeta ainda resiste enquanto Super Boo avanca entre rochas suspensas.",
        "middle": "Uma rajada rosa corta o espaco; Goku arremessa o brinco, Vegeta o intercepta e ambos encaixam os Potara sem parar.",
        "end_state": "A atracao dos brincos arranca os dois do solo e os comprime num nucleo branco-dourado enquanto Boo estica o braco para impedir.",
        "reaction": "Vegeta abandona a hesitacao; Boo perde o sorriso e reage tarde demais.",
        "camera": "Dolly lateral baixo entre destrocos, arco fisico de setenta graus e push-in diagonal que acompanha a convergencia.",
        "foreground": "Pedras, poeira e o braco elastico de Boo cruzam profundidades diferentes sem ocultar os rostos.",
        "background": "A cratera cresce e as nuvens se abrem em espiral na direcao do nucleo de fusao.",
        "cut": "Cortar no pico da convergencia, antes de revelar o corpo fundido.",
        "events": 4,
    },
    {
        "id": "M02", "slug": "nascimento_de_vegetto", "title": "Nascimento de Vegetto",
        "sources": ["T03"], "start": 2, "end": 3,
        "characters": ["Vegetto base", "Super Boo"],
        "purpose": "Revelar Vegetto em forma base e iniciar a luta no mesmo movimento.",
        "question": "A fusao produzira um guerreiro capaz de dominar o primeiro ataque?",
        "start_state": "O nucleo branco-dourado ainda contem silhuetas convergentes; Boo investe para atingir a fusao incompleta.",
        "middle": "Vegetto emerge com cabelo preto e dois Potara, bloqueia durante a propria formacao e captura o pulso de Boo.",
        "end_state": "Vegetto base completamente formado arrasta Boo pelo solo quebrado segurando o mesmo pulso, sem pose de apresentacao.",
        "reaction": "Boo perde o eixo e usa o corpo elastico para tentar recuperar equilibrio.",
        "camera": "Mergulho atraves do halo, handheld controlado no bloqueio e tracking rente ao solo durante o arrasto.",
        "foreground": "Aro de energia, tecido e cascalho passam pela lente em velocidades distintas.",
        "background": "O arrasto abre uma cicatriz continua no terreno e derruba formacoes rochosas.",
        "cut": "Cortar quando Boo transforma a queda em contra-ataque.",
        "events": 3,
    },
    {
        "id": "M03", "slug": "transformacao_super_saiyan", "title": "Vegetto vira Super Saiyan",
        "sources": ["T04"], "start": 3, "end": 4,
        "characters": ["Vegetto base", "Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Mostrar a transformacao completa durante combate, preservando os dois Potara.",
        "question": "Vegetto conseguira transformar a pressao de Boo em vantagem?",
        "start_state": "Vegetto base desliza segurando o pulso de Boo; cabelo preto e ambos os brincos estao visiveis.",
        "middle": "Boo martela o solo; Vegetto absorve o impacto, o cabelo se ergue gradualmente, fica dourado e a aura explode fisicamente.",
        "end_state": "Vegetto Super Saiyan completo rompe a onda de choque e contra-ataca, com cabelo dourado, olhos azul-esverdeados e dois Potara.",
        "reaction": "Boo recua pela primeira vez e protege o rosto contra o pulso dourado.",
        "camera": "Orbit curto fisico ao redor do impacto, recuo pela onda de choque e reentrada frontal junto ao contra-ataque.",
        "foreground": "Rochas racham, levantam e atravessam a lente; tecido e cabelo respondem com inercia diferente.",
        "background": "A onda dourada abre um corredor permanente nas nuvens e no relevo.",
        "cut": "Cortar no primeiro contato limpo de Vegetto Super Saiyan.",
        "events": 4,
    },
    {
        "id": "M04", "slug": "dominio_e_teleporte", "title": "Domínio e perseguição por teleporte",
        "sources": ["T05", "T06"], "start": 4, "end": 6,
        "characters": ["Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Estabelecer superioridade de Vegetto e converter um lancamento em perseguicao espacial continua.",
        "question": "Boo conseguira recuperar distancia depois de ser lancado?",
        "start_state": "Vegetto Super Saiyan entra por cima e atras de Boo com aura dourada e ambos os Potara.",
        "middle": "Boo usa um membro elastico para lancar Vegetto contra a rocha; Vegetto reaparece por teleporte antes do impacto e devolve Boo ao ar.",
        "end_state": "Vegetto surge acima da nova trajetoria de Boo e continua a perseguicao sem retornar a guarda.",
        "reaction": "Boo alterna surpresa e tentativa desesperada de localizar Vegetto em profundidade.",
        "camera": "Chicote fisico motivado pelo lancamento, passagem atras da formacao rochosa e crane ascendente que encontra o reaparecimento.",
        "foreground": "Membros elasticos, rocha rompida e detritos criam oclusoes breves, nunca um blackout de troca de corpo.",
        "background": "Cada impacto deixa uma cratera distinta e a trajetoria sobe para ilhas rochosas suspensas.",
        "cut": "Cortar quando Vegetto cruza acima de Boo para iniciar a reversao seguinte.",
        "events": 4,
    },
    {
        "id": "M05", "slug": "reversao_e_contra_ataque", "title": "Reversão e contra-ataque",
        "sources": ["T07", "T08"], "start": 6, "end": 8,
        "characters": ["Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Dar a Boo uma ameaca elastica real e fazer Vegetto supera-la por leitura e velocidade.",
        "question": "O corpo imprevisivel de Boo finalmente prende Vegetto?",
        "start_state": "Vegetto persegue Boo no ar; Boo gira o torso e prepara membros em vetores diferentes.",
        "middle": "Boo prende uma perna e um braco, tenta esmagar Vegetto entre rochas; Vegetto gira o quadril, rompe uma extensao e usa a outra como alavanca.",
        "end_state": "Vegetto escapa, inverte a tracao e arremessa Boo atraves de duas ilhas rochosas em sequencia irreversivel.",
        "reaction": "Boo percebe a inversao somente quando a propria extensao o puxa para o impacto.",
        "camera": "Travelling helicoidal curto ao redor da captura, descida junto a alavanca e aceleração lateral nos dois impactos.",
        "foreground": "Extensoes de Boo, lascas e fragmentos passam em planos independentes.",
        "background": "Duas ilhas colapsam em ordem e permanecem destruidas no quadro final.",
        "cut": "Cortar na saida de Boo do segundo impacto, ainda em movimento ascendente.",
        "events": 4,
    },
    {
        "id": "M06", "slug": "combate_aereo_e_lancamento", "title": "Combate aéreo e lançamento",
        "sources": ["T09", "T10"], "start": 8, "end": 10,
        "characters": ["Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Encerrar a troca fisica com vantagem decisiva e preparar organicamente o golpe final.",
        "question": "Vegetto conseguira criar a distancia exata para carregar o Kamehameha?",
        "start_state": "Boo sai do colapso girando; Vegetto entra no angulo cego entre ilhas suspensas.",
        "middle": "Vegetto combina joelho, desvio e golpe curto sem alternancia educada; Boo tenta estabilizar membros em direcoes opostas.",
        "end_state": "Boo e lancado ao alto em espiral irregular; Vegetto pousa numa ilha inclinada, desliza e abre a base de energia.",
        "reaction": "Vegetto acompanha a trajetoria antes de baixar o centro de gravidade; Boo falha em frear a espiral.",
        "camera": "Long lens lateral comprimida, passagem fisica entre ilhas e crane aberto que desce com Vegetto.",
        "foreground": "Ilhas e fragmentos giram fora de sincronia, revelando profundidade real.",
        "background": "A espiral de Boo sobe contra nuvens partidas e o corredor devastado dos impactos anteriores.",
        "cut": "Cortar quando as maos de Vegetto iniciam a primeira concentracao azul.",
        "events": 4,
    },
    {
        "id": "M07", "slug": "carga_kamehameha", "title": "Carga do Kamehameha",
        "sources": ["T11"], "start": 10, "end": 11,
        "characters": ["Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Construir o golpe final com transformacao ambiental e contra-ataque simultaneo.",
        "question": "Boo conseguira improvisar um contra-feixe antes da carga completa?",
        "start_state": "Vegetto desliza na ilha inclinada e abre a base; Boo ainda gira muito acima.",
        "middle": "A esfera azul cresce entre as maos, pedras levitam e as nuvens se afastam; Boo comprime energia rosa de forma instavel.",
        "end_state": "Os dois disparam de diagonais opostas; os feixes ainda nao se tocaram, mas iluminam todo o campo devastado.",
        "reaction": "Vegetto sustenta a base sob a pressao; Boo dispara cedo por medo de perder a janela.",
        "camera": "Push-in curvo nas maos, passagem entre pedras suspensas e corte de eixo motivado pela revelacao do contra-feixe.",
        "foreground": "Pedras, tecido, faiscas e ondas de pressao reagem independentemente.",
        "background": "Nuvens e ilhas sao empurradas para fora do corredor dos dois feixes.",
        "cut": "Cortar um instante antes da colisao para maximizar o impacto seguinte.",
        "events": 4,
    },
    {
        "id": "M08", "slug": "kamehameha_final", "title": "Kamehameha final",
        "sources": ["T12"], "start": 11, "end": 12,
        "characters": ["Vegetto Super Saiyan", "Super Boo"],
        "purpose": "Entregar um climax poderoso, legivel e irreversivel com consequencia visual.",
        "question": "O Kamehameha de Vegetto atravessara a resistencia de Boo?",
        "start_state": "Os feixes azul e rosa avancam de diagonais opostas, separados por poucos metros.",
        "middle": "Os feixes colidem; Vegetto avanca fisicamente, o azul comprime o rosa e Boo perde forma dentro da luz.",
        "end_state": "O Kamehameha atravessa o ceu e explode alem de Boo; Vegetto permanece exausto em silhueta diante de uma coluna azul irreversivel.",
        "reaction": "Vegetto baixa os bracos somente depois da explosao; o campo passa do caos ao silencio.",
        "camera": "Travelling lateral baixo junto ao feixe, corrida fisica ate a colisao, recuo violento e settle final atras de Vegetto.",
        "foreground": "Cascalho, tecido e ondas de choque atravessam planos diferentes.",
        "background": "Ceu, nuvens e ilhas ficam permanentemente afastados pela coluna luminosa.",
        "cut": "Encerrar na silhueta exausta e na consequencia ambiental, sem retorno a pose de luta.",
        "events": 4,
    },
]


GLOBAL_STYLE = (
    "Photorealistic live-action feature film with believable adult human performers and a physically convincing pink humanoid; "
    "natural skin pores, sweat, practical costume texture, cinematic lenses, realistic motion blur, weighted contact, asymmetric timing, "
    "premium physically based energy and destruction effects; never anime, animation, game render or plastic skin."
)
FORBIDDEN = [
    "no robotic pauses, symmetric choreography or polite turn-based attacks",
    "no repeated wind-up, repeated strike, rollback, pose reset or return to idle",
    "no simple zoom-only motion, living photo, camera reversal or static tail",
    "no teleport used to hide identity, costume, anatomy or body-count changes",
    "no duplicate fighter, extra character, text, logo, watermark or interface",
    "no missing Potara after fusion and no black hair after the Super Saiyan transformation",
]


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def anchor_name(index: int) -> str:
    return f"anchor_{index:02d}.png"


def main() -> None:
    if PROJECT.exists():
        raise SystemExit(f"Projeto ja existe; nenhuma sobrescrita foi feita: {PROJECT}")
    for directory in (
        "audio", "base_images", "deliveries", "edit", "input", "keyframes",
        "logs", "output", "prompts", "qc", "refs", "takes",
    ):
        (PROJECT / directory).mkdir(parents=True, exist_ok=True)

    old_project = read_json(SOURCE / "project_manifest.json")
    for index in APPROVED_ANCHORS:
        source = SOURCE / "keyframes" / anchor_name(index)
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, PROJECT / "keyframes" / source.name)

    created_at = timestamp()
    production_takes = []
    queue_takes = []
    for position, spec in enumerate(TAKES):
        start_name = anchor_name(spec["start"])
        end_name = anchor_name(spec["end"])
        start_exists = spec["start"] in APPROVED_ANCHORS
        end_exists = spec["end"] in APPROVED_ANCHORS
        start_rel = f"keyframes/{start_name}"
        end_rel = f"keyframes/{end_name}"
        start_abs = str((PROJECT / start_rel).resolve()) if start_exists else ""
        end_abs = str((PROJECT / end_rel).resolve()) if end_exists else ""
        progression = f'{spec["start_state"]} -> {spec["middle"]} -> {spec["end_state"]}'
        prompt = (
            "Create one continuous eight-second MiniMax H3 first/last-frame cinematic take using the exact approved boundary images. "
            f"{GLOBAL_STYLE} Camera: {spec['camera']} Foreground: {spec['foreground']} Background: {spec['background']} "
            f"Timeline 0-25%: {spec['start_state']} Timeline 25-70%: {spec['middle']} Timeline 70-100%: {spec['end_state']} "
            f"Reaction: {spec['reaction']} Preserve the materially changed end state without freezing the final second. "
            f"Forbidden: {'; '.join(FORBIDDEN)}."
        )
        (PROJECT / "prompts" / f"{spec['id']}.md").write_text(
            f"# {spec['id']} - {spec['title']}\n\n{prompt}\n", encoding="utf-8"
        )
        shot = {
            "story_purpose": spec["purpose"],
            "dramatic_question": spec["question"],
            "story_change": f'{spec["start_state"]} -> {spec["end_state"]}',
            "motion_beats": {
                "start": spec["start_state"], "middle": spec["middle"], "end": spec["end_state"],
            },
            "reaction": spec["reaction"],
            "cut_motivation": spec["cut"],
            "duration_reason": (
                "Eight seconds are justified by at least two distinct dramatic turns, a visible reaction, "
                "physical camera translation and an irreversible environment or character state change."
            ),
            "distinct_story_events": spec["events"],
            "camera": {"movement": spec["camera"], "physical_translation": True},
            "keyframes": {
                "start": start_rel, "end": end_rel,
                "approved": start_exists and end_exists,
                "approval_source": "approved anchors inherited from the owner-reviewed predecessor project",
            },
            "visual_references": {
                "start_frame_file": start_abs,
                "start_frame_approved": start_exists,
                "end_frame_file": end_abs,
                "end_frame_approved": end_exists,
                "shared_boundary_contract": "main take boundaries use approved story anchors",
            },
            "source_take_ids": spec["sources"],
            "forbidden": FORBIDDEN,
        }
        generation = {
            "engine": ENGINE,
            "profile": PROFILE,
            "workflow": "MiniMax H3 FL2VA approved first/last-frame, visual-only",
            "fps": 24,
            "frames": 192,
            "preview_resolution": "1280x720",
            "final_resolution_after_picture_lock": "1920x1080",
            "start_anchor": start_rel,
            "end_anchor": end_rel,
            "status": "WAITING_MINIMAX_H3_GENERATION" if start_exists and end_exists else "WAITING_APPROVED_ANCHORS",
            "render_authorized": False,
            "visual_only_pass": True,
            "native_audio_authorized": False,
            "prompt": prompt,
            "negative_prompt": ", ".join(FORBIDDEN),
        }
        transition = {
            "evident_camera": {"required": True, "movement": spec["camera"], "physical_translation": True},
            "real_depth": {
                "required": True, "foreground": spec["foreground"],
                "midground": progression, "background": spec["background"], "differential_motion": True,
            },
            "internal_action": {
                "required": True, "primary_event": spec["middle"],
                "independent_elements": ["body and costume follow-through", "debris and environment reaction"],
            },
            "clear_progression": {
                "required": True, "start": spec["start_state"], "middle": spec["middle"], "end": spec["end_state"],
            },
        }
        production_takes.append({
            "id": spec["id"], "slug": spec["slug"], "title": spec["title"],
            "role": "minimax_h3_primary_story_take_8s", "pilot": spec["id"] == "M01",
            "timeline": {"source_start_seconds": position * 8, "source_end_seconds": (position + 1) * 8, "duration_seconds": 8},
            "generation": generation, "shot_contract": shot,
            "transition_motion_contract": transition,
            "qc": {
                "status": "WAITING_MINIMAX_H3_GENERATION" if start_exists and end_exists else "WAITING_APPROVED_ANCHORS",
                "human_visual_approval": "pending", "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK",
            },
        })
        queue_takes.append({
            "id": spec["id"], "slug": spec["slug"], "title": spec["title"],
            "objective": spec["purpose"], "characters": spec["characters"],
            "status": "PLANNED", "maestro_status": "PLANNED", "pilot": spec["id"] == "M01",
            "target_duration_seconds": 8, "animation_prompt": prompt,
            "render_authorized": False,
            "video_generation": {
                "profile": PROFILE, "width": 1280, "height": 720, "fps": 24, "frames": 192,
                "steps": 20, "guidance": 1.0, "start_end_frame_enabled": True,
                "require_approved_end_frame": True, "maestro_job_enabled": True,
                "visual_only_pass": True, "native_audio_authorized": False,
            },
            "shot_contract": shot,
            "base_image": {
                "status": "approved_for_video" if start_exists else "waiting_anchor_human_qc",
                "file": start_abs,
                "model": "approved inherited story anchor" if start_exists else "",
                "source_project": SOURCE.name,
            },
            "maestro_director_requests": [],
            "qc": {
                "status": "waiting_minimax_h3_generation" if start_exists and end_exists else "waiting_anchor_human_qc",
                "human_anchor_approval": "approved_in_predecessor_project" if start_exists else "pending",
                "human_visual_approval": "pending", "audio_gate": "BLOCKED_UNTIL_PICTURE_LOCK",
            },
            "qc_status": "waiting_minimax_h3_generation" if start_exists and end_exists else "waiting_anchor_human_qc",
            "audio_direction": {
                "delivery_required": False, "strategy": "hunyuanvideo_foley_after_picture_lock",
                "status": "blocked_until_picture_lock",
            },
            "maestro_notes": (
                "Take principal MiniMax H3 de 8 s. Exige as duas ancoras aprovadas; "
                "audio e upscale permanecem bloqueados ate aprovacao visual."
            ),
        })

    project = copy.deepcopy(old_project)
    project.update({
        "schema_version": "vejito_super_boo_minimax_h3_8x8s_v1",
        "project_id": PROJECT.name,
        "title": "Vegetto x Super Boo - MiniMax H3 - 8 takes principais de 8s",
        "objective": "Produzir 64 s brutos em oito takes principais H3 e montar um filme final de 60 s sem caudas estaticas.",
        "duration_target_seconds": 60,
        "source_coverage_seconds": 64,
        "created_at": created_at, "updated_at": created_at,
        "status": "MINIMAX_H3_M01_READY_FOR_GENERATION", "maestro_status": "IN_PROGRESS",
        "render_authorized": False, "render_authority": "per_take_owner_qc_in_maestro",
        "render_scope": "",
        "video_generation": {
            "engine": ENGINE, "profile": PROFILE,
            "workflow_contract": "8 primary takes x 8 seconds; 192 frames at 24 fps; approved first/last anchors required.",
            "take_count": 8, "pilot_take": "M01", "source_duration_seconds": 64,
            "editorial_target_seconds": 60, "serial_gpu_only": True, "visual_only_pass": True,
            "native_audio_authorized": False, "silent_model_substitution_forbidden": True,
            "human_qc_each_take_required": True,
        },
        "rollback": {
            "source_project_preserved": str(SOURCE.resolve()),
            "replacement_forbidden_until_new_master_human_approval": True,
        },
        "pilot_result": {}, "take_review_candidates": [], "anchor_candidate_batches": [],
        "take_queue": "take_queue.json",
    })
    production = {
        "schema_version": "vejito_super_boo_minimax_h3_8x8s_production_v1",
        "project_id": PROJECT.name, "sequence_id": "potara_to_final_kamehameha_8x8s",
        "role": "primary_live_action_fight_sequence", "updated_at": created_at,
        "sequence_stakes": "Goku and Vegeta must fuse before Super Boo destroys the battlefield; Vegetto must end the threat.",
        "continuity_rule": "Irreversible damage and transformations carry forward; no pose, hair or Potara reset.",
        "global_style": GLOBAL_STYLE, "global_forbidden": FORBIDDEN,
        "universal_transition_motion_gate": ["evident_camera", "real_depth", "internal_action", "clear_progression"],
        "source_coverage_seconds": 64, "editorial_target_seconds": 60,
        "takes": production_takes,
        "character_continuity": project["character_continuity"],
    }
    queue = {
        "schema_version": "vejito_super_boo_minimax_h3_8x8s_queue_v1",
        "project_id": PROJECT.name,
        "status": "MINIMAX_H3_M01_READY_FOR_GENERATION", "updated_at": created_at,
        "render_authorized": False,
        "methodology": "eight_minimax_h3_primary_8s_first_last_human_qc_serial_then_60s_edit",
        "gpu_policy": {
            "serial_only": True, "max_concurrent_video_jobs": 1,
            "verify_queue_before_each_take": True, "silent_fallback_forbidden": True,
        },
        "audio_policy": {
            "status": "BLOCKED_UNTIL_PICTURE_LOCK", "native_h3_audio_authorized": False,
            "foley_engine_after_picture_lock": "Tencent HunyuanVideo-Foley XXL",
        },
        "anchor_generation_policy": {
            "required": True, "first_last_frame_required": True,
            "approved_boundary_reuse": True, "missing_anchors_generated_and_reviewed_in_maestro": True,
        },
        "takes": queue_takes,
    }
    write_json(PROJECT / "project_manifest.json", project)
    write_json(PROJECT / "production_manifest.json", production)
    write_json(PROJECT / "take_queue.json", queue)
    (PROJECT / "FIXLOG.md").write_text(
        "# FIXLOG\n\n## 2026-08-15 - Projeto H3 8x8s criado\n\n"
        "- Oito takes principais de 8 s, 192 quadros a 24 fps, total bruto de 64 s e alvo editorial de 60 s.\n"
        "- LTX proibido; MiniMax H3 visual-only, GPU serial, duas ancoras aprovadas e QC humano por take.\n"
        "- M01-M04 possuem as duas ancoras herdadas; M05-M08 permanecem bloqueados ate as ancoras faltantes.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "project_id": PROJECT.name, "takes": 8, "frames_per_take": 192,
        "seconds_per_take": 8, "source_seconds": 64, "editorial_target_seconds": 60,
        "two_anchor_ready": [item["id"] for item in queue_takes if item["shot_contract"]["visual_references"]["end_frame_approved"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
