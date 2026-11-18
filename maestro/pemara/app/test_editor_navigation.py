from pathlib import Path
import re
import json
import unittest


APP_ROOT = Path(__file__).resolve().parent


class EditorNavigationTest(unittest.TestCase):
    def test_retired_areas_are_removed_and_3d_has_a_dedicated_entry(self) -> None:
        source = (APP_ROOT / "assets" / "maestro.js").read_text(encoding="utf-8")
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        for retired in ('studio', 'audio-studio', 'game-studio'):
            self.assertNotIn(f'data-section="{retired}"', html)
            self.assertNotIn(f'data-section-jump="{retired}"', html)
            self.assertNotIn(f'id="section-{retired}"', html)
        self.assertNotIn('assets/editor-suite.', html)
        self.assertNotIn('assets/native-studios.', html)
        self.assertNotIn('MaestroEditorSuite', source)
        self.assertIn('data-section="models3d"', html)
        self.assertIn('id="section-models3d"', html)
        self.assertIn('window.MaestroModels3D?.activate()', source)

    def test_maestro_script_cache_key_contains_current_frontend_build(self) -> None:
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        build = json.loads((APP_ROOT / "assets" / "maestro-build.json").read_text(encoding="utf-8"))["build"]
        self.assertIn(f'assets/maestro.js?v={build}', html)

    def test_frontend_build_manifest_matches_script_and_has_refresh_guard(self) -> None:
        source = (APP_ROOT / "assets" / "maestro.js").read_text(encoding="utf-8")
        manifest = (APP_ROOT / "assets" / "maestro-build.json").read_text(encoding="utf-8")
        build = json.loads(manifest)["build"]
        self.assertIn(f'const MAESTRO_FRONTEND_BUILD = "{build}";', source)
        self.assertIn("reloadIfFrontendIsOutdated", source)
        self.assertIn('cache: "no-store"', source)

    def test_h3_controls_expose_profiles_vertical_and_sage_required(self) -> None:
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="gen-h3-quality-profile"', html)
        self.assertIn('value="h3_production" selected', html)
        self.assertIn('id="gen-h3-model-variant"', html)
        self.assertIn('value="fasth3_8step_v2"', html)
        self.assertIn('value="portrait"', html)
        self.assertIn('id="gen-h3-sage-status"', html)
        audio_input = re.search(r'<input id="gen-minimax-native-audio"[^>]*>', html)
        self.assertIsNotNone(audio_input)
        self.assertNotIn("checked", audio_input.group(0))

    def test_retired_reinstrument_is_absent_and_hyperframes_keeps_sidebar_order(self) -> None:
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        reinstrument = '<button class="nav-link" data-section="reinstrument"><span>03</span>Reinstrumentar</button>'
        # Sidebar additions may renumber entries without changing their order.
        hyperframes = re.search(r'<button class="nav-link" data-section="hyperframes"><span>\d+</span>HyperFrames</button>', html)
        engines = re.search(r'<button class="nav-link" data-section="tools"><span>\d+</span>Motores</button>', html)
        self.assertNotIn(reinstrument, html)
        self.assertNotIn('id="section-reinstrument"', html)
        self.assertNotIn('assets/music-reinstrument.', html)
        self.assertIsNotNone(hyperframes)
        self.assertIsNotNone(engines)
        self.assertLess(hyperframes.start(), engines.start())

    def test_hyperframes_section_contains_embedded_editor(self) -> None:
        html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        source = (APP_ROOT / "assets" / "maestro.js").read_text(encoding="utf-8")
        self.assertIn('id="section-hyperframes"', html)
        self.assertIn('id="hyperframes-frame"', html)
        self.assertIn('https://maestro.pemaratech.com.br:8443/', source)


if __name__ == "__main__":
    unittest.main()
