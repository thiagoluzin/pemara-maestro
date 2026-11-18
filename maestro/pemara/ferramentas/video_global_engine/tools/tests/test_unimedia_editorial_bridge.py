from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "unimedia_editorial_bridge.py"
SPEC = importlib.util.spec_from_file_location("unimedia_editorial_bridge", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)
ENGINE_ROOT = MODULE_PATH.parents[1]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _valid_plan() -> dict:
    return {
        "version": 1,
        "id": "rich-run",
        "title": "Acessibilidade em videos educacionais",
        "topic": "Acessibilidade",
        "language": "pt-BR",
        "style": "clinical-editorial",
        "canvas": {"width": 1920, "height": 1080, "fps": 30},
        "artDirection": "Azul profundo, laranja de contraste e superficies foscas.",
        "designBrief": "Infografico limpo, alto contraste e hierarquia visual acessivel.",
        "scenes": [
            {
                "id": "cena-1",
                "templateId": "clinical-cover-001",
                "title": "Acesso amplia aprendizagem",
                "narration": "Legendas, contraste e descricao visual ampliam o acesso ao conteudo.",
                "visibleText": ["Acesso", "Aprendizagem"],
                "durationSec": 4,
                "slide": "cover",
                "keywords": ["acesso"],
                "artBrief": "Interface educacional com legenda, contraste alto e leitor de tela.",
                "motionBrief": "Dolly lateral revela tres camadas e termina na legenda destacada.",
                "palette": {
                    "background": "#071431",
                    "surface": "#FFFFFF",
                    "primary": "#0A62A3",
                    "accent": "#FF8C05",
                    "textPrimary": "#FFFFFF",
                    "textSecondary": "#DCE7F3",
                },
                "assets": [],
                "cues": [{"at": 0, "text": "Acesso", "target": "title"}],
            },
            {
                "id": "cena-2",
                "templateId": "clinical-stat-002",
                "title": "Tres recursos combinados",
                "narration": "Legendas, audiodescricao e navegacao por teclado atuam em conjunto.",
                "visibleText": ["Legendas", "Audiodescricao", "Teclado"],
                "durationSec": 6,
                "slide": "content",
                "keywords": ["legendas", "teclado"],
                "artBrief": "Tres paineis conectados mostram legenda, audio e teclado.",
                "motionBrief": "Tracking frontal percorre os paineis com entrada sequencial dos itens.",
                "assets": [],
                "cues": [
                    {"at": 0, "text": "Legendas", "target": "bullet"},
                    {"at": 2, "text": "Audiodescricao", "target": "bullet"},
                    {"at": 4, "text": "Teclado", "target": "bullet"},
                ],
            },
        ],
        "createdAt": "2026-08-13T12:00:00Z",
        "warnings": [],
    }


def _valid_manifest() -> dict:
    return {
        "version": 1,
        "runId": "rich-run",
        "createdAt": "2026-08-13T12:00:01Z",
        "title": "Acessibilidade em videos educacionais",
        "topic": "Acessibilidade",
        "aspect": "16:9",
        "sceneCount": 2,
        "durationSec": 10,
        "degraded": [],
        "gates": {
            "roteiro": {
                "approvedBy": "human",
                "manifestSha": "a" * 64,
                "reviewer": "editor-humano",
            },
            "imagens": {"round": 1, "approved": 0, "rejected": 0},
        },
        "reuse": {"reused": 0, "generated": 0, "reuseRate": 0},
        "cost": {"usd": 0.42, "byProvider": {"nova-text": 0.42}},
    }


def _valid_factpack() -> dict:
    return {
        "version": 1,
        "topic": "Acessibilidade",
        "audience": "iniciante",
        "learningObjectives": ["Identificar recursos de acessibilidade"],
        "facts": [
            {
                "id": "fact-001",
                "claim": "Legendas ampliam o acesso ao conteudo falado.",
                "kind": "effect",
                "sourceRef": {
                    "documentId": "material-owner",
                    "chunkId": "material-owner#1",
                    "quote": "Legendas ampliam o acesso ao conteudo falado.",
                },
                "confidence": 0.9,
            }
        ],
        "forbiddenInferences": ["Nao afirmar conformidade legal automatica."],
        "sourceHash": "b" * 64,
    }


class UnimediaBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        _write_json(self.root / "plan.json", _valid_plan())
        _write_json(self.root / "manifest.json", _valid_manifest())
        _write_json(
            self.root / "cost.json",
            {
                "version": 1,
                "runId": "rich-run",
                "entries": [{"provider": "nova-text", "model": "test", "units": {}, "usd": 0.42}],
                "totals": {"usd": 0.42, "byProvider": {"nova-text": 0.42}},
            },
        )
        _write_json(self.root / "factpack.json", _valid_factpack())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_bundle_has_stable_identity_metrics_and_no_blockers(self) -> None:
        bundle = bridge.load_bundle(self.root)

        self.assertEqual(bundle.project_id, "rich_run")
        self.assertEqual(bundle.metrics["sceneCount"], 2)
        self.assertEqual(bundle.metrics["durationSeconds"], 10)
        self.assertEqual(bundle.metrics["templateUniqueRatio"], 1.0)
        self.assertEqual(bundle.metrics["factCount"], 1)
        self.assertEqual(bundle.blocking_issues, [])
        self.assertEqual(bundle.risk_issues, [])
        self.assertEqual(set(bundle.artifact_hashes), {"plan.json", "manifest.json", "cost.json", "factpack.json"})

    def test_contract_rejects_duplicate_scene_long_take_and_missing_briefs(self) -> None:
        plan = _valid_plan()
        plan["scenes"][1]["id"] = "cena-1"
        plan["scenes"][1]["durationSec"] = 14
        plan["scenes"][1].pop("artBrief")
        plan["scenes"][1].pop("motionBrief")
        _write_json(self.root / "plan.json", plan)

        bundle = bridge.load_bundle(self.root)
        codes = {issue.code for issue in bundle.blocking_issues}

        self.assertIn("scene-id-duplicate", codes)
        self.assertIn("scene-duration-policy", codes)
        self.assertIn("scene-art-brief-missing", codes)
        self.assertIn("scene-motion-brief-missing", codes)

    def test_auto_approval_degraded_run_and_missing_factpack_require_explicit_risk_acceptance(self) -> None:
        manifest = _valid_manifest()
        manifest["gates"]["roteiro"]["approvedBy"] = "auto"
        manifest["degraded"] = ["roteiro-heuristico", "render-still"]
        _write_json(self.root / "manifest.json", manifest)
        (self.root / "factpack.json").unlink()

        bundle = bridge.load_bundle(self.root)
        codes = {issue.code for issue in bundle.risk_issues}

        self.assertEqual(
            codes,
            {"source-auto-approved", "source-degraded", "factpack-missing"},
        )

    def test_asset_path_must_stay_inside_source_run_and_hash_must_match(self) -> None:
        outside = self.root.parent / "outside.png"
        outside.write_bytes(b"not-authorized")
        plan = _valid_plan()
        plan["scenes"][0]["assets"] = [
            {"kind": "image", "ref": str(outside), "sha256": "c" * 64, "role": "spot"}
        ]
        _write_json(self.root / "plan.json", plan)

        bundle = bridge.load_bundle(self.root)
        codes = {issue.code for issue in bundle.blocking_issues}

        self.assertIn("asset-outside-source", codes)

    def test_review_package_is_deterministic_and_stale_approval_is_rejected(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review_dir = self.root / "maestro-review"

        first = bridge.write_review_package(bundle, review_dir)
        first_bytes = first.manifest_path.read_bytes()
        second = bridge.write_review_package(bundle, review_dir)

        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(first_bytes, second.manifest_path.read_bytes())

        approval_path = review_dir / "approved.json"
        _write_json(
            approval_path,
            {
                "approved": True,
                "manifestSha256": "0" * 64,
                "reviewer": "owner",
                "approvedAt": "2026-08-13T13:00:00-03:00",
                "acceptedRisks": [],
                "importAssets": False,
            },
        )
        with self.assertRaisesRegex(bridge.BridgeError, "obsoleta"):
            bridge.validate_review_approval(approval_path, first, bundle)

    def test_review_approval_rejects_manifest_tampered_after_package_creation(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle)
        review.manifest_path.write_text("{}\n", encoding="utf-8")

        with self.assertRaisesRegex(bridge.BridgeError, "integridade|alterado"):
            bridge.validate_review_approval(approval_path, review, bundle)

    def _approved_review(self, bundle, *, import_assets: bool = False):
        review = bridge.write_review_package(bundle, self.root / "maestro-review")
        approval_path = review.directory / "approved.json"
        _write_json(
            approval_path,
            {
                "approved": True,
                "manifestSha256": review.manifest_sha256,
                "reviewer": "owner-reviewer",
                "approvedAt": "2026-08-13T13:00:00-03:00",
                "acceptedRisks": [issue.code for issue in bundle.risk_issues],
                "importAssets": import_assets,
            },
        )
        return review, approval_path

    def _authorization(self, *, assets: bool = False) -> Path:
        path = self.root / "authorization.json"
        scopes = ["generated_editorial_metadata"]
        if assets:
            scopes.append("generated_assets")
        _write_json(
            path,
            {
                "schemaVersion": "1.0",
                "sourceRepository": "flaviomartil/unimedia-engine",
                "authorizationBasis": "repository_owner_written_permission",
                "grantor": "repository-owner",
                "authorizedTo": "Pemara",
                "grantedAt": "2026-08-13T12:30:00-03:00",
                "scopes": scopes,
                "assetRightsConfirmed": assets,
                "evidenceReference": "email-owner-2026-08-13",
            },
        )
        return path

    def test_project_payload_maps_editorial_plan_to_locked_maestro_takes(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle)
        approval = bridge.validate_review_approval(approval_path, review, bundle)
        authorization = bridge.validate_source_authorization(self._authorization())

        manifest, queue, editorial = bridge.build_project_payloads(
            bundle,
            review,
            approval,
            authorization,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:05:00-03:00",
        )

        self.assertEqual(manifest["maestro_status"], "PLANNED")
        self.assertEqual(manifest["audio"]["mode"], "visual_only")
        self.assertEqual(manifest["editorial_bridge"]["review_manifest_sha256"], review.manifest_sha256)
        self.assertEqual(queue["primary_orchestration_policy"], "policies/primary_take_orchestration_h3_ltx25.json")
        self.assertEqual(len(queue["takes"]), 2)
        self.assertEqual(queue["takes"][0]["id"], "001")
        self.assertEqual(queue["takes"][1]["timeline_start_seconds"], 4)
        self.assertEqual(queue["takes"][0]["video_generation"]["profile"], "owner_selection_required")
        self.assertTrue(queue["takes"][0]["video_generation"]["engine_selection_required"])
        self.assertFalse(queue["takes"][0]["video_generation"]["fallback_allowed"])
        self.assertEqual(queue["takes"][0]["shot_contract"]["provider_style"], bridge.BRIDGE_VERSION)
        self.assertEqual(queue["takes"][0]["video_generation"]["frames"], 0)
        self.assertEqual(queue["takes"][1]["video_generation"]["frames"], 0)
        self.assertFalse(queue["takes"][0]["audio_directive"]["usage_authorized"])
        self.assertEqual(queue["takes"][0]["base_image"]["status"], "pending_human_qc")
        self.assertEqual(editorial["overlay_plan"]["scenes"][1]["visibleText"], ["Legendas", "Audiodescricao", "Teclado"])

    def test_apply_creates_native_project_atomically_and_is_idempotent(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle)
        authorization_path = self._authorization()
        projects_root = self.root / "maestro-projects"

        created = bridge.apply_project(
            bundle,
            review,
            approval_path,
            authorization_path,
            projects_root=projects_root,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:05:00-03:00",
        )
        repeated = bridge.apply_project(
            bundle,
            review,
            approval_path,
            authorization_path,
            projects_root=projects_root,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:10:00-03:00",
        )

        self.assertTrue(created.created)
        self.assertFalse(repeated.created)
        project = projects_root / "rich_run"
        self.assertEqual(created.project_dir, project.resolve())
        self.assertTrue((project / "project_manifest.json").is_file())
        self.assertTrue((project / "take_queue.json").is_file())
        self.assertTrue((project / "input" / "editorial_source" / "plan.json").is_file())
        self.assertTrue((project / "editorial" / "factpack.json").is_file())
        self.assertTrue((project / "editorial" / "overlay_plan.json").is_file())
        self.assertTrue((project / "qc" / "editorial_import" / "editorial-review.manifest.json").is_file())
        integrity_path = project / "qc" / "editorial_import" / "import-integrity.json"
        self.assertTrue(integrity_path.is_file())
        integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
        self.assertIn("take_queue.json", integrity["files"])
        self.assertEqual(list((project / "input" / "editorial_assets").glob("*")), [])

        studio_root = ENGINE_ROOT.parents[1] / "services" / "studio"
        if str(studio_root) not in sys.path:
            sys.path.insert(0, str(studio_root))
        import ltx_review_pipeline
        import video_projects

        listed = video_projects.list_projects(projects_root)
        takes = video_projects.list_takes(projects_root, "rich_run")
        policy = ltx_review_pipeline.load_ltx_review_pipeline_policy(
            project,
            "ltx-2.5-22b-distilled-transformer-nvfp4.safetensors",
        )
        self.assertEqual(listed["data"][0]["projectId"], "rich_run")
        self.assertEqual(takes["data"][0]["status"], "PLANNED")
        self.assertFalse(takes["data"][0]["canGenerate"])
        self.assertEqual(policy["version"], "h3_ltx25_rife425_midpoint48_retime60_v1")
        self.assertEqual(policy["source_resolution"], {"width": 960, "height": 544})

    def test_idempotent_reapply_rejects_a_corrupted_existing_project(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle)
        authorization_path = self._authorization()
        projects_root = self.root / "maestro-projects-corruption"
        created = bridge.apply_project(
            bundle,
            review,
            approval_path,
            authorization_path,
            projects_root=projects_root,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:05:00-03:00",
        )
        (created.project_dir / "take_queue.json").unlink()

        with self.assertRaisesRegex(bridge.BridgeError, "nao corresponde|integridade"):
            bridge.apply_project(
                bundle,
                review,
                approval_path,
                authorization_path,
                projects_root=projects_root,
                engine_root=ENGINE_ROOT,
                now="2026-08-13T13:10:00-03:00",
            )

    def test_idempotent_reapply_rejects_changed_human_approval(self) -> None:
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle)
        authorization_path = self._authorization()
        projects_root = self.root / "maestro-projects-approval-change"
        bridge.apply_project(
            bundle,
            review,
            approval_path,
            authorization_path,
            projects_root=projects_root,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:05:00-03:00",
        )
        changed = json.loads(approval_path.read_text(encoding="utf-8"))
        changed["reviewer"] = "different-reviewer"
        _write_json(approval_path, changed)

        with self.assertRaisesRegex(bridge.BridgeError, "nao corresponde|integridade"):
            bridge.apply_project(
                bundle,
                review,
                approval_path,
                authorization_path,
                projects_root=projects_root,
                engine_root=ENGINE_ROOT,
                now="2026-08-13T13:10:00-03:00",
            )

    def test_asset_import_requires_separate_rights_and_stays_pending_human_qc(self) -> None:
        asset = self.root / "assets" / "cena-1.png"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"synthetic-owned-image")
        asset_sha = hashlib.sha256(asset.read_bytes()).hexdigest()
        video_asset = self.root / "assets" / "cena-1.mp4"
        video_asset.write_bytes(b"synthetic-owned-video")
        video_sha = hashlib.sha256(video_asset.read_bytes()).hexdigest()
        plan = _valid_plan()
        plan["scenes"][0]["assets"] = [
            {"kind": "image", "ref": str(asset), "sha256": asset_sha, "role": "spot"},
            {"kind": "video", "ref": str(video_asset), "sha256": video_sha, "role": "b-roll"},
        ]
        _write_json(self.root / "plan.json", plan)
        _write_json(
            self.root / "asset-rights.json",
            {
                "schemaVersion": "1.0",
                "assets": [
                    {
                        "path": "assets/cena-1.png",
                        "sha256": asset_sha,
                        "license": "Proprietary - written permission",
                        "rightsHolder": "repository-owner",
                        "sourceReference": "run-rich-run/cena-1",
                        "approvedForImport": True,
                        "reviewedBy": "rights-reviewer",
                        "reviewedAt": "2026-08-13T12:45:00-03:00",
                    },
                    {
                        "path": "assets/cena-1.mp4",
                        "sha256": video_sha,
                        "license": "Proprietary - written permission",
                        "rightsHolder": "repository-owner",
                        "sourceReference": "run-rich-run/cena-1-video",
                        "approvedForImport": True,
                        "reviewedBy": "rights-reviewer",
                        "reviewedAt": "2026-08-13T12:45:00-03:00",
                    }
                ],
            },
        )
        bundle = bridge.load_bundle(self.root)
        review, approval_path = self._approved_review(bundle, import_assets=True)
        projects_root = self.root / "projects-with-assets"

        result = bridge.apply_project(
            bundle,
            review,
            approval_path,
            self._authorization(assets=True),
            projects_root=projects_root,
            engine_root=ENGINE_ROOT,
            now="2026-08-13T13:05:00-03:00",
        )

        imported = list((result.project_dir / "input" / "editorial_assets").glob("*.png"))
        imported_videos = list((result.project_dir / "input" / "editorial_assets").glob("*.mp4"))
        self.assertEqual(len(imported), 1)
        self.assertEqual(len(imported_videos), 1)
        sidecar = json.loads(imported[0].with_suffix(".json").read_text(encoding="utf-8"))
        queue = json.loads((result.project_dir / "take_queue.json").read_text(encoding="utf-8"))
        catalog = json.loads((result.project_dir / "editorial" / "asset_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(sidecar["validation_status"], "pending_human_qc")
        self.assertTrue(sidecar["approval_required_before_video"])
        self.assertEqual(queue["takes"][0]["base_image"]["status"], "pending_human_qc")
        self.assertEqual(len(queue["takes"][0]["base_image"]["candidate_assets"]), 1)
        self.assertTrue(queue["takes"][0]["base_image"]["candidate_assets"][0]["file"].endswith(".png"))
        self.assertEqual({entry["kind"] for entry in catalog["entries"]}, {"image", "video"})
        self.assertTrue(all(entry["status"] == "pending_human_qc" for entry in catalog["entries"]))

    def test_asset_scope_cannot_be_inferred_from_editorial_authorization(self) -> None:
        with self.assertRaisesRegex(bridge.BridgeError, "generated_assets"):
            bridge.validate_source_authorization(self._authorization(), import_assets=True)

    def test_cli_emits_accessible_review_status_without_applying(self) -> None:
        review_dir = self.root / "cli-review"
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = bridge.main([str(self.root), "--review-dir", str(review_dir)])

        self.assertEqual(result, 0)
        self.assertIn("STATUS=AWAITING_HUMAN_REVIEW", stdout.getvalue())
        self.assertIn("GPU_STARTED=NO", stdout.getvalue())
        self.assertIn("AUDIO_MODE=VISUAL_ONLY", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue((review_dir / "editorial-review.manifest.json").is_file())

    def test_cli_returns_blocked_when_contract_has_unresolved_errors(self) -> None:
        plan = _valid_plan()
        plan["scenes"][0]["motionBrief"] = ""
        _write_json(self.root / "plan.json", plan)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = bridge.main(
                [str(self.root), "--review-dir", str(self.root / "blocked-review")]
            )

        self.assertEqual(result, 2)
        self.assertIn("STATUS=BLOCKED", stdout.getvalue())
        self.assertIn("scene-motion-brief-missing", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_json_size_limit_is_enforced_before_parsing(self) -> None:
        with patch.object(bridge, "MAX_JSON_BYTES", 100):
            with self.assertRaisesRegex(bridge.BridgeError, "limite"):
                bridge.load_bundle(self.root)

    def test_non_finite_json_number_is_rejected_at_the_input_boundary(self) -> None:
        plan = _valid_plan()
        plan["scenes"][0]["palette"]["background"] = float("nan")
        _write_json(self.root / "plan.json", plan)

        with self.assertRaisesRegex(bridge.BridgeError, "JSON|numerica|invalido"):
            bridge.load_bundle(self.root)

    def test_executable_asset_is_rejected_even_when_hash_matches(self) -> None:
        asset = self.root / "assets" / "payload.exe"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"MZ-synthetic")
        asset_sha = hashlib.sha256(asset.read_bytes()).hexdigest()
        plan = _valid_plan()
        plan["scenes"][0]["assets"] = [
            {"kind": "image", "ref": str(asset), "sha256": asset_sha, "role": "spot"}
        ]
        _write_json(self.root / "plan.json", plan)

        bundle = bridge.load_bundle(self.root)

        self.assertIn("asset-media-type", {issue.code for issue in bundle.blocking_issues})

    def test_overlay_text_and_cues_must_be_bounded_and_timed_inside_scene(self) -> None:
        plan = _valid_plan()
        plan["scenes"][0]["visibleText"] = ["ok", {"html": "nao"}]
        plan["scenes"][0]["cues"] = [
            {"at": 9, "text": "fora da cena", "target": "title"}
        ]
        _write_json(self.root / "plan.json", plan)

        bundle = bridge.load_bundle(self.root)
        codes = {issue.code for issue in bundle.blocking_issues}

        self.assertIn("scene-visible-text-invalid", codes)
        self.assertIn("scene-cue-timing", codes)


if __name__ == "__main__":
    unittest.main()
