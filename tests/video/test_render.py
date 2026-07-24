"""Behavior contracts for deterministic FFmpeg timeline rendering."""

from __future__ import annotations

import array
import hashlib
import importlib
import io
import json
import math
import subprocess
import sys
import wave
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

from video_pipeline.models import (
    MediaSettings,
    OutputConfig,
    ProjectManifest,
    Rectangle,
    SafeArea,
    Scene,
    TextSizes,
    VisualState,
)
from video_pipeline.render import RenderCapabilities, RenderConfig, RenderResult
from video_pipeline.scenes import RenderedSceneState

REPOSITORY_ROOT = Path(__file__).parents[2]
EXPECTED_STATE_IDS = (
    ("problem", "question"),
    ("problem", "mute_safe_copy"),
    ("visible-workflow", "editor-lines-1-14"),
    ("visible-workflow", "editor-lines-15-27"),
    ("visible-workflow", "mute_safe_copy"),
    ("caught-defect", "teaching-source"),
    ("caught-defect", "teaching-diagnostics"),
    ("caught-defect", "mute_safe_copy"),
    ("shared-policy", "system-map"),
    ("shared-policy", "mute_safe_copy"),
    ("guarded-execution", "runner"),
    ("guarded-execution", "mute_safe_copy"),
    ("promise", "end-card"),
    ("promise", "mute_safe_copy"),
)


@dataclass(frozen=True, slots=True)
class _Fixture:
    project: ProjectManifest
    states: tuple[RenderedSceneState, ...]
    captions: Path
    selected_wav: Path
    selected_wav_sha256: str


type _RenderedFixture = tuple[_Fixture, RenderConfig, RenderResult]


def _require_render_api() -> None:
    try:
        module = importlib.import_module("video_pipeline.render")
    except ModuleNotFoundError:
        pytest.fail("render stage is missing")
    assert module is not None


def _svg(index: int, label: str, *, changed: bool = False) -> bytes:
    color = f"#{(index * 913_919 + (1 if changed else 0)) & 0xFFFFFF:06x}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" '
        'viewBox="0 0 320 180">'
        f'<rect width="320" height="180" fill="{color}"/>'
        '<rect x="18" y="122" width="284" height="42" rx="8" fill="#111827"/>'
        '<text x="160" y="149" text-anchor="middle" font-family="Noto Sans" '
        f'font-size="16" fill="#ffffff">TEST ONLY {label}</text>'
        "</svg>"
    ).encode()


def _wav(*, sample_rate: int = 48_000, sample_count: int = 67_200) -> bytes:
    samples = array.array(
        "h",
        (
            round(12_000 * math.sin(2 * math.pi * 880 * index / sample_rate))
            if sample_rate // 10 <= index < sample_count - sample_rate // 10
            else 0
            for index in range(sample_count)
        ),
    )
    if sys.byteorder != "little":
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(samples.tobytes())
    return output.getvalue()


def _fixture(tmp_path: Path) -> _Fixture:
    output_root = tmp_path / "dist" / "video"
    output = OutputConfig(
        root=output_root,
        narrated=output_root / "final" / "fixture-narrated.mp4",
        speaker=output_root / "final" / "fixture-speaker.mp4",
        render_manifest=output_root / "candidate" / "render-manifest.json",
        container="mp4",
        video_codec="h264",
        audio_codec="aac",
        pixel_format="yuv420p",
        deterministic=True,
    )
    scene_lengths = (2, 3, 3, 2, 2, 2)
    scenes: list[Scene] = []
    rendered: list[RenderedSceneState] = []
    frame = 0
    state_index = 0
    for scene_index, state_count in enumerate(scene_lengths):
        scene_id = EXPECTED_STATE_IDS[state_index][0]
        scene_start = frame
        states: list[VisualState] = []
        for _ in range(state_count):
            expected_scene, state_id = EXPECTED_STATE_IDS[state_index]
            assert expected_scene == scene_id
            state = VisualState(
                id=state_id,
                start_frame=frame,
                end_frame=frame + 3,
                evidence_rectangles=(),
            )
            states.append(state)
            rendered.append(
                RenderedSceneState(
                    scene_id=scene_id,
                    state_id=state_id,
                    start_frame=frame,
                    end_frame=frame + 3,
                    svg=_svg(state_index, f"{scene_id}/{state_id}"),
                    evidence_rectangles=(),
                    essential_rectangles=(Rectangle(18, 122, 284, 42),),
                    copy_rectangle=Rectangle(18, 122, 284, 42),
                    caption_rectangle=Rectangle(16, 126, 288, 38),
                    display_text=f"TEST ONLY {scene_id}/{state_id}",
                    content_ledger=(f"TEST ONLY {scene_id}/{state_id}",),
                    references=(),
                    asset_ids=("noto-sans-regular",),
                )
            )
            frame += 3
            state_index += 1
        scenes.append(
            Scene(
                id=scene_id,
                start_frame=scene_start,
                end_frame=frame,
                source_paths=(REPOSITORY_ROOT / f"TEST-ONLY-SCENE-{scene_index}.txt",),
                visual_states=tuple(states),
            )
        )
    assert frame == 42
    project = ProjectManifest(
        media=MediaSettings(width=320, height=180, fps=30, total_frames=42),
        safe_area=SafeArea(
            rectangle=Rectangle(16, 9, 288, 162),
            text_sizes=TextSizes(caption=18, code=12, label=12),
        ),
        output=output,
        scenes=tuple(scenes),
        evidence_dominant_frames=0,
    )
    captions = tmp_path / "TEST-ONLY-captions.srt"
    captions.write_text(
        "1\n00:00:00,200 --> 00:00:01,100\nTEST ONLY NARRATION CAPTION\n",
        encoding="utf-8",
    )
    selected_wav = tmp_path / "TEST-ONLY-selected-narration.wav"
    selected_wav.write_bytes(_wav())
    return _Fixture(
        project=project,
        states=tuple(rendered),
        captions=captions,
        selected_wav=selected_wav,
        selected_wav_sha256=hashlib.sha256(selected_wav.read_bytes()).hexdigest(),
    )


@pytest.fixture(scope="module")
def render_capabilities() -> RenderCapabilities:
    from video_pipeline.render import probe_render_capabilities

    return probe_render_capabilities()


@pytest.fixture
def rendered_fixture(tmp_path: Path, render_capabilities: RenderCapabilities) -> _RenderedFixture:
    from video_pipeline.render import RenderConfig, render_timeline

    fixture = _fixture(tmp_path)
    config = RenderConfig.fixture(
        width=320,
        height=180,
        fps=30,
        total_frames=42,
        caption_size=18,
        video_bitrate="400k",
    )
    result = render_timeline(
        repository_root=REPOSITORY_ROOT,
        project=fixture.project,
        states=fixture.states,
        captions_path=fixture.captions,
        selected_wav=fixture.selected_wav,
        selected_wav_sha256=fixture.selected_wav_sha256,
        config=config,
        capabilities=render_capabilities,
    )
    return fixture, config, result


def _probe(path: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            (
                "format=format_name,duration:"
                "stream=index,codec_type,codec_name,width,height,r_frame_rate,"
                "duration,nb_read_frames,channels,sample_rate"
            ),
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return cast(dict[str, object], json.loads(completed.stdout))


def _decoded_pcm(path: Path) -> array.array[int]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            "atrim=end_sample=67200,asetpts=N/SR/TB",
            "-c:a",
            "pcm_s16le",
            "-f",
            "s16le",
            "-",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    samples = array.array("h")
    samples.frombytes(completed.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _tone_amplitude(samples: array.array[int], frequency: int, sample_rate: int) -> float:
    mono = [(samples[index] + samples[index + 1]) / 2 for index in range(0, len(samples), 2)]
    omega = 2 * math.pi * frequency / sample_rate
    coefficient = 2 * math.cos(omega)
    previous = 0.0
    before_previous = 0.0
    for sample in mono:
        current = sample + coefficient * previous - before_previous
        before_previous = previous
        previous = current
    power = (
        previous * previous
        + before_previous * before_previous
        - coefficient * previous * before_previous
    )
    return math.sqrt(max(0.0, power)) / len(mono)


def test_tc_t7_000__reference_toolchain__passes_real_preflight() -> None:
    completed = subprocess.run(
        ["ffmpeg", "-version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.stdout.startswith("ffmpeg version 8.1.2 ")
    _require_render_api()


def test_tc_t7_001__short_real_fixture__renders_matching_picture_variants(
    rendered_fixture: _RenderedFixture,
) -> None:
    fixture, _, result = rendered_fixture
    narrated_probe = _probe(fixture.project.output.narrated)
    speaker_probe = _probe(fixture.project.output.speaker)
    for probe in (narrated_probe, speaker_probe):
        streams = cast(list[dict[str, object]], probe["streams"])
        video = next(stream for stream in streams if stream["codec_type"] == "video")
        audio = next(stream for stream in streams if stream["codec_type"] == "audio")
        assert (video["codec_name"], video["width"], video["height"]) == ("h264", 320, 180)
        assert video["r_frame_rate"] == "30/1"
        assert int(cast(str, video["nb_read_frames"])) == 42
        assert (audio["codec_name"], audio["channels"], audio["sample_rate"]) == (
            "aac",
            2,
            "48000",
        )
        assert float(cast(str, video["duration"])) == pytest.approx(1.4, abs=1 / 30)
        assert float(
            cast(str, cast(dict[str, object], probe["format"])["duration"])
        ) == pytest.approx(1.4, abs=1 / 30)

    narrated_pcm = _decoded_pcm(fixture.project.output.narrated)
    speaker_pcm = _decoded_pcm(fixture.project.output.speaker)
    assert len(narrated_pcm) == len(speaker_pcm) == 67_200 * 2
    assert _tone_amplitude(narrated_pcm, 880, 48_000) > (
        8 * _tone_amplitude(speaker_pcm, 880, 48_000)
    )
    assert result.decoded_picture_sha256["speaker"] == result.base_picture_sha256
    assert result.decoded_picture_sha256["narrated"] != result.base_picture_sha256
    assert result.decoded_pcm_sha256["narrated"] != result.decoded_pcm_sha256["speaker"]


def test_tc_t7_002__graphs__separate_captions_audio_bed_and_loudness(
    rendered_fixture: _RenderedFixture,
    render_capabilities: RenderCapabilities,
) -> None:
    from video_pipeline.render import build_variant_command

    fixture, config, result = rendered_fixture
    command = build_variant_command(
        capabilities=render_capabilities,
        project=fixture.project,
        config=config,
        base_video=result.base_video,
        captions_path=fixture.captions,
        selected_wav=fixture.selected_wav,
    )
    graph = command[command.index("-filter_complex") + 1]
    assert graph.count("subtitles=") == 1
    assert "Noto Sans" in graph
    assert "[1:a:0]" in graph
    assert "sine=frequency=110:sample_rate=48000" in graph
    assert graph.count("sine=frequency=660:sample_rate=48000") == (len(fixture.project.scenes) - 1)
    assert "loudnorm=I=-16:LRA=7:TP=-1" in graph
    assert "loudnorm=I=-28:LRA=7:TP=-6" in graph
    assert "atrim=end_sample=67200" in graph
    speaker_output_index = command.index(str(fixture.project.output.speaker))
    assert command[speaker_output_index - 1] == "+faststart"

    manifest = json.loads(fixture.project.output.render_manifest.read_text(encoding="utf-8"))
    assert manifest["synthesis"]["external_music_inputs"] == []
    assert manifest["outputs"]["narrated"]["inputs"] == [
        "shared_picture",
        "captions_srt",
        "selected_narration_wav",
        "procedural_tonal_bed_and_cues",
    ]
    assert manifest["outputs"]["speaker"]["inputs"] == [
        "shared_picture",
        "procedural_tonal_bed_and_cues",
    ]
    assert manifest["audio_targets"] == {
        "narrated": {"integrated_lufs": -16, "true_peak_dbtp": -1},
        "speaker": {"integrated_lufs": -28, "true_peak_dbtp": -6},
    }


def test_tc_t7_003__cache_selected_wav_and_manifest__are_exact(
    rendered_fixture: _RenderedFixture,
    render_capabilities: RenderCapabilities,
) -> None:
    from video_pipeline.render import RenderConfig, RenderError, render_timeline

    fixture, config, first = rendered_fixture
    assert len(first.rebuilt_states) == 14
    assert first.timeline_rebuilt is True
    second = render_timeline(
        repository_root=REPOSITORY_ROOT,
        project=fixture.project,
        states=fixture.states,
        captions_path=fixture.captions,
        selected_wav=fixture.selected_wav,
        selected_wav_sha256=fixture.selected_wav_sha256,
        config=config,
        capabilities=render_capabilities,
    )
    assert second.rebuilt_states == ()
    assert second.timeline_rebuilt is False

    with pytest.raises(RenderError, match="selected narration WAV checksum"):
        render_timeline(
            repository_root=REPOSITORY_ROOT,
            project=fixture.project,
            states=fixture.states,
            captions_path=fixture.captions,
            selected_wav=fixture.selected_wav,
            selected_wav_sha256="0" * 64,
            config=config,
            capabilities=render_capabilities,
        )

    changed = list(fixture.states)
    changed[0] = replace(
        changed[0],
        svg=_svg(0, "problem/question", changed=True),
    )
    third = render_timeline(
        repository_root=REPOSITORY_ROOT,
        project=fixture.project,
        states=tuple(changed),
        captions_path=fixture.captions,
        selected_wav=fixture.selected_wav,
        selected_wav_sha256=fixture.selected_wav_sha256,
        config=config,
        capabilities=render_capabilities,
    )
    assert third.rebuilt_states == ("problem/question",)
    assert third.timeline_rebuilt is True

    manifest = json.loads(fixture.project.output.render_manifest.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["source_revision"]
    assert len(manifest["project_timing"]["states"]) == 14
    assert manifest["project_timing"]["total_frames"] == 42
    assert manifest["inputs"]["selected_narration_wav"]["sha256"] == (fixture.selected_wav_sha256)
    assert set(manifest["toolchain"]) == {
        "encoder",
        "ffmpeg",
        "ffprobe",
        "fontconfig",
        "fonts",
        "librsvg",
        "options",
    }
    assert manifest["toolchain"]["ffmpeg"]["version"] == "8.1.2"
    assert manifest["toolchain"]["ffprobe"]["version"] == "8.1.2"
    assert manifest["toolchain"]["librsvg"]["version"] == "2.62.3"
    assert manifest["toolchain"]["encoder"]["name"] == "libopenh264"
    assert manifest["toolchain"]["encoder"]["verified"] is True
    assert [font["family"] for font in manifest["toolchain"]["fonts"]] == [
        "Noto Sans",
        "Noto Sans Mono",
    ]
    for output in manifest["outputs"].values():
        assert len(output["sha256"]) == 64
        assert len(output["decoded_video_sha256"]) == 64
        assert len(output["decoded_pcm_sha256"]) == 64
        assert output["decoded_audio_samples_per_channel"] == 67_200
        assert output["probe"]["program_audio_boundary"] == {
            "first_program_sample": 0,
            "last_program_sample_exclusive": 67_200,
            "packet_after_program_boundary": False,
            "priming_skip_samples": 1024,
        }
    assert len(manifest["shared_picture"]["decoded_video_sha256"]) == 64

    production = RenderConfig.production()
    assert (
        production.width,
        production.height,
        production.fps,
        production.total_frames,
    ) == (1920, 1080, 30, 4050)
