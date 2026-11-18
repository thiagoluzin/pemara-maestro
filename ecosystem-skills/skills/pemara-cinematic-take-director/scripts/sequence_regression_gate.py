from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CANONICAL_PROJECT = "vejito_super_boo_3x10_continuo_liveaction_foley_v1"
PASS_FIELDS = ("art_direction", "cinematic", "motion", "technical")
DYNAMIC_CHAIN_INPUT_MODE = "FIRST_FRAME_ONLY_SERIAL_LAST_MOVING_FRAME_CHAIN"
DYNAMIC_END_STATUS = "DYNAMIC_END_FROM_H3_TAKE_NOT_PRECOMPUTED"
DYNAMIC_END_SOURCE_POLICY = "EDITORIAL_BOUNDARY_LAST_STILL_MOVING_FRAME_OF_HUMAN_APPROVED_H3_TAKE"
DYNAMIC_SERIAL_CHAIN_RULE = (
    "APPROVED_PREVIOUS_TAKE_RETAINED_EDITORIAL_BOUNDARY_LAST_MOVING_FRAME_TO_NEXT_TAKE_START"
)
DYNAMIC_END_SOURCE_POLICIES = {
    "LAST_STILL_MOVING_FRAME_OF_HUMAN_APPROVED_H3_TAKE",
    DYNAMIC_END_SOURCE_POLICY,
}
DYNAMIC_SERIAL_CHAIN_RULES = {
    "APPROVED_PREVIOUS_TAKE_LAST_MOVING_FRAME_TO_NEXT_TAKE_START",
    DYNAMIC_SERIAL_CHAIN_RULE,
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def resolve_asset(manifest_path: Path, value: Any) -> Path | None:
    if not nonempty(value):
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def approved_status(value: Any) -> bool:
    return str(value or "").strip().lower() in {
        "approved",
        "approved_by_owner",
        "approved_for_video",
    }


def take_id(take: dict[str, Any]) -> str:
    return str(take.get("id") or take.get("take_id") or "").strip()


def is_h3_dynamic_chain_take(
    data: dict[str, Any], take: dict[str, Any]
) -> bool:
    """Recognize the strict owner-directed alternative to static duel endpoints."""

    strategy = data.get("h3_free_duel_strategy")
    strategy = strategy if isinstance(strategy, dict) else {}
    generation = take.get("video_generation")
    generation = generation if isinstance(generation, dict) else {}
    art = take.get("art_direction_gate")
    art = art if isinstance(art, dict) else {}
    end_image = take.get("end_image")
    end_image = end_image if isinstance(end_image, dict) else {}
    duel_take_ids = {str(value) for value in strategy.get("duel_take_ids", [])}

    return all(
        (
            take_id(take) in duel_take_ids,
            nonempty(strategy.get("decision_id")),
            strategy.get("serial_chain_rule") in DYNAMIC_SERIAL_CHAIN_RULES,
            strategy.get("no_freeze_hold_crossfade_or_rife") is True,
            generation.get("input_mode") == DYNAMIC_CHAIN_INPUT_MODE,
            generation.get("choreography_freedom") is True,
            art.get("precomputed_internal_anchors_required") is False,
            art.get("precomputed_end_anchor_required") is False,
            end_image.get("status") == DYNAMIC_END_STATUS,
            end_image.get("source_policy") in DYNAMIC_END_SOURCE_POLICIES,
            end_image.get("static_image_generation_forbidden") is True,
            end_image.get("exact_hash_registration_required") is True,
            end_image.get("strategy_decision_id") == strategy.get("decision_id"),
        )
    )


def check_approved_asset(
    asset: dict[str, Any],
    label: str,
    manifest_path: Path,
    errors: list[str],
) -> None:
    if not approved_status(asset.get("status")):
        errors.append(f"{label}.status não está aprovado para vídeo")

    file_path = resolve_asset(manifest_path, asset.get("file"))
    declared_sha = str(asset.get("sha256") or "").strip().lower()
    if file_path is None:
        errors.append(f"{label}.file está ausente")
    elif not file_path.is_file():
        errors.append(f"{label}.file não existe: {file_path}")
    elif not declared_sha:
        errors.append(f"{label}.sha256 está ausente")
    else:
        actual_sha = sha256_file(file_path)
        if actual_sha != declared_sha:
            errors.append(f"{label}.sha256 diverge do arquivo real")

    metadata_path = resolve_asset(manifest_path, asset.get("metadata"))
    if metadata_path is None:
        errors.append(f"{label}.metadata está ausente")
        return
    if not metadata_path.is_file():
        errors.append(f"{label}.metadata não existe: {metadata_path}")
        return
    try:
        metadata = load(metadata_path)
    except (OSError, ValueError) as exc:
        errors.append(f"{label}.metadata não pôde ser lida: {exc}")
        return
    metadata_sha = str(
        metadata.get("sha256")
        or metadata.get("image_sha256")
        or metadata.get("source_sha256")
        or ""
    ).strip().lower()
    if declared_sha and metadata_sha != declared_sha:
        errors.append(f"{label}.metadata.sha256 diverge da âncora vinculada")
    metadata_status = metadata.get("status") or metadata.get("validation_status")
    if not approved_status(metadata_status):
        errors.append(f"{label}.metadata.status não registra aprovação")
    approval = metadata.get("approval") or {}
    previous = approval.get("previous_evidence") or {}
    human_review = metadata.get("human_review") or {}
    has_owner_evidence = any(
        (
            approved_status(approval.get("status")),
            approved_status(previous.get("source_status")),
            (
                approved_status(human_review.get("decision"))
                and human_review.get("explicit_human_confirmation") is True
            ),
            nonempty(approval.get("reconfirmed_by_owner_at")),
            nonempty(metadata.get("approved_at")),
            nonempty(metadata.get("approval_basis")),
            nonempty(metadata.get("approval_evidence")),
        )
    )
    if not has_owner_evidence:
        errors.append(f"{label}.metadata não contém evidência de aprovação humana")


def check_contract(data: dict[str, Any], errors: list[str]) -> None:
    reference = data.get("canonical_reference", {})
    if reference.get("project_id") != CANONICAL_PROJECT:
        errors.append(f"canonical_reference.project_id deve ser {CANONICAL_PROJECT}")
    if reference.get("owner_declared_standard") is not True:
        errors.append("canonical_reference.owner_declared_standard deve ser true")
    if not nonempty(reference.get("audited_artifacts")):
        errors.append("canonical_reference.audited_artifacts está ausente")

    bible = data.get("art_direction_bible", {})
    if bible.get("style_mode") != "photorealistic_live_action":
        errors.append("art_direction_bible.style_mode deve ser photorealistic_live_action")
    for field in (
        "character_materials",
        "character_anatomy",
        "environment",
        "lens_language",
        "lighting",
        "palette",
        "forbidden_render_modes",
    ):
        if not nonempty(bible.get(field)):
            errors.append(f"art_direction_bible.{field} está ausente")
    anatomy = bible.get("character_anatomy")
    if not isinstance(anatomy, dict) or not anatomy:
        errors.append("art_direction_bible.character_anatomy deve ser uma matriz por personagem")
    else:
        for character, invariant in anatomy.items():
            if not nonempty(invariant):
                errors.append(
                    f"art_direction_bible.character_anatomy.{character} está vazio"
                )
    if bible.get("anchor_source_policy") != "reuse_exact_owner_approved_images_no_regeneration":
        errors.append(
            "art_direction_bible.anchor_source_policy deve bloquear regeneração de âncoras aprovadas"
        )

    approvals = data.get("approval_policy", {})
    for field in (
        "human_anchor_approval_required",
        "human_take_art_approval_required",
        "human_take_motion_approval_required",
        "human_final_playback_required",
    ):
        if approvals.get(field) is not True:
            errors.append(f"approval_policy.{field} deve ser true")
    if approvals.get("auto_promote") is not False:
        errors.append("approval_policy.auto_promote deve ser false")
    for field in (
        "owner_rejection_auto_creates_same_scope_replacement",
        "preserve_rejected_artifacts",
        "block_rejected_from_assembly",
        "replacement_requires_separate_human_approval",
    ):
        if approvals.get(field) is not True:
            errors.append(f"approval_policy.{field} deve ser true")

    engine_policy = data.get("generation_engine_policy", {})
    owner_engine = engine_policy.get("owner_selected_engine")
    if not nonempty(owner_engine):
        errors.append("generation_engine_policy.owner_selected_engine está ausente")
    if engine_policy.get("allow_substitution_without_owner_approval") is not False:
        errors.append(
            "generation_engine_policy.allow_substitution_without_owner_approval deve ser false"
        )

    catalog = data.get("maestro_catalog_policy", {})
    if catalog.get("visible_items") != "main_takes_only":
        errors.append("maestro_catalog_policy.visible_items deve ser main_takes_only")
    if catalog.get("internal_microsegments_visible") is not False:
        errors.append("maestro_catalog_policy.internal_microsegments_visible deve ser false")

    takes = data.get("takes", [])
    if not takes:
        errors.append("takes deve conter ao menos um take principal")
        return
    route = data.get("visual_route_id")
    if not nonempty(route):
        errors.append("visual_route_id está ausente")
    for index, take in enumerate(takes, start=1):
        label = f"take[{take.get('id', index)}]"
        for field in (
            "story_purpose",
            "story_change",
            "reaction",
            "cut_motivation",
            "duration_reason",
            "motion_beats",
        ):
            if not nonempty(take.get(field)):
                errors.append(f"{label}.{field} está ausente")
        beats = take.get("motion_beats", {})
        for beat in ("early_0_30", "middle_30_70", "late_70_100"):
            if not nonempty(beats.get(beat)):
                errors.append(f"{label}.motion_beats.{beat} está ausente")
        if take.get("visual_route_id") != route:
            errors.append(f"{label}.visual_route_id diverge da rota visual única")
        identity = take.get("identity_contract", {})
        for field in (
            "expected_characters",
            "forbidden_characters",
            "required_traits",
            "forbidden_traits",
            "identity_risk",
        ):
            if not nonempty(identity.get(field)):
                errors.append(f"{label}.identity_contract.{field} está ausente")
        engine = (take.get("video_generation") or {}).get("engine")
        if not nonempty(engine):
            errors.append(f"{label}.video_generation.engine está ausente")
        elif nonempty(owner_engine) and engine != owner_engine:
            errors.append(f"{label}.video_generation.engine diverge do engine escolhido")
        if str(identity.get("identity_risk") or "").lower() in {"high", "critical"}:
            dynamic_chain = is_h3_dynamic_chain_take(data, take)
            if not take.get("internal_anchors") and not dynamic_chain:
                errors.append(
                    f"{label}.internal_anchors é obrigatório para identity_risk alto/crítico"
                )
            if (
                not take.get("internal_anchors")
                and (take.get("video_generation") or {}).get("input_mode")
                == DYNAMIC_CHAIN_INPUT_MODE
                and not dynamic_chain
            ):
                errors.append(
                    f"{label}.h3_dynamic_chain possui contrato incompleto ou inconsistente"
                )


def check_anchors(
    data: dict[str, Any],
    errors: list[str],
    manifest_path: Path,
    selected_take_ids: set[str] | None = None,
) -> None:
    for index, take in enumerate(data.get("takes", []), start=1):
        label = f"take[{take.get('id', index)}]"
        current_take_id = take_id(take) or str(index)
        if selected_take_ids is not None and current_take_id not in selected_take_ids:
            continue

        check_approved_asset(
            take.get("base_image", {}), f"{label}.base_image", manifest_path, errors
        )
        if not is_h3_dynamic_chain_take(data, take):
            check_approved_asset(
                take.get("end_image", {}), f"{label}.end_image", manifest_path, errors
            )
            for anchor_index, anchor in enumerate(
                take.get("internal_anchors", []), start=1
            ):
                check_approved_asset(
                    anchor,
                    f"{label}.internal_anchors[{anchor_index}]",
                    manifest_path,
                    errors,
                )
        art = take.get("art_direction_gate", {})
        if art.get("anchor_status") != "PASS":
            errors.append(f"{label}.art_direction_gate.anchor_status não está PASS")
        if art.get("human_anchor_review") != "APPROVED":
            errors.append(f"{label}.art_direction_gate.human_anchor_review não está APPROVED")
        if not nonempty(art.get("anchor_contact_sheet")):
            errors.append(f"{label}.art_direction_gate.anchor_contact_sheet está ausente")


def check_assembly(
    data: dict[str, Any], errors: list[str], manifest_path: Path
) -> None:
    take_ids: list[str] = []
    takes_by_id: dict[str, dict[str, Any]] = {}
    for index, take in enumerate(data.get("takes", []), start=1):
        take_id = str(take.get("id", index))
        take_ids.append(take_id)
        takes_by_id[take_id] = take
        label = f"take[{take_id}]"
        if take.get("status") != "APPROVED" or take.get("maestro_status") != "APPROVED":
            errors.append(f"{label} não tem aprovação visual final no Maestro")
        gates = take.get("release_gates", {})
        for field in PASS_FIELDS:
            if gates.get(field) != "PASS":
                errors.append(f"{label}.release_gates.{field} não está PASS")
        if gates.get("human") != "APPROVED":
            errors.append(f"{label}.release_gates.human não está APPROVED")
        if not nonempty(gates.get("video_contact_sheet")):
            errors.append(f"{label}.release_gates.video_contact_sheet está ausente")
        active = resolve_asset(manifest_path, (take.get("video") or {}).get("output_active"))
        for rejected_index, rejected in enumerate(
            (take.get("video") or {}).get("rejected_candidates", []), start=1
        ):
            rejected_label = f"{label}.video.rejected_candidates[{rejected_index}]"
            if rejected.get("preserved") is not True:
                errors.append(f"{rejected_label}.preserved deve ser true")
            rejected_path = resolve_asset(manifest_path, rejected.get("path"))
            if active and rejected_path and active == rejected_path:
                errors.append(f"{rejected_label} não pode ser output_active")

    assembly = data.get("assembly", {})
    if assembly.get("mixed_visual_routes") is not False:
        errors.append("assembly.mixed_visual_routes deve ser false")
    if assembly.get("salvage_repair_used") is not False:
        errors.append("assembly.salvage_repair_used deve ser false")
    if assembly.get("crossfade_frames") != 0:
        errors.append("assembly.crossfade_frames deve ser 0")
    if assembly.get("freeze_frames") != 0:
        errors.append("assembly.freeze_frames deve ser 0")
    if assembly.get("static_hold_frames") != 0:
        errors.append("assembly.static_hold_frames deve ser 0")
    if assembly.get("all_sources_owner_approved") is not True:
        errors.append("assembly.all_sources_owner_approved deve ser true")
    interpolation = assembly.get("interpolation", {})
    if interpolation.get("used_only_after_source_pass") is not True:
        errors.append("assembly.interpolation.used_only_after_source_pass deve ser true")
    sources = assembly.get("sources", [])
    source_ids = [str(item.get("take_id")) for item in sources]
    if source_ids != take_ids:
        errors.append("assembly.sources deve listar, em ordem, exatamente os takes principais")
    for source_index, source in enumerate(sources, start=1):
        take_id = str(source.get("take_id") or "")
        label = f"assembly.sources[{source_index}]"
        source_path = resolve_asset(manifest_path, source.get("file"))
        declared_sha = str(source.get("sha256") or "").strip().lower()
        if source_path is None:
            errors.append(f"{label}.file está ausente")
            continue
        if not source_path.is_file():
            errors.append(f"{label}.file não existe: {source_path}")
            continue
        if not declared_sha:
            errors.append(f"{label}.sha256 está ausente")
            continue
        actual_sha = sha256_file(source_path)
        if actual_sha != declared_sha:
            errors.append(f"{label}.sha256 diverge do bitstream real")

        take = takes_by_id.get(take_id) or {}
        video = take.get("video") or {}
        active_path = resolve_asset(manifest_path, video.get("output_active"))
        if active_path != source_path:
            errors.append(f"{label}.file diverge do output_active aprovado do take {take_id}")
        if str(video.get("sha256") or "").strip().lower() != declared_sha:
            errors.append(f"{label}.sha256 diverge de take[{take_id}].video.sha256")
        owner = take.get("owner_take_approval") or {}
        if not approved_status(owner.get("status")):
            errors.append(f"take[{take_id}].owner_take_approval.status não está APPROVED")
        if str(owner.get("approved_file_sha256") or "").strip().lower() != declared_sha:
            errors.append(
                f"{label}.sha256 diverge do hash exato aprovado pelo proprietário"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bloqueia regressões de arte, direção e montagem em sequências live action do Maestro.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--stage", choices=("contract", "anchors", "assembly"), required=True)
    parser.add_argument(
        "--takes",
        nargs="+",
        help="No estágio anchors, valida somente os takes indicados da cadeia serial.",
    )
    args = parser.parse_args()

    if args.stage == "assembly" and args.takes:
        parser.error("--takes não pode limitar o gate final de assembly")

    manifest_path = args.manifest.resolve()
    data = load(manifest_path)
    selected_take_ids = set(args.takes) if args.takes else None
    known_take_ids = {take_id(take) for take in data.get("takes", [])}
    if selected_take_ids:
        unknown_take_ids = sorted(selected_take_ids - known_take_ids)
        if unknown_take_ids:
            parser.error(f"takes desconhecidos: {', '.join(unknown_take_ids)}")
    errors: list[str] = []
    check_contract(data, errors)
    if args.stage in ("anchors", "assembly"):
        check_anchors(data, errors, manifest_path, selected_take_ids)
    if args.stage == "assembly":
        check_assembly(data, errors, manifest_path)

    report = {
        "manifest": str(manifest_path),
        "stage": args.stage,
        "takes": sorted(selected_take_ids) if selected_take_ids else "ALL",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
