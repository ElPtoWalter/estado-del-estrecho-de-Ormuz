from __future__ import annotations

import copy
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from phase2_video.script import generate_local_script
from phase2_visual.render import render_storyboard
from phase2_visual.storyboard import build_storyboard
from test_video_support import package


ROOT = Path(__file__).resolve().parent


class VisualRenderTests(unittest.TestCase):
    def setUp(self):
        self.package = package()
        self.script = generate_local_script(self.package)
        self.storyboard = build_storyboard(self.package, self.script)
        self.output = ROOT / ".phase2c-render-test" / "assets"

    def tearDown(self):
        shutil.rmtree(self.output.parent, ignore_errors=True)

    def test_renderer_creates_one_safe_original_svg_per_scene(self):
        manifest = render_storyboard(self.storyboard, self.output)
        self.assertEqual(len(manifest["assets"]), len(self.storyboard["scenes"]))
        self.assertFalse(manifest["network_used"])
        self.assertFalse(manifest["external_assets_used"])
        self.assertFalse(manifest["publication_allowed"])
        for asset in manifest["assets"]:
            path = self.output.parent / asset["file"]
            root = ET.fromstring(path.read_text(encoding="utf-8"))
            self.assertTrue(root.tag.endswith("svg"))
            self.assertEqual(asset["rights_status"], "cleared")
            self.assertEqual(asset["allowed_uses"], ["internal_preview"])
            lowered = path.read_text(encoding="utf-8").casefold()
            self.assertNotIn("<image", lowered)
            self.assertNotIn("<script", lowered)
            self.assertNotIn("foreignobject", lowered)

    def test_schematic_map_is_explicitly_not_for_navigation(self):
        render_storyboard(self.storyboard, self.output)
        map_scene = next(
            scene for scene in self.storyboard["scenes"]
            if scene["resolved_template"] == "schematic-map"
        )
        text = (self.output / f'{map_scene["scene_id"]}.svg').read_text(encoding="utf-8")
        self.assertIn("NO APTO PARA NAVEGACIÓN", text)

    def test_renderer_rejects_non_assets_directory_and_stale_files(self):
        with self.assertRaisesRegex(ValueError, "must-be-assets"):
            render_storyboard(self.storyboard, self.output.parent / "frames")
        self.output.mkdir(parents=True)
        (self.output / "stale.svg").write_text("stale", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must-be-empty"):
            render_storyboard(self.storyboard, self.output)

    def test_renderer_rejects_a_tampered_storyboard_directly(self):
        changed = copy.deepcopy(self.storyboard)
        changed["publication_allowed"] = True
        with self.assertRaisesRegex(ValueError, "invalid-storyboard-for-render"):
            render_storyboard(changed, self.output)


if __name__ == "__main__":
    unittest.main()
