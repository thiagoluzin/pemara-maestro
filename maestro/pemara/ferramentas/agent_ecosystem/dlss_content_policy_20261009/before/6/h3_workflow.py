"""Canonical MiniMax H3 production workflow exposed by Maestro Studio.

This module is intentionally read-only.  It inventories the installed local
stack and describes the gates that must be satisfied, but it never starts a
GPU job or approves a human-review candidate.
"""

from __future__ import annotations

from pathlib import Path
import configparser
import os
import re
from typing import Any

from h3_prompt_writing import official_skill_integrity
from live_action_workflows import workflow_pack_status as live_action_pack_status
from h3_face_refine import policy as face_refine_policy
from h3_acceleration import (SAMPLING_CONSUMERS, prepare_spectrum, ensure_spectrum,
                             validate_spectrum, SPECTRUM_NODE)


WORKFLOW_VERSION = "maestro-minimax-h3-sage-spectrum-required@2026-10-04"
ENGINE_POLICY = "minimax_h3_only"

H3_FL2VA_MODEL_NAME = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
H3_REF2VA_MODEL_NAME = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
FAST_H3_MODEL_NAME = "fastvideo_fasth3_8step_v2_pruned_int8_convrot.safetensors"
FAST_H3_VARIANT = "fasth3_8step_v2"
FAST_H3_STEPS = 8
DEFAULT_H3_QUALITY_PROFILE = "h3_production"
H3_SAGE_ATTENTION_NODE = "MiniMaxH3MemoryEfficientSageAttentionPatch"
FAST_H3_EXPECTED_BYTES = 22_128_378_696

# The legacy 720p profile remains resolvable for persisted jobs. New requests
# use Production, whose dimensions and sampling budget are explicit.
H3_QUALITY_PROFILES: dict[str, dict[str, Any]] = {
    "h3_draft": {"label": "H3 Draft", "width": 1024, "height": 576, "verticalWidth": 576, "verticalHeight": 1024, "steps": (6,), "nativeAudio": False, "draftOnly": True},
    "h3_production": {"label": "H3 Production", "width": 1088, "height": 608, "verticalWidth": 608, "verticalHeight": 1088, "steps": (10,), "nativeAudio": False},
    "h3_hero": {"label": "H3 Hero", "width": 1344, "height": 768, "verticalWidth": 768, "verticalHeight": 1344, "steps": (12, 13, 14), "nativeAudio": False},
    "h3_master": {"label": "H3 Master", "width": 1344, "height": 768, "verticalWidth": 768, "verticalHeight": 1344, "steps": (20,), "nativeAudio": False},
    "h3_master_fbc20": {"label": "H3 Master (ID antigo FBC; Sage + Spectrum)", "width": 1344, "height": 768, "verticalWidth": 768, "verticalHeight": 1344, "steps": (20,), "nativeAudio": False, "legacy": True, "acceleration": "sage_spectrum_required"},
    "h3_master_spectrum20": {"label": "H3 Master (ID antigo Spectrum)", "width": 1344, "height": 768, "verticalWidth": 768, "verticalHeight": 1344, "steps": (20,), "nativeAudio": False, "legacy": True, "acceleration": "sage_spectrum_required"},
    "h3_legacy_720p": {"label": "H3 Legacy 720p", "width": 1280, "height": 720, "verticalWidth": 720, "verticalHeight": 1280, "steps": (20,), "nativeAudio": False, "legacy": True},
    "h3_approved_action_720p8s": {"label": "H3 Approved Action 720p 8s", "width": 1280, "height": 720, "verticalWidth": 720, "verticalHeight": 1280, "steps": (20,), "nativeAudio": False},
}


def resolve_h3_quality_profile(profile_id: str = "", *, width: int | None = None, height: int | None = None, steps: int | None = None, model_variant: str = "") -> tuple[str, dict[str, Any], bool]:
    """Resolve an explicit profile, preserving stored 720p jobs when absent."""
    profile_id = str(profile_id or "").strip().lower()
    explicit_profile = bool(profile_id)
    matched_existing_geometry = False
    if profile_id:
        if profile_id not in H3_QUALITY_PROFILES:
            raise ValueError("Perfil H3 invalido. Use Draft, Production, Hero ou Master.")
        profile = H3_QUALITY_PROFILES[profile_id]
    else:
        profile_id, profile = DEFAULT_H3_QUALITY_PROFILE, H3_QUALITY_PROFILES[DEFAULT_H3_QUALITY_PROFILE]
        for candidate_id, candidate in H3_QUALITY_PROFILES.items():
            geometries = {(candidate["width"], candidate["height"]), (candidate["verticalWidth"], candidate["verticalHeight"])}
            if width is not None and height is not None and (int(width), int(height)) in geometries and (steps is None or int(steps) in candidate["steps"]):
                profile_id, profile = candidate_id, candidate
                matched_existing_geometry = True
                break
    vertical = width is not None and height is not None and (int(width), int(height)) == (profile["verticalWidth"], profile["verticalHeight"])
    allowed_steps = (FAST_H3_STEPS,) if str(model_variant or "").strip().lower() == FAST_H3_VARIANT else profile["steps"]
    if steps is not None and int(steps) not in allowed_steps and (explicit_profile or matched_existing_geometry):
        allowed = "-".join(map(str, (min(profile["steps"]), max(profile["steps"]))))
        if str(model_variant or "").strip().lower() == FAST_H3_VARIANT:
            allowed = str(FAST_H3_STEPS)
        raise ValueError(f"{profile['label']} exige {allowed} steps.")
    return profile_id, profile, vertical


def _model_source_reaches(workflow: dict[str, Any], source_id: str, target_id: str, seen: set[str] | None = None) -> bool:
    seen = seen or set()
    source_id = str(source_id)
    target_id = str(target_id)
    if source_id == target_id:
        return True
    if source_id in seen:
        return False
    seen.add(source_id)
    node = workflow.get(source_id)
    if not isinstance(node, dict):
        return False
    model_link = (node.get("inputs") or {}).get("model")
    return (
        isinstance(model_link, (list, tuple))
        and len(model_link) >= 1
        and _model_source_reaches(workflow, str(model_link[0]), target_id, seen)
    )


def _model_source_has_connected_sage(workflow: dict[str, Any], source_id: str, loader_id: str) -> bool:
    """Require Sage on the model chain that actually originates at this H3 loader."""
    seen: set[str] = set()

    def visit(current_id: str) -> bool:
        current_id = str(current_id)
        if current_id in seen or current_id == str(loader_id):
            return False
        seen.add(current_id)
        node = workflow.get(current_id)
        if not isinstance(node, dict):
            return False
        model_link = (node.get("inputs") or {}).get("model")
        if not isinstance(model_link, (list, tuple)) or not model_link:
            return False
        parent_id = str(model_link[0])
        if str(node.get("class_type") or "") == H3_SAGE_ATTENTION_NODE:
            return _model_source_reaches(workflow, parent_id, loader_id)
        return visit(parent_id)

    return visit(str(source_id))


def ensure_h3_sage_attention(workflow: dict[str, Any]) -> dict[str, Any]:
    """Attach the mandatory Sage -> protection -> Spectrum chain to all H3 paths."""
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("H3_GRAPH_EMPTY: o workflow ComfyUI esta vazio.")
    nodes = [node for node in workflow.values() if isinstance(node, dict)]
    loaders = [
        (str(node_id), node) for node_id, node in workflow.items()
        if isinstance(node, dict)
        and str(node.get("class_type") or "") == "UNETLoader"
        and str((node.get("inputs") or {}).get("unet_name") or "")
        .startswith(("minimax_h3_", "fastvideo_fasth3_"))
    ]
    if not loaders:
        if any(str(n.get("class_type") or "").startswith("MiniMaxH3") and
               n.get("class_type") in {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo",
                                       "MiniMaxH3MotionDirector", "MiniMaxH3FiniteSegmentSampler"}
               for n in nodes):
            raise ValueError("H3_GRAPH_MODEL_REQUIRED: workflow H3 sem UNETLoader suportado.")
        return workflow
    if len(loaders) != 1:
        raise ValueError("H3_GRAPH_MODEL_AMBIGUOUS: SageAttention exige um UNETLoader H3.")
    loader_id = loaders[0][0]
    prepare_spectrum(workflow)

    consumers = [
        (str(node_id), node) for node_id, node in workflow.items()
        if isinstance(node, dict)
        and str(node.get("class_type") or "") in SAMPLING_CONSUMERS
        and isinstance((node.get("inputs") or {}).get("model"), (list, tuple))
    ]
    if not consumers:
        raise ValueError("H3_GRAPH_SAGE_PATH_MISSING: nenhum caminho de amostragem H3 foi encontrado.")
    consumer_sources = [str((node.get("inputs") or {})["model"][0]) for _, node in consumers]
    if any(not _model_source_reaches(workflow, source, loader_id) for source in consumer_sources):
        raise ValueError("H3_GRAPH_MODEL_PATH_MISMATCH: amostrador nao deriva do UNETLoader H3 selecionado.")
    if all(_model_source_has_connected_sage(workflow, source, loader_id) for source in consumer_sources):
        return ensure_spectrum(workflow)

    unpatched = [
        (node_id, node, str((node.get("inputs") or {})["model"][0]))
        for node_id, node in consumers
        if not _model_source_has_connected_sage(workflow, str((node.get("inputs") or {})["model"][0]), loader_id)
    ]
    sources = list(dict.fromkeys(source_id for _, _, source_id in unpatched))
    for source_id in sources:
        # Numeric IDs are reserved by the Ref2VA builder (17 = audio VAE).
        patch_id = "pemara_h3_sage_" + source_id
        while patch_id in workflow:
            patch_id += "_"
        workflow[patch_id] = {
            "class_type": H3_SAGE_ATTENTION_NODE,
            "inputs": {"model": [source_id, 0]},
        }
        for _, consumer, consumer_source in unpatched:
            if consumer_source == source_id:
                consumer["inputs"]["model"] = [patch_id, 0]
    return ensure_spectrum(workflow)


def validate_h3_comfy_graph(
    workflow: dict[str, Any],
    *,
    mode: str,
    exact_pose_control_required: bool = False,
    model_variant: str = "",
) -> dict[str, Any]:
    """Prove that the generated Comfy graph implements the declared H3 mode.

    Reference video is not a synonym for pose control.  A graph may only claim
    exact pose transfer when a real pose-conditioning node consumes a DWPose
    stream.  Stock H3 Ref2VA has no such input and therefore fails closed for
    that production requirement.
    """

    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("H3_GRAPH_EMPTY: o workflow ComfyUI esta vazio.")
    nodes = [node for node in workflow.values() if isinstance(node, dict)]
    classes = {str(node.get("class_type") or "") for node in nodes}
    loaders = [
        (str(node_id), node) for node_id, node in workflow.items()
        if isinstance(node, dict) and str(node.get("class_type") or "") == "UNETLoader"
    ]
    if len(loaders) != 1:
        raise ValueError("H3_GRAPH_MODEL_AMBIGUOUS: exige exatamente um UNETLoader.")
    loader_id, loader = loaders[0]
    loaded_model = str((loader.get("inputs") or {}).get("unet_name") or "")
    normalized_mode = str(mode or "").strip().upper()
    normalized_variant = str(model_variant or "").strip().lower()
    if normalized_variant not in {"", "base", FAST_H3_VARIANT}:
        raise ValueError(f"H3_GRAPH_VARIANT_INVALID: variante desconhecida {normalized_variant}.")
    if normalized_variant == FAST_H3_VARIANT and normalized_mode not in {"T2VA", "I2VA", "FL2VA", "L2VA"}:
        raise ValueError("H3_FAST_REFERENCE_UNSUPPORTED: FastH3 suporta texto e primeiro/ultimo quadro, sem Ref2VA.")
    expected = {
        "T2VA": (H3_FL2VA_MODEL_NAME, "MiniMaxH3ImageToVideo"),
        "I2VA": (H3_FL2VA_MODEL_NAME, "MiniMaxH3ImageToVideo"),
        "FL2VA": (H3_FL2VA_MODEL_NAME, "MiniMaxH3ImageToVideo"),
        "L2VA": (H3_FL2VA_MODEL_NAME, "MiniMaxH3ImageToVideo"),
        "REF2VA": (H3_REF2VA_MODEL_NAME, "MiniMaxH3ReferenceToVideo"),
    }.get(normalized_mode)
    if expected is None:
        raise ValueError(f"H3_GRAPH_MODE_INVALID: modo desconhecido {normalized_mode or 'vazio'}.")
    expected_model, expected_conditioning = expected
    if normalized_variant == FAST_H3_VARIANT:
        expected_model = FAST_H3_MODEL_NAME
    if loaded_model != expected_model:
        raise ValueError(
            "H3_GRAPH_MODEL_MISMATCH: "
            f"{normalized_mode} exige {expected_model}, mas o grafo carrega {loaded_model or 'nenhum'}."
        )
    if expected_conditioning not in classes:
        raise ValueError(
            "H3_GRAPH_CONDITIONING_MISMATCH: "
            f"{normalized_mode} exige o no {expected_conditioning}."
        )
    incompatible = (
        "MiniMaxH3ReferenceToVideo"
        if normalized_mode != "REF2VA"
        else "MiniMaxH3ImageToVideo"
    )
    if incompatible in classes:
        raise ValueError(
            "H3_GRAPH_MIXED_MODES: o grafo mistura condicionamentos FL2VA e Ref2VA."
        )
    if not any(str(node.get("class_type") or "") == H3_SAGE_ATTENTION_NODE for node in nodes):
        raise ValueError("H3_GRAPH_SAGE_REQUIRED: SageAttention H3 e obrigatorio em todo workflow.")
    sampling_consumers = [
        node for node in nodes
        if str(node.get("class_type") or "") in SAMPLING_CONSUMERS
        and isinstance((node.get("inputs") or {}).get("model"), (list, tuple))
    ]
    if not sampling_consumers or any(
        not _model_source_has_connected_sage(workflow, str((node.get("inputs") or {})["model"][0]), loader_id)
        for node in sampling_consumers
    ):
        raise ValueError("H3_GRAPH_SAGE_DISCONNECTED: SageAttention nao esta conectado ao caminho de amostragem.")
    validate_spectrum(workflow)
    if normalized_variant == FAST_H3_VARIANT:
        schedulers = [node for node in nodes if str(node.get("class_type") or "") == "BasicScheduler"]
        if not schedulers or any(int((node.get("inputs") or {}).get("steps") or 0) != FAST_H3_STEPS for node in schedulers):
            raise ValueError("H3_FAST_STEPS_REQUIRED: FastH3 8-Step V2 exige exatamente 8 steps.")
    if exact_pose_control_required:
        raise ValueError(
            "H3_EXACT_POSE_UNSUPPORTED: video de referencia H3 nao e controle DWPose. "
            "Coreografia exata exige DWPreprocessor ligado a um condicionador de pose compativel."
        )
    return {
        "ok": True,
        "mode": normalized_mode,
        "model": loaded_model,
        "conditioning": expected_conditioning,
        "modelVariant": normalized_variant or "base",
        "sageAttention": "connected_required",
        "spectrum": "connected_required",
        "exactPoseControl": bool(exact_pose_control_required),
    }

H3_COMPONENTS = (
    ("MiniMax H3 FL2VA pruned INT8 ConvRot", "video_generation", f"ferramentas/ComfyUI/models/diffusion_models/{H3_FL2VA_MODEL_NAME}", True),
    ("MiniMax H3 Ref2VA pruned INT8 ConvRot", "reference_video_generation", f"ferramentas/ComfyUI/models/diffusion_models/{H3_REF2VA_MODEL_NAME}", False),
    ("Qwen3-VL-32B MiniMax H3 NVFP4 AWQ", "text_and_multimodal_encoding", "ferramentas/ComfyUI/models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", True),
    ("MiniMax H3 Video VAE INT8 ConvRot", "video_decode", "ferramentas/ComfyUI/models/vae/minimax_h3_video_vae_int8_convrot.safetensors", True),
    ("MiniMax H3 Audio VAE FP32", "native_audio_decode", "ferramentas/ComfyUI/models/vae/minimax_h3_audio_vae_fp32.safetensors", True),
    ("Qwen Image 2.1 INT8", "anchor_generation", "ferramentas/ComfyUI/models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors", False),
    ("Qwen Image 2.1 Edit", "anchor_correction", "ferramentas/ComfyUI/models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors", False),
    ("SeedVR2 3B INT8 ConvRot", "required_approved_source_upscale", "ferramentas/ComfyUI/models/diffusion_models/seedvr2_3b_int8_convrot.safetensors", False),
    ("SeedVR2 VAE FP16", "required_upscale_decode", "ferramentas/ComfyUI/models/vae/seedvr2_ema_vae_fp16.safetensors", False),
)

WORKFLOW_SKILLS = (
    ("pemara-video-production-lead", "sequence_production_and_artistic_review"),
    ("pemara-cinematography-director", "blocking_camera_lighting_and_visual_readability"),
    ("pemara-performance-director", "playable_intention_acting_reaction_and_recovery"),
    ("pemara-film-editor", "approved_source_selection_rhythm_and_causal_cuts"),
    ("pemara-live-action-showrunner", "live_action_risk_routing_and_contract"),
    ("pemara-live-action-combat-director", "signature_moves_power_ownership_and_contact_physics"),
    ("pemara-live-action-kinetic-supervisor", "identity_performance_balance_and_kinetic_handoffs"),
    ("pemara-live-action-continuity", "moving_handoff_and_connector_contract"),
    ("pemara-live-action-qc", "human_material_temporal_and_finishing_qc"),
    ("project-planner", "brief_and_schedule"),
    ("creative-director", "screenplay_and_visual_language"),
    ("pemara-cinematic-take-director", "take_story_contract"),
    ("image-production", "anchor_creation_and_qc"),
    ("pemara-video-motion-director", "continuous_motion_contract"),
    ("video-production", "technical_qc_and_master"),
    ("game-audio-designer", "foley_and_mix_direction"),
    ("audio-analysis", "loudness_and_sync_qc"),
    ("debugger", "root_cause_debug"),
    ("test-engineer", "regression_gates"),
    ("performance-optimizer", "quality_preserving_profiling"),
    ("documentation-and-adrs", "traceability_and_restore_docs"),
    ("automation-engineer", "serial_queue_and_backup"),
)

STAGES: tuple[dict[str, Any], ...] = (
    {
        "id": "01_story_contract",
        "label": "Producao, roteiro e direcao dos takes",
        "agents": ["pemara-video-production-lead", "pemara-cinematic-take-director", "pemara-performance-director", "pemara-cinematography-director", "pemara-film-editor", "pemara-live-action-showrunner", "pemara-live-action-combat-director", "pemara-live-action-kinetic-supervisor", "project-planner", "creative-director"],
        "models": ["NVIDIA reasoning (optional, text only)"],
        "output": "mapa unico, cameras/percursos/estados compartilhados, contrato verificavel e bloco piloto com fronteira; intencao, atuacao, cobertura e cortes",
        "gate": "owner_story_approval",
    },
    {
        "id": "02_anchor_lock",
        "label": "Fotos ancora perfeitas",
        "agents": ["image-production", "pemara-cinematography-director", "pemara-cinematic-take-director"],
        "models": ["Qwen Image 2.1 INT8", "Qwen Image 2.1 Edit"],
        "output": "ancoras aprovadas por hash, elenco conferido e DLSS seletivo com mascara explicita dos atores; fonte anterior preservada",
        "gate": "owner_anchor_approval",
    },
    {
        "id": "03_h3_prompt_compile",
        "label": "Prompt H3 oficial amarrado",
        "agents": ["pemara-performance-director", "pemara-cinematography-director", "creative-director", "pemara-live-action-combat-director", "pemara-video-motion-director", "h3-prompt-writing"],
        "models": ["Qwen3-VL-32B MiniMax H3 NVFP4 AWQ"],
        "output": "modo H3 qualificado, timeline, ancoras por rota, intencao e camera; audio somente no escopo autorizado",
        "gate": "official_prompt_contract_pass",
    },
    {
        "id": "04_preflight",
        "label": "Preflight sem GPU",
        "agents": ["pemara-live-action-showrunner", "pemara-live-action-qc", "pemara-video-motion-director", "test-engineer"],
        "models": [],
        "output": "identidade, fisica, camera, profundidade, acao interna, progressao e integridade",
        "gate": "closed_preflight_pass",
    },
    {
        "id": "05_h3_take",
        "label": "Geracao serial MiniMax H3",
        "agents": ["automation-engineer", "performance-optimizer"],
        "models": ["MiniMax H3 FL2VA/Ref2VA pruned INT8 ConvRot", "MiniMax H3 Video VAE INT8 ConvRot", "MiniMax H3 Audio VAE FP32", "SageAttention + Spectrum"],
        "output": "take nativo no perfil escolhido; Production 1088x608 ou 608x1088, 24 fps, 10 steps, guidance 1.0 por padrao; DLSS 5 obrigatorio na previa",
        "gate": "technical_candidate_only",
    },
    {
        "id": "06_visual_qc",
        "label": "QC visual e aprovacao humana",
        "agents": ["pemara-video-production-lead", "pemara-live-action-qc", "pemara-performance-director", "pemara-cinematography-director", "video-production", "pemara-video-motion-director"],
        "models": [],
        "output": "MP4 integral observado: historia, atuacao, fotografia, identidade, fisica e movimento; timestamps, correcao e integridade, sem inferir aprovacao por metadata",
        "gate": "owner_visual_approval",
    },
    {
        "id": "07_continuous_connectors",
        "label": "Continuidade e cortes de acao",
        "agents": ["pemara-film-editor", "pemara-live-action-kinetic-supervisor", "pemara-live-action-continuity", "pemara-cinematic-take-director", "pemara-video-motion-director"],
        "models": ["MiniMax H3 FL2VA pruned INT8 ConvRot"],
        "output": "fronteiras revisadas em intervalos moveis e geografia compartilhada; corte direto ou acao ausente por conector permitido; fonte incompatível exige correcao",
        "gate": "no_crossfade_no_freeze_no_reset",
    },
    {
        "id": "08_picture_lock",
        "label": "Montagem aprovada e acabamento FHD60",
        "agents": ["pemara-film-editor", "pemara-video-production-lead", "video-production"],
        "models": ["SeedVR2 3B INT8 ConvRot", "Practical-RIFE 4.25 exact60", "DLSS 5 Natural", "FFmpeg H.264 NVENC"],
        "output": "candidato FHD/QHD/UHD 60 fps, contain/pad sem corte, audio existente preservado, fonte nativa aprovada retida",
        "gate": "owner_picture_lock",
    },
    {
        "id": "09_foley",
        "label": "Audio adicional somente quando solicitado",
        "agents": ["game-audio-designer", "audio-analysis"],
        "models": ["Tencent HunyuanVideo-Foley XXL"],
        "output": "audio existente preservado; Foley novo somente no escopo explicitamente autorizado, candidato com escuta e aprovacao proprias",
        "gate": "owner_audio_approval",
    },
    {
        "id": "10_final_master",
        "label": "Master final e rollback",
        "agents": ["pemara-video-production-lead", "pemara-film-editor", "video-production", "test-engineer", "documentation-and-adrs"],
        "models": ["FFmpeg", "ffprobe", "EBU R128"],
        "output": "FHD60, hashes, loudness, manifesto, backup e rollback",
        "gate": "technical_pass_plus_owner_approval",
    },
)


def _agents_root(workspace_root: Path) -> Path:
    root = Path(workspace_root).resolve()
    return root.parents[1] / ".agents"


def _file_status(workspace_root: Path, item: tuple[str, str, str, bool]) -> dict[str, Any]:
    label, role, relative, required = item
    path = Path(workspace_root) / Path(relative)
    present = path.is_file()
    return {
        "label": label,
        "role": role,
        "required": required,
        "present": present,
        "bytes": path.stat().st_size if present else 0,
        "relativePath": relative,
    }


def _active_comfy_diffusion_dirs(workspace: Path) -> list[Path]:
    workspaces: list[Path] = []
    for key in ("COMFYUI_WORKSPACE", "COMFY_WORKSPACE"):
        value = os.environ.get(key, "").strip()
        if value:
            workspaces.append(Path(value).expanduser())
    local_app_data = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    config_path = local_app_data / "comfy-cli" / "config.ini"
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
        configured = parser.defaults().get("default_workspace") or parser.get("comfy-cli", "default_workspace", fallback="")
        if configured:
            workspaces.append(Path(configured).expanduser())
    except (OSError, configparser.Error):
        pass
    if not workspaces:
        workspaces.extend((workspace.parent / "runtimes").glob("ComfyUI-*"))

    diffusion_dirs: list[Path] = []
    for comfy_workspace in dict.fromkeys(path.resolve() for path in workspaces):
        diffusion_dirs.append(comfy_workspace / "models" / "diffusion_models")
        extra_paths_file = comfy_workspace / "extra_model_paths.yaml"
        try:
            import yaml
        except ImportError:
            continue
        try:
            extra_paths = yaml.safe_load(extra_paths_file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(extra_paths, dict):
            continue
        for entry in extra_paths.values():
            if not isinstance(entry, dict) or not entry.get("base_path"):
                continue
            base_path = Path(os.path.expandvars(str(entry["base_path"]))).expanduser()
            for category in ("diffusion_models", "unet"):
                folders = entry.get(category) or []
                if isinstance(folders, str):
                    folders = folders.splitlines()
                elif not isinstance(folders, (list, tuple)):
                    folders = [folders]
                for folder in folders:
                    folder = str(folder or "").strip()
                    if folder:
                        diffusion_dirs.append(base_path / folder)
    return list(dict.fromkeys(path.resolve() for path in diffusion_dirs))


def workflow_status(workspace_root: Path, *, comfy_online: bool = False) -> dict[str, Any]:
    """Return the canonical workflow plus a live, non-invasive inventory."""

    workspace = Path(workspace_root).resolve()
    agents_root = _agents_root(workspace)
    skill_root = agents_root / "skills"
    profile_root = agents_root / "profiles"
    installed_skills = sorted(path.name for path in skill_root.iterdir() if path.is_dir()) if skill_root.is_dir() else []
    installed_profiles = sorted(path.stem for path in profile_root.glob("*.md")) if profile_root.is_dir() else []
    routed_skills = [
        {"name": name, "role": role, "installed": name in installed_skills}
        for name, role in WORKFLOW_SKILLS
    ]
    official = official_skill_integrity(workspace)
    live_action_pack = live_action_pack_status(workspace)
    routed_skills.insert(
        5,
        {
            "name": "h3-prompt-writing",
            "role": "official_local_prompt_compiler",
            "installed": bool(official.get("ok")),
            "official": True,
        },
    )
    components = [_file_status(workspace, item) for item in H3_COMPONENTS]
    fast_h3_candidates = [
        root / FAST_H3_MODEL_NAME
        for root in _active_comfy_diffusion_dirs(workspace)
    ]
    fast_h3_path = next((path for path in fast_h3_candidates if path.is_file()), None)
    fast_h3_size = fast_h3_path.stat().st_size if fast_h3_path else 0
    fast_h3_ready = bool(fast_h3_path and fast_h3_size == FAST_H3_EXPECTED_BYTES)
    required_components_ok = all(item["present"] for item in components if item["required"])
    required_skills_ok = all(item["installed"] for item in routed_skills)
    return {
        "ok": bool(required_components_ok and required_skills_ok and official.get("ok") and live_action_pack.get("ok")),
        "version": WORKFLOW_VERSION,
        "enginePolicy": ENGINE_POLICY,
        "videoEngine": "MiniMax H3",
        "faceRefine": face_refine_policy(),
        "comfyOnline": bool(comfy_online),
        "productionReady": bool(comfy_online and required_components_ok and required_skills_ok and official.get("ok") and live_action_pack.get("ok")),
        "qualityPolicy": {
            "nativeFps": 24,
            "deliveryFps": 60,
            "defaultProfile": DEFAULT_H3_QUALITY_PROFILE,
            "guidance": 1.0,
            "livePreviewOptIn": True,
            "sampler": "res_multistep",
            "scheduler": "simple",
            "renderFocusPreflight": True,
            "mainTakeDurationPolicy": "story_driven_4_to_15_seconds; five seconds is not mandatory",
            "postprocess": ["SeedVR2 3B INT8 ConvRot", "RIFE 4.25 timestamps j/60", "DLSS 5 Natural", "contain/pad sem corte", "audio existente preservado", "H.264 60 fps"],
            "faceRefine": {"enabled": False, "status": "REMOVED_BY_OWNER"},
            "finishingContract": "services/studio/upscaling_required.py",
            "sageAttention": {"required": True, "node": H3_SAGE_ATTENTION_NODE},
            "spectrum": {"required": True, "node": SPECTRUM_NODE, "configuration": "approved_audio_replay"},
        },
        "qualityProfiles": [
            {"id": profile_id, **profile, "steps": list(profile["steps"])}
            for profile_id, profile in H3_QUALITY_PROFILES.items()
            if not profile.get("legacy")
        ],
        "capabilities": {
            "fl2vaReady": any(
                item["present"] and item["relativePath"].endswith(H3_FL2VA_MODEL_NAME)
                for item in components
            ),
            "ref2vaReady": any(
                item["present"] and item["relativePath"].endswith(H3_REF2VA_MODEL_NAME)
                for item in components
            ),
            "fastH3Ready": fast_h3_ready,
            "fastH3Model": FAST_H3_MODEL_NAME,
            "fastH3Bytes": fast_h3_size,
            "fastH3ExpectedBytes": FAST_H3_EXPECTED_BYTES,
            "sageAttentionRequired": True,
            "spectrumRequired": True,
            "exactPoseControl": False,
            "referenceVideoIsPoseControl": False,
        },
        "continuousActionContract": {
            "required": True,
            "crossfadeFrames": 0,
            "freezeFrames": 0,
            "staticHoldFrames": 0,
            "resetAllowed": False,
        },
        "catalog": {
            "installedSkills": len(installed_skills),
            "installedProfiles": len(installed_profiles),
            "agentsRoot": str(agents_root),
        },
        "routedSkills": routed_skills,
        "components": components,
        "officialPromptSkill": official,
        "liveActionPack": live_action_pack,
        "stages": list(STAGES),
    }


def take_readiness(spec: dict[str, Any]) -> dict[str, Any]:
    """Summarize the already-enforced project preflight as explicit H3 gates."""

    prompt = str(spec.get("prompt") or "")
    contract = spec.get("h3PromptContract") if isinstance(spec.get("h3PromptContract"), dict) else {}
    profile = str(spec.get("generationProfile") or "")
    mode = str(contract.get("mode") or "")
    has_start = bool(spec.get("keyframeName"))
    has_end = bool(spec.get("endKeyframeName"))
    minimax_control = (
        spec.get("minimaxAnchorControl")
        if isinstance(spec.get("minimaxAnchorControl"), dict)
        else {}
    )
    has_reference_images = bool(minimax_control.get("referenceImages"))
    has_reference_video = bool(minimax_control.get("referenceVideo"))
    required_prompt_sections = (
        (
            "subject_definitions:",
            "summary:",
            "retention_analysis:",
            "detailed_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        )
        if mode == "REF2VA"
        else (
            "integrated_multimodal_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        )
    )
    anchor_mode_ready = (
        (mode == "T2VA" and not has_start and not has_end)
        or (mode == "I2VA" and has_start and not has_end)
        or (mode == "FL2VA" and has_start and has_end)
        or (mode == "L2VA" and not has_start and has_end)
        # MiniMax H3 Ref2VA accepts appearance pictures without a motion video.
        # A reference video is optional and, when absent, motion is prompt-guided.
        or (mode == "REF2VA" and (has_reference_images or has_reference_video))
    )
    execution = (
        spec.get("takeExecutionContract")
        if isinstance(spec.get("takeExecutionContract"), dict)
        else {}
    )
    ref_subjects_ready = (
        mode != "REF2VA"
        or bool(re.search(r"<Subject\s+\d+>", prompt, flags=re.IGNORECASE))
    )
    motion_capability_ready = not (
        mode == "REF2VA"
        and str(execution.get("motionBinding") or "").strip().lower() == "exact_pose"
    )
    camera_ready, camera_detail = True, 'not_required_for_historical_or_single_shot_scope'
    camera_contract = spec.get('sequenceCameraContract')
    if spec.get('sequenceCameraRequired') or camera_contract:
        try:
            if not camera_contract:
                raise ValueError('Mapa/contrato de camera ausente.')
            from sequence_camera_contract import load_and_validate
            load_and_validate(camera_contract, take_id=spec.get('takeId'), stage='generation')
            camera_detail = 'map_and_pilot_evidence_verified; artistic_approval_not_inferred'
        except (OSError, ValueError, KeyError) as error:
            camera_ready, camera_detail = False, str(error)
    gates = [
        {"id": "engine", "pass": profile.startswith("minimax_h3_"), "detail": profile},
        {"id": "official_prompt", "pass": contract.get("localOnly") is True and bool(contract.get("contractVersion")), "detail": str(contract.get("contractVersion") or "missing")},
        {"id": "prompt_sections", "pass": all(section in prompt for section in required_prompt_sections), "detail": mode or "unknown"},
        {"id": "reference_subjects", "pass": ref_subjects_ready, "detail": "Ref2VA requires explicit <Subject N> identity roles"},
        {"id": "anchor_mode", "pass": anchor_mode_ready, "detail": f"mode={mode}; start={has_start}; end={has_end}; refImages={has_reference_images}; refVideo={has_reference_video}"},
        {"id": "motion_capability", "pass": motion_capability_ready, "detail": f"mode={mode}; motion={execution.get('motionBinding', 'legacy')}"},
        {"id": "native_quality", "pass": float(spec.get("fps") or 0) == 24.0 and float(spec.get("guidance") or 0) == 1.0, "detail": f"{spec.get('fps')} fps; {spec.get('steps')} steps; guidance {spec.get('guidance')}"},
        {"id": "execution_controls", "pass": not execution or execution.get("declaredControlsVerified") is True, "detail": f"anchors={execution.get('anchorBinding', 'legacy')}; motion={execution.get('motionBinding', 'legacy')}"},
        {"id": "sequence_camera", "pass": camera_ready, "detail": camera_detail},
        {"id": "human_gate", "pass": str(spec.get("status") or "").upper() not in {"GENERATING", "QUEUED"}, "detail": "candidate_requires_owner_review"},
    ]
    return {
        "ready": all(item["pass"] for item in gates[:-1]),
        "projectId": str(spec.get("projectId") or ""),
        "takeId": str(spec.get("takeId") or ""),
        "mode": mode,
        "gates": gates,
        "next": "queue_candidate" if all(item["pass"] for item in gates[:-1]) else "repair_contract",
    }
