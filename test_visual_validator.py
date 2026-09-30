from __future__ import annotations

import copy
import shutil
import unittest
from pathlib import Path

from phase2_video.script import generate_local_script
from phase2_visual.render import render_storyboard
from phase2_visual.schema import storyboard_content_hash, storyboard_id
from phase2_visual.storyboard import build_storyboard
from phase2_visual.validator import validate_storyboard, validate_visual_manifest
from test_video_support import package


ROOT = Path(__file__).resolve().parent


def reseal_storyboard(storyboard: dict) -> dict:
    result = copy.deepcopy(storyboard)
    digest = storyboard_content_hash(result)
    result["content_hash"] = digest
    result["storyboard_id"] = storyboard_id(result["site"], digest)
    return result


class VisualValidatorTests(unittest.TestCase):
    def setUp(self):
        self.package = package()
        self.script = generate_local_script(self.package)
        self.storyboard = build_storyboard(self.package, self.script)
        self.output = ROOT / ".phase2c-validator-test"

    def tearDown(self):
        shutil.rmtree(self.output, ignore_errors=True)

    def test_valid_storyboard_passes(self):
        report = validate_storyboard(self.package, self.script, self.storyboard)
        self.assertEqual(report["validation_status"], "PASS")

    def test_timeline_gap_is_rejected_even_when_resealed(self):
        changed = copy.deepcopy(self.storyboard)
        changed["scenes"][1]["start_ms"] += 1
        changed = reseal_storyboard(changed)
        report = validate_storyboard(self.package, self.script, changed)
        self.assertEqual(report["validation_status"], "FAIL")
        self.assertIn("TIMELINE_GAP", report["validation_errors"])
        self.assertIn("NON_DETERMINISTIC_STORYBOARD", report["validation_errors"])

    def test_traceability_change_is_rejected_even_when_resealed(self):
        changed = copy.deepcopy(self.storyboard)
        changed["scenes"][0]["fact_ids"] = []
        changed = reseal_storyboard(changed)
        report = validate_storyboard(self.package, self.script, changed)
        self.assertIn("NON_DETERMINISTIC_STORYBOARD", report["validation_errors"])

    def test_valid_manifest_and_assets_pass(self):
        manifest = render_storyboard(self.storyboard, self.output / "assets")
        report = validate_visual_manifest(
            self.package, self.script, self.storyboard, manifest, self.output
        )
        self.assertEqual(report["validation_status"], "PASS")

    def test_modified_svg_is_rejected(self):
        manifest = render_storyboard(self.storyboard, self.output / "assets")
        first = self.output / manifest["assets"][0]["file"]
        first.write_text(first.read_text(encoding="utf-8") + "<!-- changed -->", encoding="utf-8")
        report = validate_visual_manifest(
            self.package, self.script, self.storyboard, manifest, self.output
        )
        self.assertIn("ASSET_HASH", report["validation_errors"])

    def test_external_image_element_is_rejected_after_hash_update(self):
        manifest = render_storyboard(self.storyboard, self.output / "assets")
        first = self.output / manifest["assets"][0]["file"]
        text = first.read_text(encoding="utf-8").replace(
            "</svg>", '<image href="https://example.invalid/a.jpg"/></svg>'
        )
        first.write_text(text, encoding="utf-8")
        from phase2_visual.schema import sha256_file, visual_manifest_content_hash, visual_manifest_id
        manifest["assets"][0]["sha256"] = sha256_file(first)
        manifest["assets"][0]["bytes"] = first.stat().st_size
        digest = visual_manifest_content_hash(manifest)
        manifest["content_hash"] = digest
        manifest["manifest_id"] = visual_manifest_id(digest)
        report = validate_visual_manifest(
            self.package, self.script, self.storyboard, manifest, self.output
        )
        self.assertIn("SVG_UNSAFE", report["validation_errors"])


if __name__ == "__main__":
    unittest.main()
