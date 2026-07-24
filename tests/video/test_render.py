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
import time
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol, cast

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
type _CacheKey = Callable[[Mapping[str, object]], str]
type _CacheContract = Callable[[RenderCapabilities, RenderConfig], dict[str, object]]
type _RunChecked = Callable[[Sequence[str], str], None]
type _MediaProbe = Callable[[Path, RenderCapabilities], dict[str, object]]


class _HashCommandOutput(Protocol):
    def __call__(
        self,
        argv: Sequence[str],
        label: str,
        *,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> tuple[str, int]: ...


class _AtomicWriteJson(Protocol):
    def __call__(
        self,
        path: Path,
        payload: Mapping[str, object],
        *,
        temporary_root: Path | None = None,
    ) -> None: ...


class _AudioBoundaryValidator(Protocol):
    def __call__(
        self,
        probe: Mapping[str, object],
        *,
        audio_stream_index: int,
        total_samples: int,
    ) -> dict[str, object]: ...


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


@pytest.fixture
def render_capabilities(tmp_path: Path) -> RenderCapabilities:
    from video_pipeline.render import probe_render_capabilities

    return probe_render_capabilities(work_root=tmp_path / "dist" / "video" / "work")


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
                "duration,nb_read_frames,channels,sample_rate,profile"
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


def _decoded_pcm(path: Path, *, end_sample: int | None = None) -> array.array[int]:
    bounded_decode = [] if end_sample is None else ["-af", f"atrim=end_sample={end_sample}"]
    completed = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            *bounded_decode,
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


def test_tc_t7_000a__capability_probe__rejects_every_used_graph_filter() -> None:
    from video_pipeline.render import RenderError, validate_required_filters

    listing = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    graph_filters = (
        "adelay",
        "afade",
        "aformat",
        "amix",
        "apad",
        "aresample",
        "asetpts",
        "asplit",
        "atrim",
        "concat",
        "format",
        "loudnorm",
        "scale",
        "setpts",
        "sine",
        "subtitles",
        "volume",
    )
    validate_required_filters(listing)
    for filter_name in graph_filters:
        listing_without_filter = "\n".join(
            line for line in listing.splitlines() if f" {filter_name} " not in line
        )
        with pytest.raises(RenderError, match=filter_name):
            validate_required_filters(listing_without_filter)


def test_tc_t7_000b__cache_keys__include_every_toolchain_identity_and_option(
    render_capabilities: RenderCapabilities,
) -> None:
    from video_pipeline import render as render_module
    from video_pipeline.render import RenderConfig

    cache_key = cast(_CacheKey, render_module.__dict__["_cache_key"])
    concat_contract = cast(
        _CacheContract,
        render_module.__dict__["_concat_options_manifest"],
    )
    scene_contract = cast(
        _CacheContract,
        render_module.__dict__["_scene_options_manifest"],
    )

    config = RenderConfig.fixture(
        width=320,
        height=180,
        fps=30,
        total_frames=42,
        caption_size=18,
        video_bitrate="400k",
    )
    baseline_state = cache_key(scene_contract(render_capabilities, config))
    baseline_timeline = cache_key(concat_contract(render_capabilities, config))
    first_font, *other_fonts = render_capabilities.fonts
    mutations = (
        replace(render_capabilities, ffmpeg_sha256="0" * 64),
        replace(render_capabilities, ffprobe_sha256="0" * 64),
        replace(render_capabilities, fontconfig_sha256="0" * 64),
        replace(
            render_capabilities,
            librsvg=replace(render_capabilities.librsvg, sha256="0" * 64),
        ),
        replace(
            render_capabilities,
            encoder_library=replace(
                render_capabilities.encoder_library,
                sha256="0" * 64,
            ),
        ),
        replace(
            render_capabilities,
            audio_encoder_library=replace(
                render_capabilities.audio_encoder_library,
                sha256="0" * 64,
            ),
        ),
        replace(
            render_capabilities,
            fonts=(replace(first_font, sha256="0" * 64), *other_fonts),
        ),
        replace(render_capabilities, encoder_help_sha256="0" * 64),
        replace(render_capabilities, aac_help_sha256="0" * 64),
    )
    for mutated in mutations:
        assert cache_key(scene_contract(mutated, config)) != baseline_state
        assert cache_key(concat_contract(mutated, config)) != baseline_timeline

    audio_option_mutation = replace(config, audio_bitrate="193k")
    assert cache_key(scene_contract(render_capabilities, audio_option_mutation)) != baseline_state
    assert (
        cache_key(concat_contract(render_capabilities, audio_option_mutation)) != baseline_timeline
    )


def test_tc_t7_000c__stream_hash__bounds_output_and_kills_stalled_process_group(
    tmp_path: Path,
) -> None:
    from video_pipeline import render as render_module
    from video_pipeline.render import RenderError

    hash_command_output = cast(
        _HashCommandOutput,
        render_module.__dict__["_hash_command_output"],
    )

    with pytest.raises(RenderError, match="output limit"):
        hash_command_output(
            (
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'x' * 2048)",
            ),
            "oversized test output",
            timeout_seconds=2,
            max_output_bytes=1024,
        )

    child_pid_path = tmp_path / "stalled-child.pid"
    child_program = (
        "import os, pathlib, signal, sys, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8'); "
        "time.sleep(60)"
    )
    parent_program = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[2], sys.argv[1]]); "
        "time.sleep(60)"
    )
    with pytest.raises(RenderError, match="timed out"):
        hash_command_output(
            (
                sys.executable,
                "-c",
                parent_program,
                str(child_pid_path),
                child_program,
            ),
            "stalled process tree",
            timeout_seconds=0.5,
            max_output_bytes=1024,
        )
    assert child_pid_path.is_file()
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 2
    while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not Path(f"/proc/{child_pid}").exists()


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
        assert audio["profile"] == "LC"
        assert float(cast(str, video["duration"])) == pytest.approx(1.4, abs=1 / 30)
        assert float(
            cast(str, cast(dict[str, object], probe["format"])["duration"])
        ) == pytest.approx(1.4, abs=1 / 30)

    narrated_pcm = _decoded_pcm(fixture.project.output.narrated, end_sample=67_200)
    speaker_pcm = _decoded_pcm(fixture.project.output.speaker, end_sample=67_200)
    assert len(narrated_pcm) == len(speaker_pcm) == 67_200 * 2
    assert not narrated_pcm[67_200 * 2 :]
    assert not speaker_pcm[67_200 * 2 :]
    assert _tone_amplitude(narrated_pcm, 880, 48_000) > (
        8 * _tone_amplitude(speaker_pcm, 880, 48_000)
    )
    assert result.decoded_picture_sha256["speaker"] == result.base_picture_sha256
    assert result.decoded_picture_sha256["narrated"] != result.base_picture_sha256
    assert result.decoded_pcm_sha256["narrated"] != result.decoded_pcm_sha256["speaker"]


def test_tc_t7_001a__native_aac_regression__untrimmed_decode_exposes_tail(
    tmp_path: Path,
) -> None:
    native_aac = tmp_path / "TEST-ONLY-native-aac-regression.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=1.4",
            "-af",
            "aformat=channel_layouts=stereo",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(native_aac),
        ],
        check=True,
        timeout=30,
    )
    decoded = _decoded_pcm(native_aac)
    assert len(decoded) // 2 == 67_584
    assert any(decoded[67_200 * 2 :])


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
    assert "loudnorm=I=-16:LRA=7:TP=-1:linear=true,volume=1.3dB" in graph
    assert "loudnorm=I=-28:LRA=7:TP=-6" in graph
    assert "atrim=end_sample=67200" in graph
    audio_encoder_indices = [index for index, argument in enumerate(command) if argument == "-c:a"]
    assert len(audio_encoder_indices) == 2
    for index in audio_encoder_indices:
        assert command[index : index + 4] == (
            "-c:a",
            "libfdk_aac",
            "-profile:a",
            "aac_low",
        )
    assert "-frame_length" not in command
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
    cold_manifest = fixture.project.output.render_manifest.read_bytes()
    cold_output_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (fixture.project.output.narrated, fixture.project.output.speaker)
    }
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
    assert fixture.project.output.render_manifest.read_bytes() == cold_manifest
    assert b"cache_status" not in cold_manifest
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (fixture.project.output.narrated, fixture.project.output.speaker)
    } == cold_output_hashes

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
        "audio_encoder",
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
    assert manifest["toolchain"]["audio_encoder"]["name"] == "libfdk_aac"
    assert manifest["toolchain"]["audio_encoder"]["profile"] == "aac_low"
    assert manifest["toolchain"]["audio_encoder"]["frame_length"] == 1024
    assert manifest["toolchain"]["audio_encoder"]["verified"] is True
    assert [font["family"] for font in manifest["toolchain"]["fonts"]] == [
        "Noto Sans",
        "Noto Sans Mono",
    ]
    for output in manifest["outputs"].values():
        assert len(output["sha256"]) == 64
        assert len(output["decoded_video_sha256"]) == 64
        assert len(output["decoded_pcm_sha256"]) == 64
        assert output["decoded_audio_samples_per_channel"] == 67_200
        audio_stream = next(
            stream for stream in output["probe"]["streams"] if stream["codec_type"] == "audio"
        )
        assert audio_stream["profile"] == "LC"
        assert output["probe"]["program_audio_boundary"] == {
            "final_discard_padding_samples": 0,
            "final_packet_duration": 640,
            "final_packet_pts": 66_560,
            "final_packet_skip_samples": 0,
            "first_program_sample": 0,
            "last_program_sample_exclusive": 67_200,
            "packet_after_program_boundary": False,
            "priming_skip_samples": 2048,
        }
    assert len(manifest["shared_picture"]["decoded_video_sha256"]) == 64

    production = RenderConfig.production()
    assert (
        production.width,
        production.height,
        production.fps,
        production.total_frames,
    ) == (1920, 1080, 30, 4050)
    assert production.caption_size == 12


def test_tc_t7_004__orchestration__keeps_every_temporary_under_owned_work_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from video_pipeline import render as render_module

    fixture = _fixture(tmp_path)
    config = render_module.RenderConfig.fixture(
        width=320,
        height=180,
        fps=30,
        total_frames=42,
        caption_size=18,
        video_bitrate="400k",
    )
    output_root = fixture.project.output.root.resolve()
    work_root = output_root / "work"
    capabilities = render_module.probe_render_capabilities(work_root=work_root)
    observed_media_paths: list[Path] = []
    manifest_temporary_roots: list[Path | None] = []
    original_run_checked = cast(
        _RunChecked,
        render_module.__dict__["_run_checked"],
    )
    original_atomic_write_json = cast(
        _AtomicWriteJson,
        render_module.__dict__["_atomic_write_json"],
    )

    def record_run_checked(argv: Sequence[str], label: str) -> None:
        observed_media_paths.extend(
            Path(argument).resolve() for argument in argv if argument.endswith(".mp4")
        )
        original_run_checked(argv, label)

    def record_atomic_write_json(
        path: Path,
        payload: Mapping[str, object],
        *,
        temporary_root: Path | None = None,
    ) -> None:
        if path == fixture.project.output.render_manifest:
            manifest_temporary_roots.append(temporary_root)
        if temporary_root is None:
            original_atomic_write_json(path, payload)
        else:
            original_atomic_write_json(
                path,
                payload,
                temporary_root=temporary_root,
            )

    monkeypatch.setattr(render_module, "_run_checked", record_run_checked)
    monkeypatch.setattr(render_module, "_atomic_write_json", record_atomic_write_json)
    render_module.render_timeline(
        repository_root=REPOSITORY_ROOT,
        project=fixture.project,
        states=fixture.states,
        captions_path=fixture.captions,
        selected_wav=fixture.selected_wav,
        selected_wav_sha256=fixture.selected_wav_sha256,
        config=config,
        capabilities=capabilities,
    )

    assert observed_media_paths
    assert all(path.is_relative_to(work_root) for path in observed_media_paths)
    assert manifest_temporary_roots == [work_root / "staging"]
    assert not [
        path
        for path in output_root.rglob("*")
        if path.is_file()
        and not path.is_relative_to(work_root)
        and path
        not in {
            fixture.project.output.narrated,
            fixture.project.output.speaker,
            fixture.project.output.render_manifest,
        }
    ]
    assert not list(output_root.glob("**/*.tmp"))
    assert not list(output_root.glob("**/*.tmp.mp4"))


def test_tc_t7_005__audio_boundary__rejects_non_sample_packet_time_base(
    rendered_fixture: _RenderedFixture,
    render_capabilities: RenderCapabilities,
) -> None:
    from video_pipeline import render as render_module
    from video_pipeline.render import RenderError

    fixture, _, _ = rendered_fixture
    media_probe = cast(_MediaProbe, render_module.__dict__["_ffprobe"])
    validate_audio_boundary = cast(
        _AudioBoundaryValidator,
        render_module.__dict__["_validate_audio_packet_boundary"],
    )
    probe = media_probe(fixture.project.output.narrated, render_capabilities)
    streams = cast(list[dict[str, object]], probe["streams"])
    audio = next(stream for stream in streams if stream["codec_type"] == "audio")
    audio["time_base"] = "1/1000"
    with pytest.raises(RenderError, match="time base"):
        validate_audio_boundary(
            probe,
            audio_stream_index=cast(int, audio["index"]),
            total_samples=67_200,
        )
