"""Publication workflow and security regressions; only synthetic local fixtures."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from PIL import Image

import internet_publication as publication
import video_projects as projects


BRIEF = "Esse vídeo será feito para publicação na internet. Filme silencioso de 60 segundos, horizontal."
PLAN = {
    "audience": "Pessoas que gostam de fantasia e ainda não conhecem estes personagens.",
    "promise": "Mostrar se uma pequena chama resistirá à tempestade que se aproxima.",
    "emotion": "Curiosidade seguida de apreensão e alívio.",
    "opening": "Uma gota cai perto da chama, que se curva sem apagar; a mão a protege.",
    "alternativeOpening": "O reflexo da chama revela a tempestade nos olhos da personagem.",
    "progression": "Gotas intensificam; mãos protegem a chama; a personagem encontra abrigo.",
    "payoff": "Sob o abrigo a chama volta a iluminar o rosto da personagem.",
    "mobileFraming": "Manter o plano horizontal solicitado e a chama legível no centro do gesto.",
    "silentComprehension": "Gotas, gesto protetor e mudança de expressão comunicam o conflito sem som.",
    "constraints": "Preservar silêncio, duração de 60 segundos, horizontal e câmera contínua.",
}


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def install_synthetic_master(root: Path, project_id: str, *, approve: bool = True, vertical: bool = False) -> Path:
    """This approval is a test fixture, never a real owner's media decision."""
    directory = root / project_id
    take = directory / "takes" / "synthetic.mp4"
    size = "96x160" if vertical else "160x96"
    binary = shutil.which("ffmpeg")
    if not binary:
        raise unittest.SkipTest("ffmpeg required for bitstream integration test")
    subprocess.run([binary, "-nostdin", "-v", "error", "-f", "lavfi", "-i", f"color=c=navy:s={size}:r=24:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(take)],
                   capture_output=True, check=True, timeout=30,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    queue_path = directory / "take_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["takes"] = [{"id": "01", "maestro_status": "APPROVED", "target_duration_seconds": 1,
                       "video": {"output_active": str(take.resolve())}}]
    save_json(queue_path, queue)
    master = directory / "output" / "synthetic-master.mp4"
    shutil.copyfile(take, master)
    readiness = projects.get_project_assembly_readiness(root, project_id)
    projects.register_project_final_output(root, project_id,
        expected_source_fingerprint=readiness["sourceFingerprint"], record={
            "file": "output/synthetic-master.mp4", "duration_seconds": 1,
            "width": 96 if vertical else 160, "height": 160 if vertical else 96, "fps": 24,
            "video_codec": "h264", "sha256": publication._sha256(master),
            "qc_status": "TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING",
        })
    if approve:
        projects.review_project_final_output(root, project_id, decision="approve")
    return master


class IntentTests(unittest.TestCase):
    def test_affirmative_variants_preserve_silent_cinematic_constraints(self):
        for brief in (BRIEF, "Faça um vídeo sem som para publicação na internet", "Quero postar este vídeo no Threads",
                      "Produza um short sobre uma tempestade", "É para o YouTube Shorts", "Não só para a internet"):
            with self.subTest(brief=brief):
                detected = publication.detect_intent(brief)
                self.assertEqual(detected["mode"], "internet")
                self.assertEqual(detected["default_action"], "prepare_only")

    def test_negation_quotes_examples_and_questions_do_not_enable(self):
        for brief in ("Não publicar este vídeo na internet", "Filme para uso privado.",
                      'Leia: "esse vídeo será feito para publicação na internet"',
                      "Exemplo: esse vídeo será feito para publicação na internet",
                      "```\nPublique na internet\n```", "> Poste no Instagram", "Como publicar na internet?",
                      "A paisagem que vi na internet inspira este filme.", "Sem publicação na internet"):
            with self.subTest(brief=brief):
                self.assertEqual(publication.detect_intent(brief)["mode"], "standard")

    def test_last_general_correction_and_platform_exclusion(self):
        self.assertEqual(publication.detect_intent("Publique na internet. Não é para a internet.")["mode"], "standard")
        result = publication.detect_intent("Quero publicar na internet, mas não publicar no Threads")
        self.assertEqual(result["mode"], "internet")
        self.assertNotIn("threads", result["platforms"])
        self.assertEqual(publication.detect_intent("Para YouTube Shorts")["platforms"], ["youtube_shorts"])

    def test_explicit_selection_and_allowlists(self):
        self.assertEqual(publication.detect_intent(BRIEF, mode="standard")["mode"], "standard")
        self.assertEqual(publication.detect_intent("", mode="internet")["mode"], "internet")
        for args in ({"mode": {}}, {"mode": "viral"}, {"platforms": ["fake"]}, {"platforms": "threads"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                publication.detect_intent(BRIEF, **args)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pemara-publication-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        projects.create_project(self.root, name="Synthetic Internet", project_id="synthetic_internet", objective=BRIEF)
        self.project_id = "synthetic_internet"
        self.directory = self.root / self.project_id

    def current(self):
        return publication.get_publication(self.root, self.project_id)

    def ready(self):
        return publication.save_plan(self.root, self.project_id, {"expectedRevision": self.current()["revision"], "plan": PLAN})

    def package(self, **changes):
        payload = {"expectedRevision": self.current()["revision"], "platform": "threads", "title": "Chama na tempestade", "coverTimeSeconds": .1}
        payload.update(changes)
        return publication.create_package(self.root, self.project_id, payload)

    def test_legacy_read_is_non_mutating_and_create_does_not_queue(self):
        before = {p.relative_to(self.directory): p.read_bytes() for p in self.directory.rglob("*") if p.is_file()}
        current = self.current()
        self.assertFalse(current["readiness"]["readyForExistingGates"])
        self.assertEqual(current["safety"], {"autoPublish": False, "autoGenerate": False, "sourceMutation": False})
        self.assertEqual(before, {p.relative_to(self.directory): p.read_bytes() for p in self.directory.rglob("*") if p.is_file()})
        self.assertEqual(json.loads((self.directory / "take_queue.json").read_text())["takes"], [])
        manifest_path = self.directory / "project_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.pop("distribution_intent")
        save_json(manifest_path, manifest)
        before = manifest_path.read_bytes()
        self.assertEqual(self.current()["intent"]["mode"], "standard")
        self.assertEqual(projects.get_project(self.root, self.project_id)["distributionIntent"]["mode"], "standard")
        self.assertEqual(manifest_path.read_bytes(), before)

    def test_original_settings_survive_mode_changes_and_publication_brief(self):
        path = self.directory / "project_manifest.json"
        before = json.loads(path.read_text())
        projects.patch_project(self.root, self.project_id, {"distributionMode": "standard"})
        projects.patch_project(self.root, self.project_id, {"publicationBrief": "Agora este vídeo será publicado na internet"})
        after = json.loads(path.read_text())
        for key in ("objective", "duration_target_seconds", "preview_resolution", "final_resolution", "fps_preview", "fps_final", "audio"):
            self.assertEqual(before[key], after[key])
        self.assertEqual(after["distribution_intent"]["mode"], "internet")

    def test_incomplete_and_stale_direction_block_generation(self):
        with self.assertRaisesRegex(ValueError, "INTERNET_DIRECTION_REQUIRED"):
            publication.generation_direction(self.directory, "01", ["01"])
        ready = self.ready()
        self.assertTrue(ready["readiness"]["readyForExistingGates"])
        self.assertFalse(ready["readiness"]["humanApproved"])
        projects.patch_project(self.root, self.project_id, {"objective": "A personagem agora protege uma semente, mantendo o silêncio."})
        self.assertTrue(self.current()["readiness"]["briefChanged"])
        with self.assertRaisesRegex(ValueError, "INTERNET_DIRECTION_REQUIRED"):
            publication.generation_direction(self.directory, "01", ["01"])
        self.ready()
        self.assertTrue(self.current()["readiness"]["readyForExistingGates"])

    def test_opening_and_payoff_only_apply_to_their_take(self):
        self.ready()
        first = publication.generation_direction(self.directory, "01", ["01", "02", "03"])
        middle = publication.generation_direction(self.directory, "02", ["01", "02", "03"])
        last = publication.generation_direction(self.directory, "03", ["01", "02", "03"])
        self.assertIn(PLAN["opening"], first)
        self.assertNotIn(PLAN["opening"], middle)
        self.assertNotIn(PLAN["payoff"], middle)
        self.assertIn(PLAN["payoff"], last)
        self.assertNotIn(PLAN["alternativeOpening"], first)
        self.assertIn(PLAN["constraints"], middle)

    def test_real_h3_spec_gets_direction_without_changing_model_or_geometry(self):
        anchor = self.directory / "keyframes" / "synthetic.png"
        Image.new("RGB", (1280, 720), "navy").save(anchor)
        queue_path = self.directory / "take_queue.json"
        queue = json.loads(queue_path.read_text())
        queue["takes"] = [{"id": "01", "maestro_status": "PLANNED", "target_duration_seconds": 4,
                           "animation_prompt": "A hand shelters the flame as rain intensifies.",
                           "base_image": {"status": "approved_for_video", "file": str(anchor.resolve())},
                           "video_generation": {"profile": "minimax_h3_fl2va_int8_720p24"}}]
        save_json(queue_path, queue)
        with self.assertRaisesRegex(ValueError, "INTERNET_DIRECTION_REQUIRED"):
            projects.get_take_generation_spec(self.root, self.project_id, "01")
        self.ready()
        active = projects.get_take_generation_spec(self.root, self.project_id, "01")
        self.assertTrue(active["internetDirection"]["enabled"])
        self.assertIn(PLAN["opening"], active["prompt"])
        projects.patch_project(self.root, self.project_id, {"distributionMode": "standard"})
        standard = projects.get_take_generation_spec(self.root, self.project_id, "01")
        for key in ("profile", "width", "height", "frames", "fps"):
            if key in active:
                self.assertEqual(active[key], standard[key])
        self.assertFalse(standard["internetDirection"]["enabled"])

    def test_optimistic_revision_allows_one_writer_and_preserves_history(self):
        def write(value):
            try:
                publication.save_plan(self.root, self.project_id, {"expectedRevision": 0, "plan": {"audience": value}})
                return "saved"
            except publication.PublicationConflictError:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, ["Público de fantasia", "Público de cinema"]))
        self.assertCountEqual(results, ["saved", "conflict"])
        self.assertEqual(len(self.current()["planHistory"]), 1)

    def test_forged_approval_mass_assignment_and_path_escape_rejected(self):
        for payload in ({"expectedRevision": 0, "plan": PLAN, "humanApproved": True},
                        {"expectedRevision": 0, "plan": {"autoPublish": True}},
                        {"expectedRevision": 0, "plan": {"opening": "\x00"}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                publication.save_plan(self.root, self.project_id, payload)
        for project_id in ("..", "../outside", "x/../../outside", "C:\\outside", "x%2f.."):
            with self.subTest(project_id=project_id), self.assertRaises(ValueError):
                publication.get_publication(self.root, project_id)
        with self.assertRaises(ValueError):
            publication._local(self.directory, "../outside.json")
        with self.assertRaises(FileNotFoundError):
            publication.get_publication(self.root, "missing")

    def test_package_copies_bitstream_and_keeps_review_pending(self):
        self.ready()
        master = install_synthetic_master(self.root, self.project_id)
        original = master.read_bytes()
        manifest_before = (self.directory / "project_manifest.json").read_bytes()
        current = self.package(captionsSrt="1\n00:00:00,000 --> 00:00:00,800\nA chama resiste.\n")
        record = current["packages"][-1]
        self.assertEqual(record["status"], "PENDING_PUBLICATION_REVIEW")
        archive = publication.package_download(self.root, self.project_id, record["id"])
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(bundle.read("video.mp4"), original)
            self.assertIn("legendas.srt", bundle.namelist())
            self.assertIn("capa.jpg", bundle.namelist())
        self.assertEqual(master.read_bytes(), original)
        self.assertEqual((self.directory / "project_manifest.json").read_bytes(), manifest_before)
        with archive.open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "modificado"):
            publication.package_download(self.root, self.project_id, record["id"])

    def test_pending_or_changed_master_and_wrong_geometry_are_blocked(self):
        self.ready()
        master = install_synthetic_master(self.root, self.project_id, approve=False)
        with self.assertRaisesRegex(ValueError, "aprovado"):
            self.package()
        projects.review_project_final_output(self.root, self.project_id, decision="approve")
        with self.assertRaisesRegex(ValueError, "horizontal"):
            self.package(platform="youtube_shorts")
        with self.assertRaisesRegex(ValueError, "4K"):
            self.package(title="Chama em 4K")
        with self.assertRaisesRegex(ValueError, "duração"):
            self.package(coverTimeSeconds=2)
        master.write_bytes(master.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "hash"):
            self.package()
        self.assertEqual(self.current()["packages"], [])

    def test_download_blocks_revoked_master(self):
        self.ready()
        install_synthetic_master(self.root, self.project_id)
        package = self.package()["packages"][-1]
        path = self.directory / "project_manifest.json"
        manifest = json.loads(path.read_text())
        manifest["final_output"]["human_review"]["status"] = "REJECTED_BY_OWNER"
        save_json(path, manifest)
        with self.assertRaisesRegex(ValueError, "aprovado"):
            publication.package_download(self.root, self.project_id, package["id"])

    def test_failed_preparation_preserves_evidence_and_blocks_download(self):
        self.ready()
        install_synthetic_master(self.root, self.project_id)
        with mock.patch.object(publication, "_probe", return_value={"width": 160, "height": 96, "fps": "24/1", "durationSeconds": 1}), \
             mock.patch.object(publication.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 45)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.package()
        package = self.current()["packages"][-1]
        self.assertEqual(package["status"], "FAILED")
        self.assertTrue((self.directory / "edit" / "internet_packages" / package["id"]).is_dir())
        with self.assertRaises(FileNotFoundError):
            publication.package_download(self.root, self.project_id, package["id"])

    def test_metrics_are_manual_partial_platform_bound_and_not_summed(self):
        self.ready()
        install_synthetic_master(self.root, self.project_id)
        package = self.package()["packages"][-1]
        payload = {"expectedRevision": self.current()["revision"], "packageId": package["id"], "platform": "threads",
                   "postUrl": "https://www.threads.com/@fixture/post/test?utm_source=fixture", "windowHours": 24,
                   "metrics": {"views": 100, "reach": None, "eligibleStarts": 100, "viewersAt3Seconds": 65}}
        first = publication.record_measurement(self.root, self.project_id, payload)
        measurement = first["measurements"][0]
        self.assertEqual(measurement["rates"]["retainedAt3SecondsPercent"]["value"], 65)
        self.assertIsNone(measurement["metrics"]["reach"])
        self.assertNotIn("sharesPerReachPercent", measurement["rates"])
        self.assertEqual(measurement["sourceSha256"], package["sourceSha256"])
        payload.update(expectedRevision=first["revision"], postUrl="https://threads.com/@fixture/post/test", windowHours=48)
        second = publication.record_measurement(self.root, self.project_id, payload)
        self.assertEqual(second["measurementSummary"]["distinctPosts"], 1)
        self.assertEqual(second["measurementSummary"]["snapshots"], 2)
        self.assertEqual(second["measurementSummary"]["status"], "INCONCLUSIVE")
        payload.update(expectedRevision=second["revision"], platform="youtube", postUrl="https://youtube.com/watch?v=fixture")
        with self.assertRaisesRegex(ValueError, "plataforma"):
            publication.record_measurement(self.root, self.project_id, payload)

    def test_numeric_and_url_abuse_is_rejected_without_network(self):
        for value in (-1, True, float("nan"), float("inf"), 10 ** 1000, 1.1):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                publication._number(value, "count", integer=True)
        for url in ("http://threads.com/post/test", "https://threads.com.attacker.invalid/x", "https://user:secret@threads.com/x", "https://127.0.0.1/x", "javascript:alert(1)"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                publication._post_url(url, "threads")
        self.assertEqual(publication.metric_rates({"eligibleStarts": 0, "viewersAt3Seconds": 0}), {})
        self.assertEqual(publication._post_identity("https://youtu.be/abc?si=x"), publication._post_identity("https://youtube.com/shorts/abc"))


if __name__ == "__main__":
    unittest.main()
