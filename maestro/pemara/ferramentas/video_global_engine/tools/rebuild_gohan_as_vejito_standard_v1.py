from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


ENGINE = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine").resolve()
PROJECT_ID = "gohan_ssj2_android16_cell_6x10s_liveaction_v1"
PROJECT = (ENGINE / "projetos" / PROJECT_ID).resolve()
ARCHIVE_ROOT = (ENGINE / "archive" / "owner_rejected_routes").resolve()
CANONICAL = (ENGINE / "projetos" / "vejito_super_boo_3x10_continuo_liveaction_foley_v1").resolve()
ROUTE_ID = "GOHAN_SSJ2_CELL_VEJITO_STANDARD_LIVEACTION_R1"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_inside(path: Path, parent: Path) -> None:
    path.relative_to(parent)


def take(
    take_id: str,
    slug: str,
    title: str,
    start: float,
    end: float,
    anchor_a: str,
    anchor_b: str,
    purpose: str,
    change: str,
    reaction: str,
    cut: str,
    duration_reason: str,
    early: str,
    middle: str,
    late: str,
    prompt: str,
) -> dict:
    return {
        "id": take_id,
        "slug": slug,
        "name": title,
        "title": title,
        "sequence": int(take_id),
        "timeline_start_seconds": start,
        "timeline_end_seconds": end,
        "target_duration_seconds": end - start,
        "native_duration_seconds": 10.083333,
        "visual_route_id": ROUTE_ID,
        "status": "ANCHORS_PENDING_HUMAN_REVIEW",
        "maestro_status": "PLANNED",
        "render_authorized": False,
        "story_purpose": purpose,
        "story_change": change,
        "reaction": reaction,
        "cut_motivation": cut,
        "duration_reason": duration_reason,
        "distinct_story_events": 3,
        "motion_beats": {
            "early_0_30": early,
            "middle_30_70": middle,
            "late_70_100": late,
        },
        "base_image": {
            "status": "pending_generation",
            "file": f"base_images/{anchor_a}.png",
            "metadata": f"base_images/{anchor_a}.json",
        },
        "end_image": {
            "status": "pending_generation",
            "file": f"base_images/{anchor_b}.png",
            "metadata": f"base_images/{anchor_b}.json",
        },
        "animation_prompt": prompt,
        "video_generation": {
            "engine": "MiniMax H3 FL2VA pruned INT8 ConvRot",
            "profile": "minimax_h3_fl2va_int8_720p24",
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
        },
        "art_direction_gate": {
            "anchor_status": "PENDING",
            "human_anchor_review": "PENDING",
            "anchor_contact_sheet": "",
            "video_style_status": "PENDING",
            "forbidden_style_detected": "PENDING_REVIEW",
        },
        "release_gates": {
            "art_direction": "PENDING",
            "cinematic": "PENDING",
            "motion": "PENDING",
            "technical": "PENDING",
            "human": "PENDING",
            "video_contact_sheet": "",
        },
        "video": {"status": "pending_generation", "output_active": "", "output_preview": ""},
        "audio_direction": {
            "status": "BLOCKED_UNTIL_PICTURE_LOCK",
            "dialogue_and_foley_after_picture_lock": True,
        },
    }


def main() -> None:
    ensure_inside(PROJECT, ENGINE / "projetos")
    ensure_inside(ARCHIVE_ROOT, ENGINE / "archive")
    if not CANONICAL.is_dir():
        raise SystemExit(f"projeto canônico ausente: {CANONICAL}")
    if not PROJECT.is_dir():
        raise SystemExit(f"projeto atual ausente: {PROJECT}")

    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    archive = (ARCHIVE_ROOT / f"{PROJECT_ID}__rejected_regressive_v6__{stamp}").resolve()
    ensure_inside(archive, ARCHIVE_ROOT)
    if archive.exists():
        raise SystemExit(f"arquivo de rollback já existe: {archive}")

    rejection = {
        "decision": "REJECTED_BY_OWNER_ENTIRE_VISUAL_ROUTE",
        "decided_at": now.isoformat(),
        "reason": (
            "Regressão severa em continuidade, montagem, direção cinematográfica e direção de arte; "
            "Cell alterna de live action para aparência de animação. O proprietário ordenou descartar "
            "a rota ativa e reconstruir nos moldes canônicos do Vejito."
        ),
        "active_promotion_forbidden": True,
        "media_deleted": False,
        "replacement_scope": "mesma narrativa, rota visual e metodologia inteiramente novas",
    }
    write_json(PROJECT / "qc" / f"owner_rejection_entire_route_{stamp}.json", rejection)

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.move(str(PROJECT), str(archive))
    PROJECT.mkdir(parents=True, exist_ok=False)
    for folder in ("base_images", "keyframes", "takes/internal", "takes/approved", "qc", "docs", "output"):
        (PROJECT / folder).mkdir(parents=True, exist_ok=True)

    anchors = {
        "A": "boundary_A_android16_speech_cell_threat",
        "B": "boundary_B_mechanical_impact_gohan_rage_rising",
        "C": "boundary_C_ssj2_launch_to_cell_juniors",
        "D": "boundary_D_last_junior_falls_gohan_redirects_to_cell",
        "E": "boundary_E_cell_energy_slap_deflection",
        "F": "boundary_F_cell_launched_gohan_pursuit",
        "G": "boundary_G_kamehameha_mountain_impact",
    }
    takes = [
        take(
            "01", "android16_cell_crush_rage", "01 — Android 16, impacto mecânico e raiva",
            0.0, 10.0, anchors["A"], anchors["B"],
            "Encerrar a fala de Android 16, tornar a ameaça de Cell irreversível e quebrar o autocontrole de Gohan.",
            "A cabeça mecânica intacta e Gohan contido tornam-se destroços mecânicos e energia emocional fora de controle.",
            "Gohan avança tarde demais, trava por um instante com o choque e responde fazendo a arena começar a se romper.",
            "Cortar enquanto pedras, aura, cabelo, roupa e câmera ainda sobem, entregando a transformação ao Take 02.",
            "Dez segundos comportam a última fala visual, a ação física de Cell, o impacto e a reação crescente sem repetição.",
            "Android 16 termina um movimento curto de boca; Gohan já avança e Cell transfere peso enquanto a câmera baixa percorre cascalho.",
            "Cell executa uma única pisada sobre a cabeça puramente mecânica; peças e poeira explodem em profundidades diferentes, sem gore.",
            "Gohan absorve o choque e a energia cresce violentamente; o chão racha e a câmera eleva sem ninguém parar.",
            "One uninterrupted photorealistic live-action 10.083333-second shot. Continue physical camera travel and character motion through Android 16's last mouth movement, one irreversible mechanical head crush by completely tailless Perfect Cell, and Gohan's escalating rage. End before stillness with Gohan, debris, dust, clothing and camera all rising into the transformation handoff. Physical materials only; no animation, cel shading, game render, plastic CGI, gore, tail, internal cut, zoom-only movement or static tail.",
        ),
        take(
            "02", "gohan_ssj2_transformation_launch", "02 — Transformação SSJ2 e arrancada",
            10.0, 20.0, anchors["B"], anchors["C"],
            "Converter a perda de Android 16 na transformação SSJ2 e numa decisão física imediata.",
            "Gohan ainda contido torna-se SSJ2 e cruza a arena em direção aos Cell Juniors.",
            "Cell recua e os Cell Juniors se armam para interceptar; Gohan não posa, ele ataca.",
            "Cortar na arrancada lateral com Gohan, relâmpagos, pedras e câmera compartilhando o vetor do Take 03.",
            "A transformação, a reação adversária e a arrancada são três eventos distintos que justificam dez segundos.",
            "A energia herdada cresce, o cabelo e a roupa respondem e a câmera faz uma órbita física curta em torno de Gohan.",
            "Gohan completa SSJ2; relâmpagos azul-brancos racham o ar e o terreno se rompe em três planos enquanto Cell reage.",
            "Sem sustentar pose, Gohan some num arranque legível rumo aos Cell Juniors e a câmera o persegue rente ao chão.",
            "One uninterrupted photorealistic live-action 10.083333-second transformation-and-launch shot. Inherit rising rage, rock velocity and crane motion. Gohan irreversibly becomes Super Saiyan 2 with physically lit golden hair, cloth, skin and blue-white electrical arcs, then immediately launches toward compact blue Cell Juniors while tailless Perfect Cell reacts. End in fast lateral pursuit motion. No animation, cel shading, game render, plastic CGI, pose hold, internal cut, extra fighters or tail.",
        ),
        take(
            "03", "ssj2_cell_juniors_directional_combo", "03 — Cell Juniors: combo direcional",
            20.0, 30.0, anchors["C"], anchors["D"],
            "Demonstrar a mudança absoluta de poder eliminando a ameaça dos Cell Juniors com velocidade e geografia legíveis.",
            "Vários Cell Juniors cercam Gohan; ao final, o último cai e Gohan já redireciona o corpo para Cell.",
            "Os Juniors tentam ataques coordenados; Gohan responde com golpes únicos, secos e progressivos, sem turnos ou congelamento.",
            "Cortar quando Gohan abandona o último impacto ainda em deslocamento para interceptar Cell.",
            "Dez segundos permitem três encontros diferentes e escalada ambiental sem repetir o mesmo golpe.",
            "Gohan herda o arranque, atravessa a primeira interceptação e arremessa um Junior para fora do eixo enquanto a câmera o acompanha.",
            "Ele encadeia dois contra-ataques em pontos distintos da arena; rochas quebram e os Juniors compactos permanecem claramente azuis, não clones verdes.",
            "O último Junior é derrubado sem gore e Gohan usa o próprio giro do golpe para acelerar em direção a Cell.",
            "One uninterrupted photorealistic live-action 10.083333-second directional combat shot. Start with the inherited SSJ2 chase. Gohan crosses real distance and defeats compact child-sized cyan-blue Cell Juniors through three distinct impacts while the camera physically tracks and orbits through a progressively damaged arena. End with the last Junior falling and Gohan redirecting toward full-size completely tailless green Perfect Cell. No full-size green clones, no animated look, no cel shading, no gore, no repeated attack, no turn-based pauses, no internal cut or static tail.",
        ),
        take(
            "04", "cell_energy_slap_and_counter", "04 — Gohan rebate a energia e contra-ataca",
            30.0, 40.0, anchors["D"], anchors["E"],
            "Fazer Cell tentar recuperar controle e mostrar Gohan anulando o ataque com desprezo físico antes do contra-ataque.",
            "Cell dispara energia contra Gohan; Gohan a desvia com um tapa simples e termina pressionando Cell corpo a corpo.",
            "Cell se surpreende com a inutilidade do ataque e tenta golpear; Gohan entra por dentro da guarda.",
            "Cortar no impacto que desloca Cell e mantém ambos, detritos e câmera atravessando a arena.",
            "O disparo, o tapa e a entrada no corpo a corpo formam uma progressão completa de dez segundos.",
            "Gohan chega do Take 03; Cell lança uma esfera/onda compacta sem parar o próprio movimento e a câmera cruza lateralmente.",
            "A energia passa ao alcance da mão e Gohan a rebate para longe com um único tapa simples; a explosão ocorre no fundo e altera o cenário.",
            "Gohan fecha a distância e aplica golpes pesados curtos, encerrando com Cell ainda sendo deslocado.",
            "One uninterrupted photorealistic live-action 10.083333-second counterattack shot. Inherit Gohan's redirect toward full-size tailless Perfect Cell. Cell fires one compact energy attack; Gohan deflects it away with one simple open-hand slap, never allowing it to pass through his body. The blast destroys distant terrain while Gohan immediately closes distance and drives Cell backward with heavy physical strikes. End with both bodies, debris and camera still translating. No animation, cel shading, game render, plastic CGI, magic passing through Gohan, tail, internal cut, slow posing or static tail.",
        ),
        take(
            "05", "gohan_dominates_cell_frenetic_exchange", "05 — Trocação frenética: Gohan domina Cell",
            40.0, 50.0, anchors["E"], anchors["F"],
            "Entregar a trocação principal com peso, velocidade e domínio crescente de Gohan.",
            "Uma tentativa de reação de Cell vira uma sequência de pressão que o lança para longe.",
            "Cell bloqueia e tenta contra-atacar; Gohan lê o movimento, quebra a defesa e o persegue antes que ele se recomponha.",
            "Cortar durante o voo de Cell com Gohan e a câmera já em perseguição para o Take 06.",
            "Dez segundos comportam contra-ataque, quebra de defesa e lançamento sem alongar ciclos de socos.",
            "Cell herda o deslocamento e tenta um contra; Gohan intercepta em câmera física de órbita curta.",
            "Três golpes distintos mudam altura, direção e dano do terreno; Cell perde espaço a cada impacto.",
            "Gohan aplica o golpe de lançamento; Cell cruza o vale e Gohan parte atrás dele sem pausa.",
            "One uninterrupted photorealistic live-action 10.083333-second high-speed melee shot. Continue the inherited body and camera vectors. Completely tailless Perfect Cell attempts a real counter; SSJ2 Gohan intercepts, breaks the guard with three distinct heavy impacts across changing height and direction, then launches Cell across the valley and pursues immediately. Physical camera orbit and chase, foreground rocks, midground fighters and distant terrain move at different speeds. No animation, cel shading, game render, plastic CGI, repeated punch loop, turn-based pause, tail, internal cut or static tail.",
        ),
        take(
            "06", "heavy_finish_kamehameha_mountain", "06 — Golpes finais e Kamehameha na montanha",
            50.0, 60.0, anchors["F"], anchors["G"],
            "Concluir a dominação com golpes mais fortes, lançamento e um Kamehameha que enterra Cell na montanha.",
            "Cell ainda voa e tenta estabilizar; termina soterrado pelo impacto do feixe numa montanha rompida.",
            "Cell tenta frear no ar; Gohan o alcança, golpeia e converte o impulso final diretamente no disparo.",
            "Encerrar no impacto em expansão, com montanha, rochas, poeira, aura e câmera ainda em movimento.",
            "Dez segundos acomodam perseguição, golpe de redirecionamento, disparo e consequência ambiental irreversível.",
            "Gohan alcança Cell ainda em voo e aplica dois impactos crescentes enquanto a câmera persegue em profundidade.",
            "O último golpe joga Cell para a montanha; Gohan freia apenas o necessário e reúne energia sem pose sustentada.",
            "Gohan dispara um Kamehameha poderoso que carrega Cell até a montanha, rompe a encosta e termina em explosão ativa.",
            "One uninterrupted photorealistic live-action 10.083333-second finishing shot. Inherit airborne Cell and pursuit velocity. SSJ2 Gohan catches full-size completely tailless Perfect Cell, lands two escalating impacts, throws him toward a mountain and converts the same momentum into an immediate powerful blue-white Kamehameha. The beam carries Cell into the mountain and ruptures the rock face while debris, dust, aura and camera remain moving through the final frame. No animation, cel shading, game render, plastic CGI, tail, pause to pose, internal cut, gore or static aftermath.",
        ),
    ]

    canonical_artifacts = [
        str(CANONICAL / "STATUS.md"),
        str(CANONICAL / "production_manifest.json"),
        str(CANONICAL / "take_queue.json"),
        str(CANONICAL / "qc" / "final_master_boundary_contact_12frames_v1.jpg"),
        str(CANONICAL / "output" / "vejito_vs_super_boo_final_36s_1080p60_foley_approved_v1.mp4"),
    ]
    production = {
        "schema_version": "2.0",
        "project_id": PROJECT_ID,
        "title": "GOHAN SSJ2 — RECONSTRUÇÃO CANÔNICA PADRÃO VEJITO",
        "methodology": "six_main_10s_takes_shared_moving_boundaries_internal_microsegments_owner_approval_per_take",
        "status": "CONTRACT_READY_ANCHORS_PENDING",
        "visual_route_id": ROUTE_ID,
        "canonical_reference": {
            "project_id": "vejito_super_boo_3x10_continuo_liveaction_foley_v1",
            "owner_declared_standard": True,
            "owner_reported_threads_performance": {
                "reported_at": now.isoformat(),
                "views_greater_than": 20500,
                "likes_approximately": 1000,
            },
            "audited_at": now.isoformat(),
            "audited_artifacts": canonical_artifacts,
            "inherit_method_not_assets": True,
        },
        "art_direction_bible": {
            "style_mode": "photorealistic_live_action",
            "production_level": "high_budget_cinematic_physical_creature_feature",
            "character_materials": {
                "gohan": "real teenage human skin and pores; dirty heavyweight purple cotton gi; individually resolved golden hair fibers; practical sweat and dust",
                "perfect_cell": "physical green-and-black chitinous bioarmor with pores, fine scratches, layered keratin edges and restrained wet highlights; purple facial and abdominal tissue; never smooth plastic",
                "android16": "purely mechanical green composite head shell, red synthetic hair fibers, steel servos, ceramic teeth, wiring and dry dust; no flesh or blood",
                "cell_juniors": "compact child-sized cyan-blue chitinous bioarmor with black sections and physical insectoid texture; never full-size green Cell clones",
            },
            "character_anatomy": {
                "gohan": "one teenage Gohan, two arms, two legs, one head; SSJ2 hair and lightning only after transformation",
                "perfect_cell": "one tall full-size Perfect Cell with crown crest and wing plates; completely tailless with no stinger or rear appendage in every frame",
                "android16": "detached mechanical head only in the opening; crushed parts remain mechanical",
                "cell_juniors": "small compact blue/cyan Cell Juniors, visually distinct from full-size green Perfect Cell",
            },
            "environment": "one continuous destroyed Cell Games rocky basin under turbulent storm clouds; every impact leaves persistent trenches, broken ridges, displaced boulders and dust",
            "lens_language": "28-40 mm spherical cinema lenses; low physical dolly, orbit, crane and chase with readable geography; no zoom-only motion",
            "lighting": "storm daylight with hard directional sun breaks, warm mineral dust, practical gold SSJ2 aura and blue-white energy bounce on real surfaces",
            "palette": "charcoal storm sky, warm ochre stone, restrained green/black Cell, dirty purple Gohan gi, controlled gold aura and blue-white lightning",
            "forbidden_render_modes": [
                "anime", "cel_shading", "illustration", "game_render", "clean_plastic_cgi", "cosplay",
                "soap_opera_lighting", "flat_studio_light", "overprocessed_hdr", "watermark", "text",
            ],
            "sequence_contact_sheet_required": True,
            "cell_animation_appearance_auto_rejects_take": True,
        },
        "approval_policy": {
            "human_anchor_approval_required": True,
            "human_take_art_approval_required": True,
            "human_take_motion_approval_required": True,
            "human_final_playback_required": True,
            "auto_promote": False,
            "owner_rejection_auto_creates_same_scope_replacement": True,
        },
        "maestro_catalog_policy": {
            "visible_items": "main_takes_only",
            "internal_microsegments_visible": False,
            "rejected_route_visible": False,
        },
        "continuous_action_contract": {
            "shared_moving_boundaries_required": True,
            "use_internal_microsegments_when_complex": True,
            "crossfade_forbidden": True,
            "freeze_forbidden": True,
            "static_tail_forbidden": True,
            "motion_handoff_required": True,
            "full_duration_motion_required": True,
        },
        "audio_policy": {
            "mode": "dialogue_and_foley_after_picture_lock",
            "android16_dialogue_timing_deferred": True,
            "foley_per_take": True,
            "human_listening_required": True,
            "auto_attach": False,
        },
        "anchors": anchors,
        "takes": takes,
        "assembly": {
            "status": "BLOCKED_UNTIL_ALL_TAKES_OWNER_APPROVED",
            "mixed_visual_routes": False,
            "salvage_repair_used": False,
            "crossfade_frames": 0,
            "freeze_frames": 0,
            "static_hold_frames": 0,
            "all_sources_owner_approved": False,
            "interpolation": {"used_only_after_source_pass": True},
            "sources": [],
        },
        "rollback": {"rejected_route_archive": str(archive), "media_deleted": False},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    queue = {
        "schema_version": "2.0",
        "project_id": PROJECT_ID,
        "methodology": production["methodology"],
        "status": "ANCHOR_ART_DIRECTION_PENDING_OWNER_REVIEW",
        "visual_route_id": ROUTE_ID,
        "render_authorized": False,
        "story_batch_policy": {"enabled": False, "reason": "produção serial e aprovação humana por take"},
        "maestro_catalog_policy": production["maestro_catalog_policy"],
        "takes": takes,
        "updated_at": now.isoformat(),
    }
    project = {
        "schema_version": "2.0",
        "project_id": PROJECT_ID,
        "title": "GOHAN SSJ2 — PADRÃO CANÔNICO VEJITO — RECONSTRUÇÃO",
        "objective": "Recriar em live action físico e cinematográfico a perda de Android 16, transformação SSJ2 e domínio de Gohan sobre Cell.",
        "duration_target_seconds": 60.0,
        "aspect_ratio": "16:9",
        "preview_resolution": "1280x720",
        "final_resolution": "1920x1080",
        "fps_preview": 24,
        "fps_final": 60,
        "status": "ANCHOR_ART_DIRECTION_PENDING_OWNER_REVIEW",
        "maestro_status": "NEEDS_REVIEW",
        "render_authorized": False,
        "take_queue": "take_queue.json",
        "production_manifest": "production_manifest.json",
        "canonical_reference_project": "vejito_super_boo_3x10_continuo_liveaction_foley_v1",
        "visual_route_id": ROUTE_ID,
        "final_output": None,
        "rollback": {"rejected_route_archive": str(archive), "media_deleted": False},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    write_json(PROJECT / "production_manifest.json", production)
    write_json(PROJECT / "take_queue.json", queue)
    write_json(PROJECT / "project_manifest.json", project)
    write_json(PROJECT / "qc" / "route_rebuild_preflight.json", {
        "status": "READY_FOR_CONTRACT_GATE",
        "created_at": now.isoformat(),
        "canonical_project": str(CANONICAL),
        "rejected_route_archive": str(archive),
        "active_take_count": len(takes),
        "active_take_ids": [item["id"] for item in takes],
        "media_deleted": False,
    })
    (PROJECT / "FIXLOG.md").write_text(
        "# FIXLOG\n\n"
        f"## {now.isoformat()} — reconstrução integral no padrão canônico Vejito\n\n"
        "- Rota V6 reprovada pelo proprietário por regressão de continuidade e direção de arte.\n"
        "- Projeto anterior removido da produção ativa e preservado integralmente no arquivo de rollback.\n"
        "- Criada rota visual única live action, seis takes principais e sete fronteiras móveis.\n"
        "- Montagem de salvamento, mistura de rotas e promoção automática foram bloqueadas.\n"
        "- Vídeo permanece bloqueado até aprovação humana das novas âncoras.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "REBUILT",
        "project": str(PROJECT),
        "rejected_archive": str(archive),
        "active_takes": [item["id"] for item in takes],
        "video_generation_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
