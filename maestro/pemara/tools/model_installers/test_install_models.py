from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import install_models as installer


class ModelInstallerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lock = installer.load_lock()

    def test_lock_has_only_pinned_allowlisted_sources(self) -> None:
        installer.validate_lock(self.lock)
        self.assertGreaterEqual(len(self.lock["artifacts"]), 20)
        for item in self.lock["artifacts"]:
            if item["kind"].startswith("hf_"):
                self.assertEqual(len(item["revision"]), 40)
            if item["kind"] != "hf_snapshot":
                self.assertTrue(
                    len(item.get("sha256", "")) == 64
                    or item.get("integrity_source") == "hf_lfs_oid"
                )
                self.assertGreater(item["expected_bytes"], 0)

    def test_all_production_components_are_present(self) -> None:
        components = {item["component"] for item in self.lock["artifacts"]}
        self.assertEqual(components, {"h3", "shared", "qwen", "rife", "foley", "wan_animate"})

    def test_no_removed_ltx_weights_remain_in_installer(self) -> None:
        legacy = [
            item
            for item in self.lock["artifacts"]
            if "ltx-2.3" in str(item.get("filename") or "").casefold()
        ]
        self.assertEqual(len(legacy), 0)
        for item in legacy:
            self.assertEqual(item["classification"], "LTX25_COMPATIBILITY_ASSET")
            self.assertIn("ic-lora", item["filename"].casefold())
            self.assertTrue(item["ltx25_consumers"])

    def test_shared_gemma_uses_offloaded_model_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            layout = installer.build_layout(Path(temp) / "Pemara")
            for item in self.lock["artifacts"]:
                if item["component"] == "shared":
                    self.assertEqual(item["destination_root"], "comfy_offloaded_models")

    def test_destination_cannot_escape_target_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            layout = installer.build_layout(Path(temp) / "Pemara")
            item = dict(self.lock["artifacts"][0])
            item["destination_filename"] = "../../fora.safetensors"
            with self.assertRaises(ValueError):
                installer.destination_for(item, layout)

    def test_hf_remote_filename_can_map_to_runtime_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            layout = installer.build_layout(Path(temp) / "Pemara")
            item = next(
                artifact
                for artifact in self.lock["artifacts"]
                if artifact["id"] == "wan22_animate_14b_bf16"
            )
            destination = installer.destination_for(item, layout)
            self.assertEqual(
                destination,
                layout.comfy_models
                / "diffusion_models"
                / "wan2.2_animate_14B_bf16.safetensors",
            )

    def test_verify_file_checks_sha256_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tiny.bin"
            payload = b"pemara-model-installer"
            path.write_bytes(payload)
            item = {
                "id": "tiny",
                "expected_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            state = {"schema_version": 1, "artifacts": {}}
            valid, reason = installer.verify_file(item, path, state, use_cache=False)
            self.assertTrue(valid, reason)
            self.assertIn("tiny", state["artifacts"])

    def test_zip_traversal_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "hostile.zip"
            destination = Path(temp) / "out"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.txt", "blocked")
            with self.assertRaises(RuntimeError):
                installer.safe_extract_zip(archive, destination)

    def test_batch_launchers_are_relocatable_and_support_dry_run(self) -> None:
        expected = {
            "00_DIAGNOSTICAR_PC.bat",
            "01_INSTALAR_H3.bat",
            "02_INSTALAR_QWEN_H3.bat",
            "03_INSTALAR_RIFE_FHD60.bat",
            "04_INSTALAR_FOLEY_XXL.bat",
            "INSTALAR_TUDO_MODELOS.bat",
            "VERIFICAR_MODELOS.bat",
        }
        for name in expected:
            content = (installer.SCRIPT_DIR / name).read_text(encoding="utf-8")
            self.assertIn("%~dp0install_models.py", content)
            self.assertIn("--target-root", content)
        readme = (installer.SCRIPT_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("--dry-run", readme)

    def test_manifest_contains_no_secret_fields(self) -> None:
        serialized = json.dumps(self.lock).casefold()
        for forbidden in ("hf_token", "api_key", "password", "authorization"):
            self.assertNotIn(forbidden, serialized)

    def test_foley_docker_build_uses_fixed_image_and_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            layout = installer.build_layout(Path(temp) / "Pemara")
            source = layout.repo_root / "ferramentas" / "audio_neural" / "HunyuanVideo-Foley"
            dockerfile = layout.repo_root / "ferramentas" / "audio_neural" / "hunyuan_gpu" / "Dockerfile"
            source.mkdir(parents=True)
            dockerfile.parent.mkdir(parents=True)
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            with (
                mock.patch.object(installer, "docker_image_exists", side_effect=(False, True)),
                mock.patch.object(installer.subprocess, "run") as run,
            ):
                installer.build_foley_image(
                    layout,
                    rebuild=False,
                    dry_run=False,
                    log=mock.Mock(),
                )
            command = run.call_args.args[0]
            self.assertEqual(command[:3], ["docker", "build", "--pull"])
            self.assertIn(installer.FOLEY_IMAGE, command)
            self.assertNotIn("shell=True", repr(run.call_args))


if __name__ == "__main__":
    unittest.main()
