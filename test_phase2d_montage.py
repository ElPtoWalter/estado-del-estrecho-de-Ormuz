"""Montage contract regressions. Synthetic tone tests never call a TTS provider."""
import copy
import importlib.util
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import phase2_montage as montage
from phase2_voice.fixtures import load_pilot_fixture
from phase2_voice.input import build_voice_input
from phase2_voice.pipeline import make_metadata
from phase2_voice.schema import voice_config
from test_phase2b_voice import artifact_directory, tone

HAS_PILLOW = importlib.util.find_spec("PIL") is not None
HAS_TOOLS = all(shutil.which(name) for name in ("ffmpeg", "ffprobe", "rsvg-convert"))


@unittest.skipUnless(HAS_PILLOW, "Optional montage runtime not installed in this job")
class MontageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.material = {}
        for site in ("ormuz", "gibraltar"):
            package, script, provenance = load_pilot_fixture(site)
            config = voice_config("es", model="gemini-3.8-flash-tts", voice="es-es-advisor-2")
            value = build_voice_input(package, script, config=config)
            audio = tone(seconds=script["target_seconds"])
            cls.material[site] = (package, script, value, make_metadata(value, audio), audio)

    def prepared(self, site="gibraltar"):
        package, script, value, metadata, audio = self.material[site]
        frames = round(len(audio[44:]) / 2 / 24000 * montage.FPS)
        cues = montage.timeline(value, metadata, [], frames)
        snapshots = {name: "a" * 64 for name in montage.INPUT_NAMES}
        plan = montage.plan(package, script, value, metadata, snapshots, cues)
        return package, script, value, metadata, audio, cues, plan

    def test_both_sites_have_contiguous_complete_timeline(self):
        for site in self.material:
            *_, cues, plan = self.prepared(site)
            self.assertEqual(cues[0]["start_frame"], 0)
            self.assertEqual(cues[-1]["end_frame"], plan["video_frames"])
            self.assertTrue(all(c["end_frame"] - c["start_frame"] >= 30 for c in cues))

    def test_outro_uses_last_actual_scene_not_hardcoded_fifth(self):
        for site in self.material:
            _, script, *_, cues, _ = self.prepared(site)
            self.assertEqual(cues[-1]["visual_scene_id"], script["scenes"][-1]["scene_id"].replace("scene-", "visual-scene-"))

    def test_subtitles_preserve_complete_editorial_text(self):
        for site in self.material:
            _, _, value, *_, cues, _ = self.prepared(site)
            self.assertEqual(montage.normalize(" ".join(c["text"] for c in cues)),
                             montage.normalize(value["full_editorial_text"]))

    def test_two_line_subtitle_area_no_overflow(self):
        for site in self.material:
            *_, cues, _ = self.prepared(site)
            self.assertTrue(all(len(c["lines"]) <= 2 for c in cues))
            self.assertTrue(all(len(montage.wrap(row, 54, 880)) == 1 for c in cues for row in c["lines"]))

    def test_declared_approximation_and_review_guards(self):
        *_, plan = self.prepared()
        self.assertEqual(plan["alignment"], montage.ALIGNMENT)
        self.assertFalse(plan["publication_allowed"])
        self.assertEqual(plan["human_review_status"], "PENDING")
        self.assertEqual(plan["transcript_validation"], "NOT_RUN")
        self.assertEqual(plan["allowed_uses"], ["internal_preview"])
        self.assertEqual(plan["provider_requests"], 0)
        self.assertEqual(plan["audio_speed_factor"], 1)

    def test_plan_is_deterministic(self):
        self.assertEqual(self.prepared()[-1], self.prepared()[-1])

    def test_source_or_audio_change_creates_new_montage_identity(self):
        package, script, value, metadata, _, cues, plan = self.prepared()
        hashes = copy.deepcopy(plan["source_hashes"])
        hashes["audio-gemini.wav"] = "b" * 64
        self.assertNotEqual(plan["montage_id"], montage.plan(package, script, value, metadata, hashes, cues)["montage_id"])

    def test_cue_provenance_and_timing_tampering_rejected(self):
        _, _, value, *_, cues, plan = self.prepared()
        cases = [("text", "Invented claim"), ("source_ids", []), ("fact_ids", []),
                 ("visual_scene_id", "visual-scene-99"), ("source_scene_id", "scene-99"),
                 ("start_frame", 3), ("start_frame", False), ("end_frame", 1),
                 ("lines", ["different words"]), ("cue_id", "cue-999"), ("kind", "outro")]
        for key, change in cases:
            with self.subTest(key=key):
                bad = copy.deepcopy(cues)
                bad[0][key] = change
                with self.assertRaises(montage.MontageError):
                    montage.validate_cues(value, bad, plan["video_frames"])

    def test_system_fonts_are_rasterized_not_external_images(self):
        package, script, _, _, _, cues, plan = self.prepared()
        storyboard = montage.build_storyboard(package, script)
        text = montage.frame_svg(package, script, storyboard, plan, cues[0])
        self.assertNotIn("<image", text)
        self.assertNotIn("href=", text)
        self.assertNotIn("http", text.replace("http://www.w3.org/2000/svg", ""))
        self.assertIn(plan["historical_label"], text)
        self.assertIn("SIN PUBLICAR", text)

    def test_official_gibraltar_source_not_ormuz_sources(self):
        package, script, _, _, _, cues, plan = self.prepared()
        storyboard = montage.build_storyboard(package, script)
        cue = next(c for c in cues if c["source_scene_id"] == "scene-01")
        text = montage.frame_svg(package, script, storyboard, plan, cue)
        self.assertIn("Protección Civil España", text)
        self.assertNotIn("Bloomberg", text)
        for number in ("57024", "14140", "173"):
            self.assertIn(number, text)

    def test_uncertainty_is_labelled_explicitly(self):
        package, script, _, _, _, cues, plan = self.prepared()
        storyboard = montage.build_storyboard(package, script)
        cue = next(c for c in cues if c["source_scene_id"] == "scene-03")
        self.assertIn("INCERTIDUMBRE ABIERTA", montage.frame_svg(package, script, storyboard, plan, cue))

    def test_missing_audio_never_calls_provider(self):
        with artifact_directory() as temp, patch("phase2_voice.gemini.render_gemini", side_effect=AssertionError("no synthesis")) as provider:
            with self.assertRaises(montage.MontageError):
                montage.render_preview(Path(temp) / "missing", Path(temp) / "output",
                                       site="gibraltar", expected_audio_sha256="a" * 64)
            provider.assert_not_called()

    def test_inside_checkout_output_rejected_before_writing(self):
        with self.assertRaises(montage.MontageError):
            montage.render_preview(Path("/absent"), montage.REPO_ROOT / ".never-create",
                                   site="ormuz", expected_audio_sha256="a" * 64)
        self.assertFalse((montage.REPO_ROOT / ".never-create").exists())

    def test_wrong_explicit_hash_rejected(self):
        with artifact_directory() as temp:
            source = self.write_input(Path(temp))
            with self.assertRaises(montage.MontageError):
                montage.load_inputs(source, "gibraltar", "0" * 64)

    def test_wrong_site_rejected(self):
        with artifact_directory() as temp:
            source = self.write_input(Path(temp))
            with self.assertRaises(montage.MontageError):
                montage.load_inputs(source, "ormuz", montage.sha(self.material["gibraltar"][-1]))

    def test_accepted_audition_profile_reused_without_relabel(self):
        package, script, _, _, _, _, _ = self.prepared()
        config = voice_config("es", voice="es-es-advisor-2", profile_id="straitwatch_es_castilian_audition_v1")
        value = build_voice_input(package, script, config=config)
        self.assertEqual(value["voice_config"]["profile_id"], "straitwatch_es_castilian_audition_v1")

    def test_manual_workflow_has_no_generation_keys_or_schedule(self):
        text = (montage.REPO_ROOT / ".github/workflows/pilot-phase2d-montage.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertIn("actions: read", text)
        self.assertNotIn("  schedule:", text)
        self.assertNotIn("  push:", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("secrets.GEMINI", text)
        self.assertNotIn("pilot_phase2b_voice.py", text)
        self.assertIn("expected-audio-sha256", text)

    def write_input(self, base, site="gibraltar"):
        package, script, value, metadata, audio = self.material[site]
        source = base / "input"
        source.mkdir()
        for name, data in zip(montage.INPUT_NAMES, (package, script, value, metadata, audio)):
            if isinstance(data, bytes):
                (source / name).write_bytes(data)
            else:
                montage.write_json(source / name, data)
        return source

    @unittest.skipUnless(HAS_TOOLS, "External local render tools not installed in this job")
    def test_real_encode_cache_reuse_and_corruption_fail_closed(self):
        with artifact_directory() as temp, patch("phase2_voice.gemini.render_gemini", side_effect=AssertionError("no synthesis")) as provider:
            base = Path(temp)
            source = self.write_input(base)
            output = base / "output"
            checksum = montage.sha(self.material["gibraltar"][-1])
            first = montage.render_preview(source, output, site="gibraltar", expected_audio_sha256=checksum)
            self.assertEqual(first["validation_status"], "PASS")
            self.assertFalse(first["cache_hit"])
            second = montage.render_preview(source, output, site="gibraltar", expected_audio_sha256=checksum)
            self.assertTrue(second["cache_hit"])
            self.assertEqual(first["montage_id"], second["montage_id"])
            self.assertEqual((source / "audio-gemini.wav").read_bytes(), self.material["gibraltar"][-1])
            self.assertEqual(first["delivery"]["source_samples"], 35 * 24000)
            metadata = montage.read_json(output / "source/audio-metadata.json")
            self.assertEqual(metadata["human_review_status"], "PENDING")
            (output / "subtitles.srt").write_text("corrupt", encoding="utf-8")
            with self.assertRaises(montage.MontageError):
                montage.render_preview(source, output, site="gibraltar", expected_audio_sha256=checksum)
            provider.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
