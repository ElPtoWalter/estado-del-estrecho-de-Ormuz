"""Manual internal montage of immutable 2A/2B inputs; no TTS, news fetch or publishing."""
from __future__ import annotations

import argparse
import array
import functools
import hashlib
import json
import math
import re
import shutil
import subprocess
import wave
from pathlib import Path
from xml.sax.saxutils import escape

from phase2_visual.render import _template_art, render_storyboard
from phase2_visual.schema import load_visual_rules
from phase2_visual.storyboard import build_storyboard
from phase2_visual.validator import validate_storyboard, validate_visual_manifest
from phase2_voice.pipeline import audit_output
from phase2_voice.validator import validate_audio
from phase2_video.schema import parse_utc

VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parent
FPS = 30
INPUT_NAMES = ("video-package.json", "script.json", "voice-input.json", "audio-metadata.json", "audio-gemini.wav")
SITES = {"ormuz": "Ormuz", "gibraltar": "Gibraltar"}
ALIGNMENT = "proportional-estimate-with-silence-snapping-NOT-ASR"


class MontageError(Exception):
    """Only closed diagnostic codes leave the CLI boundary."""


def fail(code):
    raise MontageError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        fail("INVALID_INPUT_FILE")
    value = json.loads(path.read_text(encoding="utf-8"))
    audit_output(canonical(value))
    return value


def write_json(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    audit_output(text)
    path.write_text(text, encoding="utf-8", newline="\n")


def normalize(text):
    return " ".join(text.split())


def load_inputs(directory, site, expected_sha):
    if site not in SITES or not re.fullmatch(r"[0-9a-f]{64}", expected_sha or ""):
        fail("INVALID_EXPLICIT_INPUT")
    if directory.is_symlink() or not directory.is_dir():
        fail("INPUT_DIRECTORY_REQUIRED")
    snapshots = {}
    for name in INPUT_NAMES:
        path = directory / name
        limit = 20 * 1024 * 1024 if name.endswith(".wav") else 2 * 1024 * 1024
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
            fail("INVALID_INPUT_FILE")
        snapshots[name] = sha(path.read_bytes())
    if snapshots["audio-gemini.wav"] != expected_sha:
        fail("EXPLICIT_AUDIO_HASH_MISMATCH")
    package, script, value, metadata = [read_json(directory / name) for name in INPUT_NAMES[:4]]
    if package.get("site") != site or script.get("language") != "es":
        fail("SITE_OR_LANGUAGE_MISMATCH")
    config = value.get("voice_config", {})
    if config.get("voice") != "es-es-advisor-2" or config.get("profile_id") not in (
            "straitwatch_es_v2", "straitwatch_es_castilian_audition_v1"):
        fail("APPROVED_VOICE_REQUIRED")
    data = (directory / "audio-gemini.wav").read_bytes()
    report = validate_audio(package, script, value, data, metadata)
    if report["validation_status"] != "PASS":
        fail("UPSTREAM_AUDIO_INVALID")
    if metadata["audio_metrics"]["sample_rate_hz"] != 24000:
        fail("NATIVE_24KHZ_REQUIRED")
    return package, script, value, metadata, snapshots, report


def font_files():
    candidates = [
        (Path("/usr/share/fonts/truetype/liberation2"), "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        (Path("/usr/share/fonts/truetype/liberation"), "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        (Path("C:/Windows/Fonts"), "arial.ttf", "arialbd.ttf"),
    ]
    for root, regular, bold in candidates:
        if (root / regular).is_file() and (root / bold).is_file():
            return root / regular, root / bold
    fail("SYSTEM_FONT_REQUIRED")


@functools.lru_cache(maxsize=16)
def font(size, bold=False):
    from PIL import ImageFont
    files = font_files()
    return ImageFont.truetype(str(files[bool(bold)]), size)


def wrap(text, size, width, bold=False):
    rows = []
    face = font(size, bold)
    for word in text.split():
        if face.getlength(word) > width:
            fail("TEXT_OVERFLOW")
        if rows and face.getlength(rows[-1] + " " + word) <= width:
            rows[-1] += " " + word
        else:
            rows.append(word)
    return rows


def chunks(text):
    words = text.split()

    @functools.lru_cache(None)
    def partition(start):
        if start == len(words):
            return 0, []
        best = None
        for end in range(start + min(3, len(words)), min(len(words), start + 14) + 1):
            phrase = " ".join(words[start:end])
            if len(wrap(phrase, 54, 880)) > 2:
                break
            rest = partition(end)
            if rest is None:
                continue
            score = (len(phrase) - 60) ** 2 / 60 + rest[0]
            if words[end - 1].endswith((".", ":", ";")):
                score -= 4
            if best is None or score < best[0]:
                best = score, [phrase, *rest[1]]
        return best

    selected = partition(0)
    if selected is None:
        fail("SUBTITLE_LAYOUT_OVERFLOW")
    return selected[1]


def silence_gaps(path):
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        samples = array.array("h", audio.readframes(audio.getnframes()))
    window = rate // 100
    start, gaps = None, []
    flags = []
    for offset in range(0, len(samples), window):
        block = samples[offset:offset + window]
        rms = math.sqrt(sum(x * x for x in block) / len(block)) / 32768
        flags.append(rms < 10 ** (-38 / 20))
    for index, quiet in enumerate([*flags, False]):
        if quiet and start is None:
            start = index
        elif not quiet and start is not None:
            if index - start >= 15:
                gaps.append({"start": start / 100, "end": index / 100,
                             "midpoint": (start + index) / 200})
            start = None
    return gaps


def timeline(value, metadata, gaps, total_frames):
    bounds = [0]
    for segment in metadata["segment_map"][:-1]:
        estimate = segment["estimated_end_seconds"]
        candidates = [g["midpoint"] for g in gaps if g["end"] - g["start"] >= .65
                      and abs(g["midpoint"] - estimate) <= 2.5]
        if not candidates:
            candidates = [g["midpoint"] for g in gaps if abs(g["midpoint"] - estimate) <= .8]
        chosen = min(candidates, key=lambda t: abs(t - estimate)) if candidates else estimate
        bounds.append(round(chosen * FPS))
    bounds.append(total_frames)
    if any(b <= a for a, b in zip(bounds, bounds[1:])):
        fail("SEGMENT_TIMELINE_INVALID")
    scene_ids = [s["scene_id"] for s in value["segments"] if s["kind"] == "scene"]
    cues = []
    for segment, first, last in zip(value["segments"], bounds, bounds[1:]):
        texts = chunks(segment["editorial_text"])
        weights = [len(t.split()) for t in texts]
        cumulative, weight_sum = 0, sum(weights)
        for text, weight in zip(texts, weights):
            start = first + round((last - first) * cumulative / weight_sum)
            cumulative += weight
            end = first + round((last - first) * cumulative / weight_sum)
            scene = segment["scene_id"] or (scene_ids[0] if segment["kind"] == "hook" else scene_ids[-1])
            cues.append({"cue_id": f"cue-{len(cues) + 1:03d}", "segment_id": segment["segment_id"],
                         "kind": segment["kind"], "source_scene_id": segment["scene_id"],
                         "visual_scene_id": scene.replace("scene-", "visual-scene-"),
                         "start_frame": start, "end_frame": end, "text": text,
                         "lines": wrap(text, 54, 880),
                         **{k: segment[k] for k in ("fact_ids", "statement_ids", "source_ids")}})
    for left, right in zip(cues, cues[1:]):
        if left["segment_id"] != right["segment_id"]:
            continue
        estimate = left["end_frame"] / FPS
        options = [round(g["midpoint"] * FPS) for g in gaps if abs(g["midpoint"] - estimate) <= .65
                   and left["start_frame"] + FPS <= round(g["midpoint"] * FPS) <= right["end_frame"] - FPS]
        if options:
            chosen = min(options, key=lambda f: abs(f / FPS - estimate))
            left["end_frame"] = right["start_frame"] = chosen
    validate_cues(value, cues, total_frames)
    return cues


def validate_cues(value, cues, total):
    if not cues or cues[0]["start_frame"] != 0 or cues[-1]["end_frame"] != total:
        fail("TIMELINE_COVERAGE")
    if normalize(" ".join(c["text"] for c in cues)) != normalize(value["full_editorial_text"]):
        fail("SUBTITLE_TEXT_CHANGED")
    segments = {s["segment_id"]: s for s in value["segments"]}
    scene_ids = [s["scene_id"] for s in value["segments"] if s["kind"] == "scene"]
    cursor = 0
    for index, cue in enumerate(cues, 1):
        segment = segments.get(cue["segment_id"])
        if segment is None or cue["cue_id"] != f"cue-{index:03d}":
            fail("CUE_IDENTITY")
        if any(type(cue[k]) is not int for k in ("start_frame", "end_frame")):
            fail("FRAME_TYPE")
        if cue["start_frame"] != cursor or cue["end_frame"] - cursor < FPS:
            fail("TIMELINE_GAP_OR_SHORT_CUE")
        cursor = cue["end_frame"]
        expected_scene = segment["scene_id"] or (scene_ids[0] if segment["kind"] == "hook" else scene_ids[-1])
        if cue["visual_scene_id"] != expected_scene.replace("scene-", "visual-scene-"):
            fail("SCENE_MISMATCH")
        for key in ("kind", "fact_ids", "statement_ids", "source_ids"):
            if cue[key] != segment[key]:
                fail("CUE_PROVENANCE")
        if cue["source_scene_id"] != segment["scene_id"]:
            fail("CUE_PROVENANCE")
        if len(cue["lines"]) > 2 or normalize(" ".join(cue["lines"])) != normalize(cue["text"]):
            fail("SUBTITLE_LAYOUT")
        if any(len(wrap(row, 54, 880)) != 1 for row in cue["lines"]):
            fail("SUBTITLE_LAYOUT")
    for segment in value["segments"]:
        reconstructed = " ".join(c["text"] for c in cues if c["segment_id"] == segment["segment_id"])
        if normalize(reconstructed) != normalize(segment["editorial_text"]):
            fail("SEGMENT_TEXT_CHANGED")


def plan(package, script, value, metadata, snapshots, cues):
    regular, bold = font_files()
    date = parse_utc(package["generated_at"]).date().isoformat()
    total = math.ceil(metadata["audio_metrics"]["frames"] * FPS / 24000)
    result = {"schema_version": VERSION, "renderer_version": VERSION, "site": package["site"],
              "package_id": package["package_id"], "script_id": script["script_id"],
              "voice_job_id": value["voice_job_id"], "source_hashes": snapshots,
              "source_target_seconds": script["target_seconds"], "audio_seconds": metadata["audio_metrics"]["frames"] / 24000,
              "video_frames": total, "fps": FPS, "width_px": 1080, "height_px": 1920,
              "font_hashes": [sha(regular.read_bytes()), sha(bold.read_bytes())],
              "font_family": font(32).getname()[0], "snapshot_date_utc": date,
              "historical_fixture": True, "historical_label": "PILOTO HISTÓRICO · " + date,
              "alignment": ALIGNMENT, "audio_speed_factor": 1, "audio_regenerated": False,
              "network_used_by_renderer": False, "external_media_assets_used": False,
              "provider_requests": 0, "allowed_uses": ["internal_preview"],
              "publication_allowed": False, "human_review_required": True,
              "human_review_status": "PENDING", "transcript_validation": "NOT_RUN", "cues": cues}
    result["content_hash"] = sha(canonical(result).encode("utf-8"))
    result["montage_id"] = "video-montage:" + result["content_hash"]
    return result


def text_svg(rows, x, y, size, step, fill, weight=400, anchor="start"):
    return f'<text font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">' + "".join(
        f'<tspan x="{x}" y="{y + i * step}">{escape(row)}</tspan>' for i, row in enumerate(rows)) + "</text>"


def frame_svg(package, script, storyboard, montage, cue):
    site = package["site"]
    theme = load_visual_rules()["themes"][site]
    scene = next(s for s in storyboard["scenes"] if s["scene_id"] == cue["visual_scene_id"])
    source_scene = next(s for s in script["scenes"] if s["scene_id"] == scene["source_scene_id"])
    headline, eyebrow, body = scene["headline"], scene["eyebrow"], scene["body"]
    if cue["kind"] in ("hook", "outro"):
        headline = "Estrecho de " + SITES[site]
        eyebrow = "LAS CLAVES Y LA INCERTIDUMBRE" if cue["kind"] == "hook" else "SEGUIMOS VIGILANDO"
    elif source_scene["voiceover"].startswith("Esto es lo que todavía no sabemos:"):
        eyebrow = "INCERTIDUMBRE ABIERTA"
    rows = wrap(headline, 66, 900, True)
    body_rows = wrap(body, 32, 900)
    if len(rows) > 5 or len(body_rows) > 2:
        fail("FRAME_TEXT_OVERFLOW")
    art = _template_art(scene, site, theme)
    warning = ""
    if scene["resolved_template"] == "schematic-map":
        art = re.sub(r"<text\b.*?</text>", "", art, flags=re.S)
        art = '<g transform="translate(54,680) scale(.9,.44)">' + art + "</g>"
        warning = text_svg(["ESTRECHO DE " + SITES[site].upper(), "ESQUEMA · NO APTO PARA NAVEGACIÓN"],
                           540, 1385, 26, 38, theme["signal"], anchor="middle")
    else:
        art = '<g transform="translate(54,-10) scale(.9)">' + art + "</g>"
    names = {r["source_id"]: r["canonical_name"] for r in package["sources"]}
    sources = "FUENTES · " + " / ".join(names[k] for k in cue["source_ids"])
    source_rows = wrap(sources, 25, 900)
    if len(source_rows) > 1:
        fail("SOURCE_LABEL_OVERFLOW")
    progress = round(900 * cue["start_frame"] / montage["video_frames"])
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">',
        f'<rect width="1080" height="1920" fill="{theme["background"]}"/>',
        f'<rect width="1080" height="12" fill="{theme["accent"]}"/>',
        f'<g font-family="{escape(montage["font_family"])}">',
        text_svg(["STRAITWATCH"], 90, 112, 40, 48, theme["text"], 700),
        text_svg([site.upper()], 990, 112, 30, 40, theme["accent"], anchor="end"),
        '<rect x="90" y="182" width="900" height="78" rx="14" fill="#243440" stroke="#F0B44D" stroke-width="2"/>',
        text_svg([montage["historical_label"]], 540, 232, 32, 40, theme["signal"], 700, "middle"),
        text_svg([eyebrow], 90, 337, 28, 35, theme["accent"], 700),
        text_svg(rows, 90, 428, 66, 79, theme["text"], 700),
        text_svg(body_rows, 90, 822, 32, 43, theme["muted"]),
        art, warning, text_svg(source_rows, 90, 1494, 25, 35, theme["muted"]),
        '<rect x="76" y="1540" width="928" height="216" rx="24" fill="#102F40"/>',
        text_svg(cue["lines"], 540, 1625 if len(cue["lines"]) == 2 else 1660, 54, 70, theme["text"], anchor="middle"),
        text_svg(["PREVIEW LOCAL · SIN PUBLICAR"], 540, 1818, 25, 32, theme["signal"], anchor="middle"),
        '<rect x="90" y="1850" width="900" height="8" rx="4" fill="#0D2A3A"/>',
        f'<rect x="90" y="1850" width="{progress}" height="8" rx="4" fill="{theme["accent"]}"/>',
        text_svg([f'{cue["start_frame"] / FPS:04.1f} s / {montage["video_frames"] / FPS:.1f} s'],
                 990, 1895, 22, 28, theme["muted"], anchor="end"),
        "</g></svg>\n"])


def run_tool(arguments, *, cwd):
    result = subprocess.run(arguments, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=180, check=False)
    if result.returncode:
        fail("RENDER_TOOL_FAILED")
    return result.stdout


def check_delivery(root, montage, original_path):
    info = json.loads(run_tool(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
                                "-of", "json", "video.mp4"], cwd=root))
    streams = info["streams"]
    if len(streams) != 2:
        fail("DELIVERY_STREAM_COUNT")
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    if (video["width"], video["height"], video["r_frame_rate"], video["codec_name"], video["pix_fmt"]) != (
            1080, 1920, "30/1", "h264", "yuv420p"):
        fail("DELIVERY_FORMAT")
    if int(video["nb_read_frames"]) != montage["video_frames"]:
        fail("DELIVERY_FRAME_COUNT")
    if abs(float(video["duration"]) - montage["video_frames"] / FPS) > .002:
        fail("DELIVERY_DURATION")
    if audio["codec_name"] != "aac" or audio["channels"] != 1 or audio["sample_rate"] != "24000":
        fail("DELIVERY_AUDIO_FORMAT")
    if abs(float(audio["duration"]) - montage["audio_seconds"]) > 1 / FPS:
        fail("DELIVERY_AUDIO_DURATION")
    raw = run_tool(["ffmpeg", "-v", "error", "-nostdin", "-i", "video.mp4", "-map", "0:a:0",
                    "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", "pipe:1"], cwd=root)
    decoded = array.array("h", raw)
    with wave.open(str(original_path), "rb") as source:
        original = array.array("h", source.readframes(source.getnframes()))
    if not len(original) <= len(decoded) <= len(original) + 2048:
        fail("DELIVERY_AUDIO_SAMPLES")
    decoded_sample_count = len(decoded)
    decoded = decoded[:len(original)]
    count = len(original)
    a_sum, b_sum = sum(original), sum(decoded)
    covariance = sum(a * b for a, b in zip(original, decoded)) - a_sum * b_sum / count
    a_var = sum(a * a for a in original) - a_sum * a_sum / count
    b_var = sum(b * b for b in decoded) - b_sum * b_sum / count
    correlation = covariance / math.sqrt(a_var * b_var) if a_var > 0 and b_var > 0 else 0
    if correlation < .98:
        fail("DELIVERY_AUDIO_DRIFT")
    return {"video_seconds": float(video["duration"]), "audio_seconds": float(audio["duration"]),
            "video_frames": int(video["nb_read_frames"]), "audio_correlation": correlation,
            "dimensions": [1080, 1920], "fps": FPS, "source_samples": len(original),
            "decoded_samples": decoded_sample_count, "compared_samples": count, "container": info}


def verify_bundle(root, expected_plan, package, script, original_path):
    actual = read_json(root / "montage.json")
    if canonical(actual) != canonical(expected_plan):
        fail("CACHED_MONTAGE_CONFLICT")
    storyboard = read_json(root / "storyboard.json")
    visual = read_json(root / "visual-manifest.json")
    if validate_storyboard(package, script, storyboard)["validation_status"] != "PASS":
        fail("CACHED_STORYBOARD_INVALID")
    if validate_visual_manifest(package, script, storyboard, visual, root)["validation_status"] != "PASS":
        fail("CACHED_VISUAL_INVALID")
    manifest = read_json(root / "delivery-manifest.json")
    required = {"schema_version": VERSION, "montage_id": actual["montage_id"],
                "publication_allowed": False, "human_review_required": True,
                "human_review_status": "PENDING", "transcript_validation": "NOT_RUN"}
    if any(type(manifest.get(k)) is not type(v) or manifest.get(k) != v for k, v in required.items()):
        fail("DELIVERY_GUARD_INVALID")
    records = manifest.get("files")
    if not isinstance(records, list):
        fail("DELIVERY_MANIFEST_INVALID")
    for record in records:
        relative = Path(record["file"])
        path = root / relative
        if relative.is_absolute() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            fail("DELIVERY_PATH_INVALID")
        if not path.is_file() or record["sha256"] != sha(path.read_bytes()) or record["bytes"] != path.stat().st_size:
            fail("DELIVERY_HASH_MISMATCH")
    required_files = {"video.mp4", "subtitles.srt", "montage.json", "storyboard.json", "visual-manifest.json"}
    if not required_files <= {r["file"] for r in records}:
        fail("DELIVERY_MANIFEST_INCOMPLETE")
    for name, checksum in actual["source_hashes"].items():
        if sha((root / "source" / name).read_bytes()) != checksum:
            fail("SOURCE_COPY_CHANGED")
    return check_delivery(root, actual, original_path)


def render_preview(input_dir, output_dir, *, site, expected_audio_sha256, repo_root=REPO_ROOT):
    input_dir, output_dir, repo_root = Path(input_dir).resolve(), Path(output_dir).resolve(), Path(repo_root).resolve()
    if output_dir.is_relative_to(repo_root) or output_dir == input_dir or output_dir.is_relative_to(input_dir) or input_dir.is_relative_to(output_dir):
        fail("OUTPUT_MUST_BE_ISOLATED")
    package, script, value, metadata, snapshots, report = load_inputs(input_dir, site, expected_audio_sha256)
    audio_path = input_dir / "audio-gemini.wav"
    total = math.ceil(metadata["audio_metrics"]["frames"] * FPS / 24000)
    cues = timeline(value, metadata, silence_gaps(audio_path), total)
    montage = plan(package, script, value, metadata, snapshots, cues)
    for name in ("ffmpeg", "ffprobe", "rsvg-convert"):
        if shutil.which(name) is None:
            fail("LOCAL_RENDER_TOOLS_REQUIRED")
    if output_dir.exists():
        metrics = verify_bundle(output_dir, montage, package, script, audio_path)
        return {"validation_status": "PASS", "cache_hit": True, "montage_id": montage["montage_id"],
                "publication_allowed": False, "provider_requests": 0, "delivery": {k: v for k, v in metrics.items() if k != "container"}}
    output_dir.mkdir(parents=True)
    for name in ("source", "compositions", "frames", "qa"):
        (output_dir / name).mkdir()
    for name in INPUT_NAMES:
        shutil.copyfile(input_dir / name, output_dir / "source" / name)
    storyboard = build_storyboard(package, script)
    visual = render_storyboard(storyboard, output_dir / "assets")
    reports = [validate_storyboard(package, script, storyboard),
               validate_visual_manifest(package, script, storyboard, visual, output_dir)]
    if any(row["validation_status"] != "PASS" for row in reports):
        fail("UPSTREAM_VISUAL_INVALID")
    write_json(output_dir / "storyboard.json", storyboard)
    write_json(output_dir / "visual-manifest.json", visual)
    write_json(output_dir / "source-validation.json", {"voice": report, "visual": reports})
    write_json(output_dir / "montage.json", montage)
    concat = ["ffconcat version 1.0"]
    for cue in cues:
        svg_path = output_dir / "compositions" / (cue["cue_id"] + ".svg")
        svg_path.write_text(frame_svg(package, script, storyboard, montage, cue), encoding="utf-8", newline="\n")
        png_name = "frames/" + cue["cue_id"] + ".png"
        run_tool(["rsvg-convert", "-o", png_name, "compositions/" + cue["cue_id"] + ".svg"], cwd=output_dir)
        concat.extend([f"file '{png_name}'", "option framerate 30",
                       f'duration {(cue["end_frame"] - cue["start_frame"]) / FPS:.12f}'])
    concat.extend([f'file \'frames/{cues[-1]["cue_id"]}.png\'', "option framerate 30"])
    (output_dir / "frames.ffconcat").write_text("\n".join(concat) + "\n", encoding="utf-8")
    def stamp(frame):
        ms = round(frame * 1000 / FPS)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    srt = "\n\n".join(f'{index}\n{stamp(c["start_frame"])} --> {stamp(c["end_frame"])}\n' + "\n".join(c["lines"])
                      for index, c in enumerate(cues, 1))
    (output_dir / "subtitles.srt").write_text(srt + "\n", encoding="utf-8")
    run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "concat", "-safe", "0", "-i", "frames.ffconcat",
              "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "-1",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
              "-r", "30", "-fps_mode", "cfr", "-frames:v", str(total),
              "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-ar", "24000", "-movflags", "+faststart", "video.mp4"], cwd=output_dir)
    metrics = check_delivery(output_dir, montage, audio_path)
    write_json(output_dir / "ffprobe.json", metrics.pop("container"))
    if any(sha((input_dir / name).read_bytes()) != checksum for name, checksum in snapshots.items()):
        fail("SOURCE_CHANGED_DURING_RENDER")
    # Contact sheet is extracted from the encoded MP4, for visual human review.
    from PIL import Image, ImageDraw
    group_keys = list(dict.fromkeys((c["kind"], c["source_scene_id"]) for c in cues))
    representative = [next(c for c in cues if (c["kind"], c["source_scene_id"]) == key) for key in group_keys]
    sheet = Image.new("RGB", (1080, math.ceil(len(representative) / 4) * 520), "#061622")
    for index, cue in enumerate(representative):
        seconds = (cue["start_frame"] + cue["end_frame"]) / (2 * FPS)
        name = f"qa/frame-{index + 1:02d}.png"
        run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-ss", f"{seconds:.3f}",
                  "-i", "video.mp4", "-frames:v", "1", name], cwd=output_dir)
        with Image.open(output_dir / name) as image:
            sheet.paste(image.convert("RGB").resize((270, 480)), ((index % 4) * 270, (index // 4) * 520))
        ImageDraw.Draw(sheet).text(((index % 4) * 270 + 10, (index // 4) * 520 + 490),
                                  cue["segment_id"], fill="white", font=font(20))
    sheet.save(output_dir / "qa/contact-sheet.png")
    summary = {"validation_status": "PASS", "renderer_version": VERSION, "montage_id": montage["montage_id"],
               "cache_hit": False, "provider_requests": 0, "source_master_unchanged": True,
               "historical_fixture": True, "human_review_required": True, "human_review_status": "PENDING",
               "transcript_validation": "NOT_RUN", "alignment": ALIGNMENT, "publication_allowed": False, "delivery": metrics}
    write_json(output_dir / "validation.json", summary)
    preview = "# StraitWatch · preview interna de montaje\n\n" + (
        f"Sitio: {SITES[site]} · Instantánea histórica UTC: {montage['snapshot_date_utc']}.\n\n"
        f"[Vídeo](video.mp4) · [Subtítulos](subtitles.srt) · [Verificación](validation.json).\n\n"
        f"Duración real: {metrics['video_seconds']:.3f} s; objetivo del storyboard intacto: {script['target_seconds']} s.\n\n"
        "Audio reutilizado completo, sin aceleración, corte o nueva síntesis. Copia AAC; máster PCM en source/.\n\n"
        "Subtítulos ESTIMADOS, no ASR. Revisar sincronización, cifras, legibilidad y voz antes de publicar.\n\n"
        "Revisión humana PENDING. Publicación bloqueada. No representa el estado actual del estrecho.\n\n"
        f"Job de voz: {value['voice_job_id']}\n\nHash del WAV: {expected_audio_sha256}\n")
    audit_output(preview)
    (output_dir / "preview.md").write_text(preview, encoding="utf-8")
    files = [{"file": str(p.relative_to(output_dir)).replace("\\", "/"), "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
             for p in sorted(output_dir.rglob("*")) if p.is_file()]
    manifest = {"schema_version": VERSION, "montage_id": montage["montage_id"], "publication_allowed": False,
                "human_review_required": True, "human_review_status": "PENDING", "transcript_validation": "NOT_RUN", "files": files}
    write_json(output_dir / "delivery-manifest.json", manifest)
    verify_bundle(output_dir, montage, package, script, audio_path)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=sorted(SITES))
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-audio-sha256", required=True)
    args = parser.parse_args()
    try:
        result = render_preview(args.input_dir, args.output_dir, site=args.site,
                                expected_audio_sha256=args.expected_audio_sha256)
    except MontageError as exc:
        print(json.dumps({"validation_status": "FAIL", "error": str(exc), "publication_allowed": False, "provider_requests": 0}))
        raise SystemExit(1) from None
    except Exception:
        print(json.dumps({"validation_status": "FAIL", "error": "INTERNAL_MONTAGE_ERROR",
                          "publication_allowed": False, "provider_requests": 0}))
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
