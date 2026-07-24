"""Render the repository explainer from frame-indexed SVG states.

The production contract is intentionally narrower than a general video editor:
FFmpeg/FFprobe 8.1.2, librsvg, verified OpenH264 and FDK AAC encoders, and the
two checksummed Noto faces are required before any cache or output is touched.
Test renders can shorten and scale the same fourteen-state graph only through
the explicit fixture configuration.

AAC-LD's 480-sample frames divide both approved timelines exactly. Native
AAC-LC was rejected because its 1024-sample framing decoded 384 samples past
the fixture boundary even though the MP4 packet duration appeared correct.

Command construction is pure, while subprocess, filesystem, cache, and manifest
work stays in explicit orchestration functions so a future toolchain change can
be reviewed without executing a render.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, cast

from .manifest import load_project
from .models import ProjectManifest
from .scenes import RenderedSceneState, compose_scene_states

REFERENCE_FFMPEG_VERSION = "8.1.2"
PRODUCTION_WIDTH = 1920
PRODUCTION_HEIGHT = 1080
PRODUCTION_FPS = 30
PRODUCTION_FRAMES = 4050
AUDIO_SAMPLE_RATE = 48_000
H264_ENCODER = "libopenh264"
AAC_ENCODER = "libfdk_aac"
AAC_PROFILE = "aac_ld"
AAC_FRAME_LENGTH = 480
LIBRSVG_DECODER = "librsvg"
RENDER_SCHEMA_VERSION = 1

_REQUIRED_FILTERS = frozenset(
    {
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
        "drawtext",
        "ebur128",
        "format",
        "loudnorm",
        "scale",
        "setpts",
        "sine",
        "subtitles",
        "volume",
    }
)
_REQUIRED_CONFIGURATION = frozenset(
    {
        "--enable-libass",
        "--enable-libfontconfig",
        "--enable-libfreetype",
        "--enable-libfdk-aac",
        "--enable-libopenh264",
        "--enable-librsvg",
    }
)
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")
_VERSION_LINE = re.compile(r"^(?P<tool>ffmpeg|ffprobe) version (?P<version>\S+) ")
_LIBRARY_LINE = re.compile(r"^\s*(?P<name>\S+)\s+=>\s+(?P<path>/\S+)\s+\(0x[0-9a-fA-F]+\)\s*$")


class RenderError(RuntimeError):
    """Reject an unsafe toolchain, input, cache entry, or render result."""


@dataclass(frozen=True, slots=True)
class ExpectedFont:
    """One exact external font file required by SVG and subtitle rendering."""

    family: str
    style: str
    path: Path
    sha256: str


PRODUCTION_FONTS = (
    ExpectedFont(
        family="Noto Sans",
        style="Regular",
        path=Path("/usr/share/fonts/google-noto/NotoSans-Regular.ttf"),
        sha256="478c558ea716033cd60c03438f628dfa75694dcf6b5f6d505a2f05fd2b4f3823",
    ),
    ExpectedFont(
        family="Noto Sans Mono",
        style="Regular",
        path=Path("/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf"),
        sha256="65b5e2b2c4a1fba9ae8be1f026cb35b03dcb8886d9b2a4147054fde12f7e767d",
    ),
)


@dataclass(frozen=True, slots=True)
class FontSnapshot:
    """Resolved font identity recorded in the render manifest."""

    family: str
    style: str
    font_version: str
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class LibrarySnapshot:
    """One linked runtime library and the hash of its resolved object."""

    soname: str
    path: Path
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    """Raw tool output interpreted before any render or cache work begins."""

    ffmpeg_path: Path
    ffprobe_path: Path
    fontconfig_path: Path
    fontquery_path: Path
    ffmpeg_version: str
    ffprobe_version: str
    filters: str
    decoders: str
    encoders: str
    encoder_help: str
    aac_help: str
    fontconfig_version: str
    font_queries: tuple[str, ...]
    linked_libraries: str


@dataclass(frozen=True, slots=True)
class RenderCapabilities:
    """Validated executables and exact identities used by command builders."""

    ffmpeg: Path
    ffprobe: Path
    fontconfig: Path
    ffmpeg_version: str
    ffprobe_version: str
    ffmpeg_sha256: str
    ffprobe_sha256: str
    ffmpeg_configuration: tuple[str, ...]
    fontconfig_version: str
    fontconfig_sha256: str
    fonts: tuple[FontSnapshot, ...]
    librsvg: LibrarySnapshot
    encoder_library: LibrarySnapshot
    audio_encoder_library: LibrarySnapshot
    encoder: str
    encoder_help_sha256: str
    aac_help_sha256: str
    encoder_verified: bool
    audio_encoder_verified: bool


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Immutable picture/audio/options contract for production or a test fixture."""

    mode: Literal["production", "fixture"]
    width: int
    height: int
    fps: int
    total_frames: int
    caption_size: int
    video_bitrate: str
    audio_sample_rate: int = AUDIO_SAMPLE_RATE
    audio_bitrate: str = "192k"
    cue_frequency: int = 660
    cue_samples: int = 3840
    cue_fade_start_sample: int = 1440
    cue_fade_samples: int = 2400
    bed_frequency: int = 110
    bed_volume: str = "0.06"
    cue_volume: str = "0.15"

    @classmethod
    def production(cls) -> RenderConfig:
        """Return the only permitted production render configuration."""
        return cls(
            mode="production",
            width=PRODUCTION_WIDTH,
            height=PRODUCTION_HEIGHT,
            fps=PRODUCTION_FPS,
            total_frames=PRODUCTION_FRAMES,
            caption_size=12,
            video_bitrate="8M",
        )

    @classmethod
    def fixture(
        cls,
        *,
        width: int,
        height: int,
        fps: int,
        total_frames: int,
        caption_size: int,
        video_bitrate: str,
    ) -> RenderConfig:
        """Return an explicitly non-production short/small render configuration."""
        config = cls(
            mode="fixture",
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            caption_size=caption_size,
            video_bitrate=video_bitrate,
        )
        _validate_config(config)
        if (width, height, total_frames) == (
            PRODUCTION_WIDTH,
            PRODUCTION_HEIGHT,
            PRODUCTION_FRAMES,
        ):
            raise RenderError("fixture configuration must remain visibly non-production")
        return config


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Paths, cache decisions, and decoded hashes from one completed render."""

    base_video: Path
    narrated: Path
    speaker: Path
    manifest_path: Path
    rebuilt_states: tuple[str, ...]
    timeline_rebuilt: bool
    base_picture_sha256: str
    decoded_picture_sha256: Mapping[str, str]
    decoded_pcm_sha256: Mapping[str, str]


def validate_required_filters(listing: str) -> None:
    """Reject an FFmpeg filter listing missing any render dependency."""
    missing_filters = sorted(
        name
        for name in _REQUIRED_FILTERS
        if re.search(
            rf"^\s*\S+\s+{re.escape(name)}\s",
            listing,
            re.MULTILINE,
        )
        is None
    )
    if missing_filters:
        raise RenderError("ffmpeg is missing filters: " + ", ".join(missing_filters))


def validate_capability_evidence(
    evidence: CapabilityEvidence,
    *,
    expected_fonts: Sequence[ExpectedFont] = PRODUCTION_FONTS,
) -> RenderCapabilities:
    """Interpret probe output and fail on any unapproved substitution."""
    ffmpeg_version, configuration = _parse_version(
        evidence.ffmpeg_version, "ffmpeg", evidence.ffmpeg_path
    )
    ffprobe_version, _ = _parse_version(evidence.ffprobe_version, "ffprobe", evidence.ffprobe_path)
    if ffmpeg_version != REFERENCE_FFMPEG_VERSION:
        raise RenderError(
            f"ffmpeg version must be exactly {REFERENCE_FFMPEG_VERSION}, got {ffmpeg_version}"
        )
    if ffprobe_version != REFERENCE_FFMPEG_VERSION:
        raise RenderError(
            f"ffprobe version must be exactly {REFERENCE_FFMPEG_VERSION}, got {ffprobe_version}"
        )
    missing_configuration = sorted(_REQUIRED_CONFIGURATION.difference(configuration))
    if missing_configuration:
        raise RenderError("ffmpeg configuration is missing: " + ", ".join(missing_configuration))
    validate_required_filters(evidence.filters)
    if (
        re.search(
            rf"^\s*\S+\s+{LIBRSVG_DECODER}\s",
            evidence.decoders,
            re.MULTILINE,
        )
        is None
    ):
        raise RenderError("ffmpeg is missing the required librsvg decoder")
    for encoder in (H264_ENCODER, AAC_ENCODER):
        if (
            re.search(
                rf"^\s*\S+\s+{re.escape(encoder)}\s",
                evidence.encoders,
                re.MULTILINE,
            )
            is None
        ):
            raise RenderError(f"ffmpeg is missing the required {encoder} encoder")
    if not evidence.encoder_help.startswith(f"Encoder {H264_ENCODER} "):
        raise RenderError(f"ffmpeg did not describe the exact {H264_ENCODER} encoder")
    if not evidence.aac_help.startswith(f"Encoder {AAC_ENCODER} "):
        raise RenderError(f"ffmpeg did not describe the exact {AAC_ENCODER} encoder")
    if "frame_length" not in evidence.aac_help:
        raise RenderError(f"{AAC_ENCODER} does not expose deterministic frame length")
    if "fontconfig version " not in evidence.fontconfig_version:
        raise RenderError("fontconfig did not report its version")
    fontconfig_version = evidence.fontconfig_version.strip().removeprefix("fontconfig version ")
    fonts = _parse_fonts(expected_fonts, evidence.font_queries)
    libraries = _parse_linked_libraries(evidence.linked_libraries)
    librsvg = _library_snapshot(libraries, "librsvg-2.so.2", "librsvg")
    encoder_library = _library_snapshot(libraries, "libopenh264.so.8", H264_ENCODER)
    audio_encoder_library = _library_snapshot(libraries, "libfdk-aac.so.2", AAC_ENCODER)
    return RenderCapabilities(
        ffmpeg=evidence.ffmpeg_path,
        ffprobe=evidence.ffprobe_path,
        fontconfig=evidence.fontconfig_path,
        ffmpeg_version=ffmpeg_version,
        ffprobe_version=ffprobe_version,
        ffmpeg_sha256=_sha256_file(evidence.ffmpeg_path, "ffmpeg executable"),
        ffprobe_sha256=_sha256_file(evidence.ffprobe_path, "ffprobe executable"),
        ffmpeg_configuration=tuple(sorted(configuration)),
        fontconfig_version=fontconfig_version,
        fontconfig_sha256=_sha256_file(evidence.fontconfig_path, "fontconfig executable"),
        fonts=fonts,
        librsvg=librsvg,
        encoder_library=encoder_library,
        audio_encoder_library=audio_encoder_library,
        encoder=H264_ENCODER,
        encoder_help_sha256=_sha256_bytes(evidence.encoder_help.encode("utf-8")),
        aac_help_sha256=_sha256_bytes(evidence.aac_help.encode("utf-8")),
        encoder_verified=False,
        audio_encoder_verified=False,
    )


def probe_render_capabilities(
    *,
    work_root: Path,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    fontconfig: str = "fc-match",
    fontquery: str = "fc-query",
    ldd: str = "ldd",
) -> RenderCapabilities:
    """Run the bounded toolchain preflight and verify both real encoders."""
    owned_work_root = _prepare_owned_work_root(work_root)
    ffmpeg_path = _resolve_executable(ffmpeg, "ffmpeg")
    ffprobe_path = _resolve_executable(ffprobe, "ffprobe")
    fontconfig_path = _resolve_executable(fontconfig, "fontconfig")
    fontquery_path = _resolve_executable(fontquery, "font query")
    ldd_path = _resolve_executable(ldd, "dynamic-library probe")
    font_queries = tuple(
        _run_text(
            (
                str(fontquery_path),
                "-f",
                "%{family[0]}\t%{style[0]}\t%{fontversion}\t%{file}\n",
                str(font.path),
            ),
            f"{font.family} font query",
        )
        for font in PRODUCTION_FONTS
    )
    evidence = CapabilityEvidence(
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        fontconfig_path=fontconfig_path,
        fontquery_path=fontquery_path,
        ffmpeg_version=_run_text((str(ffmpeg_path), "-version"), "ffmpeg version"),
        ffprobe_version=_run_text((str(ffprobe_path), "-version"), "ffprobe version"),
        filters=_run_text((str(ffmpeg_path), "-hide_banner", "-filters"), "ffmpeg filters"),
        decoders=_run_text((str(ffmpeg_path), "-hide_banner", "-decoders"), "ffmpeg decoders"),
        encoders=_run_text((str(ffmpeg_path), "-hide_banner", "-encoders"), "ffmpeg encoders"),
        encoder_help=_run_text(
            (str(ffmpeg_path), "-hide_banner", "-h", f"encoder={H264_ENCODER}"),
            f"{H264_ENCODER} help",
        ),
        aac_help=_run_text(
            (str(ffmpeg_path), "-hide_banner", "-h", f"encoder={AAC_ENCODER}"),
            "AAC help",
        ),
        fontconfig_version=_run_text((str(fontconfig_path), "--version"), "fontconfig version"),
        font_queries=font_queries,
        linked_libraries=_run_text((str(ldd_path), str(ffmpeg_path)), "ffmpeg libraries"),
    )
    capabilities = validate_capability_evidence(evidence)
    _run_binary(
        (
            str(capabilities.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=30:d=0.04",
            "-frames:v",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            capabilities.encoder,
            "-b:v",
            "100k",
            "-g",
            "30",
            "-bf",
            "0",
            "-threads",
            "1",
            "-f",
            "h264",
            "-",
        ),
        f"{capabilities.encoder} verification",
    )
    _verify_aac_encoder(capabilities, work_root=owned_work_root)
    return replace(
        capabilities,
        encoder_verified=True,
        audio_encoder_verified=True,
    )


def _verify_aac_encoder(capabilities: RenderCapabilities, *, work_root: Path) -> None:
    """Verify the approved AAC profile preserves an exact sample boundary."""
    verification_samples = AAC_FRAME_LENGTH * 2
    probe_root = work_root / "probes"
    probe_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=probe_root,
        prefix="aac-",
    ) as temporary_directory:
        output = Path(temporary_directory) / "verification.mp4"
        _run_checked(
            (
                str(capabilities.ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-f",
                "lavfi",
                "-i",
                (
                    f"sine=frequency=997:sample_rate={AUDIO_SAMPLE_RATE}:"
                    f"duration={verification_samples / AUDIO_SAMPLE_RATE}"
                ),
                "-af",
                "aformat=sample_fmts=fltp:channel_layouts=stereo",
                "-c:a",
                AAC_ENCODER,
                "-profile:a",
                AAC_PROFILE,
                "-frame_length",
                str(AAC_FRAME_LENGTH),
                "-b:a",
                "192k",
                "-ar",
                str(AUDIO_SAMPLE_RATE),
                "-ac",
                "2",
                "-use_editlist",
                "1",
                str(output),
            ),
            f"{AAC_ENCODER} verification",
        )
        _, byte_count = _hash_command_output(
            (
                str(capabilities.ffmpeg),
                "-v",
                "error",
                "-i",
                str(output),
                "-map",
                "0:a:0",
                "-c:a",
                "pcm_s16le",
                "-f",
                "s16le",
                "-",
            ),
            f"{AAC_ENCODER} decoded verification",
            timeout_seconds=30,
            max_output_bytes=verification_samples * 2 * 2,
        )
    if byte_count != verification_samples * 2 * 2:
        raise RenderError(f"{AAC_ENCODER} did not preserve the exact decoded sample boundary")


def build_scene_clip_command(
    *,
    capabilities: RenderCapabilities,
    config: RenderConfig,
    source_svg: Path,
    destination: Path,
    frame_count: int,
) -> tuple[str, ...]:
    """Return the exact SVG-state clip command without executing it."""
    if frame_count <= 0:
        raise RenderError("state frame_count must be positive")
    return (
        str(capabilities.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(config.fps),
        "-c:v",
        LIBRSVG_DECODER,
        "-i",
        str(source_svg),
        "-an",
        "-vf",
        (
            f"scale={config.width}:{config.height}:flags=lanczos,"
            f"format=yuv420p,setpts=N/({config.fps}*TB)"
        ),
        "-frames:v",
        str(frame_count),
        "-fps_mode",
        "cfr",
        *_encoded_video_options(capabilities, config),
        *_deterministic_mp4_options(config),
        str(destination),
    )


def build_concat_command(
    *,
    capabilities: RenderCapabilities,
    config: RenderConfig,
    clips: Sequence[Path],
    destination: Path,
) -> tuple[str, ...]:
    """Return the ordered frame-concat command for all fourteen state clips."""
    if len(clips) != 14:
        raise RenderError("the frame graph must concatenate exactly 14 state clips")
    inputs = tuple(argument for clip in clips for argument in ("-i", str(clip)))
    labels = "".join(f"[{index}:v:0]" for index in range(len(clips)))
    graph = (
        f"{labels}concat=n={len(clips)}:v=1:a=0,"
        f"setpts=N/({config.fps}*TB),format=yuv420p[shared_picture]"
    )
    return (
        str(capabilities.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        *inputs,
        "-filter_complex",
        graph,
        "-map",
        "[shared_picture]",
        "-an",
        "-frames:v",
        str(config.total_frames),
        "-fps_mode",
        "cfr",
        *_encoded_video_options(capabilities, config),
        *_deterministic_mp4_options(config),
        str(destination),
    )


def build_variant_command(
    *,
    capabilities: RenderCapabilities,
    project: ProjectManifest,
    config: RenderConfig,
    base_video: Path,
    captions_path: Path,
    selected_wav: Path,
) -> tuple[str, ...]:
    """Return the one invocation that creates both delivery variants."""
    fonts_dir = capabilities.fonts[0].path.parent
    _require_filter_path(captions_path, "captions_path")
    _require_filter_path(fonts_dir, "fonts directory")
    subtitle_style = (
        f"FontName=Noto Sans,FontSize={config.caption_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=12"
    )
    video_graph = (
        "[0:v:0]"
        f"subtitles=filename={captions_path.as_posix()}:"
        f"fontsdir={fonts_dir.as_posix()}:force_style='{subtitle_style}',"
        f"setpts=N/({config.fps}*TB),format=yuv420p[narrated_video]"
    )
    audio_graph = _audio_filter_graph(project, config)
    graph = f"{video_graph};{audio_graph}"
    return (
        str(capabilities.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(base_video),
        "-i",
        str(selected_wav),
        "-filter_complex",
        graph,
        "-map",
        "[narrated_video]",
        "-map",
        "[narrated_audio]",
        "-frames:v",
        str(config.total_frames),
        "-fps_mode",
        "cfr",
        *_encoded_video_options(capabilities, config),
        *_encoded_audio_options(config),
        *_deterministic_mp4_options(config),
        str(project.output.narrated),
        "-map",
        "0:v:0",
        "-map",
        "[speaker_audio]",
        "-frames:v",
        str(config.total_frames),
        "-c:v",
        "copy",
        *_encoded_audio_options(config),
        *_deterministic_mp4_options(config),
        str(project.output.speaker),
    )


def render_timeline(
    *,
    repository_root: Path,
    project: ProjectManifest,
    states: Sequence[RenderedSceneState],
    captions_path: Path,
    selected_wav: Path,
    selected_wav_sha256: str,
    config: RenderConfig | None = None,
    capabilities: RenderCapabilities | None = None,
) -> RenderResult:
    """Render cached state clips, one shared picture, and both final variants."""
    selected_config = config if config is not None else RenderConfig.production()
    _validate_render_inputs(repository_root, project, states, selected_config)
    actual_wav_sha256 = _sha256_file(selected_wav, "selected narration WAV")
    if actual_wav_sha256 != selected_wav_sha256:
        raise RenderError("selected narration WAV checksum does not match")
    captions_sha256 = _sha256_file(captions_path, "captions SRT")
    output_root = project.output.root.resolve()
    owned_work_root = _prepare_owned_work_root(output_root / "work")
    selected_capabilities = capabilities or probe_render_capabilities(
        work_root=owned_work_root,
    )
    if not selected_capabilities.encoder_verified:
        raise RenderError("H.264 encoder must pass a real verification encode")
    if not selected_capabilities.audio_encoder_verified:
        raise RenderError("AAC encoder must pass an exact-boundary verification encode")

    work_root = owned_work_root / "render-cache"
    staging_root = owned_work_root / "staging"
    state_root = work_root / "states"
    timeline_root = work_root / "timelines"
    state_root.mkdir(parents=True, exist_ok=True)
    timeline_root.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    state_records: list[dict[str, object]] = []
    rebuilt_states: list[str] = []
    clips: list[Path] = []
    for state in states:
        record, clip, rebuilt = _render_state_clip(
            state,
            state_root=state_root,
            capabilities=selected_capabilities,
            config=selected_config,
        )
        state_records.append(record)
        clips.append(clip)
        if rebuilt:
            rebuilt_states.append(f"{state.scene_id}/{state.state_id}")

    timeline_key = _cache_key(
        {
            "kind": "shared-picture",
            "clips": [
                {"path": clip.name, "sha256": _sha256_file(clip, "state clip")} for clip in clips
            ],
            "command_contract": _concat_options_manifest(selected_capabilities, selected_config),
        }
    )
    base_video = timeline_root / f"{timeline_key}.mp4"
    base_sidecar = timeline_root / f"{timeline_key}.json"
    timeline_rebuilt = not _cache_entry_valid(base_video, base_sidecar, timeline_key)
    if timeline_rebuilt:
        temporary = base_video.with_name(f".{base_video.name}.tmp.mp4")
        try:
            _run_checked(
                build_concat_command(
                    capabilities=selected_capabilities,
                    config=selected_config,
                    clips=clips,
                    destination=temporary,
                ),
                "shared-picture concat",
            )
            _validate_media_shape(
                base_video=temporary,
                capabilities=selected_capabilities,
                config=selected_config,
                require_audio=False,
            )
            temporary.replace(base_video)
        finally:
            temporary.unlink(missing_ok=True)
        _write_cache_sidecar(base_sidecar, timeline_key, base_video)

    project.output.narrated.parent.mkdir(parents=True, exist_ok=True)
    project.output.speaker.parent.mkdir(parents=True, exist_ok=True)
    project.output.render_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_narrated = _staging_path(
        staging_root,
        "narrated",
        ".mp4",
    )
    temporary_speaker = _staging_path(
        staging_root,
        "speaker",
        ".mp4",
    )
    temporary_project = replace(
        project,
        output=replace(
            project.output,
            narrated=temporary_narrated,
            speaker=temporary_speaker,
        ),
    )
    try:
        _run_checked(
            build_variant_command(
                capabilities=selected_capabilities,
                project=temporary_project,
                config=selected_config,
                base_video=base_video,
                captions_path=captions_path,
                selected_wav=selected_wav,
            ),
            "delivery variants",
        )
        _validate_media_shape(
            base_video=temporary_narrated,
            capabilities=selected_capabilities,
            config=selected_config,
            require_audio=True,
        )
        _validate_media_shape(
            base_video=temporary_speaker,
            capabilities=selected_capabilities,
            config=selected_config,
            require_audio=True,
        )
        temporary_narrated.replace(project.output.narrated)
        temporary_speaker.replace(project.output.speaker)
    finally:
        temporary_narrated.unlink(missing_ok=True)
        temporary_speaker.unlink(missing_ok=True)
    base_probe = _validate_media_shape(
        base_video=base_video,
        capabilities=selected_capabilities,
        config=selected_config,
        require_audio=False,
    )
    output_probes = {
        "narrated": _validate_media_shape(
            base_video=project.output.narrated,
            capabilities=selected_capabilities,
            config=selected_config,
            require_audio=True,
        ),
        "speaker": _validate_media_shape(
            base_video=project.output.speaker,
            capabilities=selected_capabilities,
            config=selected_config,
            require_audio=True,
        ),
    }
    base_picture_sha256 = _decoded_video_hash(base_video, selected_capabilities)
    decoded_picture = {
        name: _decoded_video_hash(path, selected_capabilities)
        for name, path in (
            ("narrated", project.output.narrated),
            ("speaker", project.output.speaker),
        )
    }
    decoded_pcm_records = {
        name: _decoded_pcm_record(path, selected_capabilities, selected_config)
        for name, path in (
            ("narrated", project.output.narrated),
            ("speaker", project.output.speaker),
        )
    }
    if decoded_picture["speaker"] != base_picture_sha256:
        raise RenderError("speaker picture is not the shared decoded picture")

    source_revision = _run_text(
        ("git", "-C", str(repository_root.resolve()), "rev-parse", "HEAD"),
        "source revision",
    ).strip()
    manifest = _render_manifest(
        repository_root=repository_root.resolve(),
        project=project,
        config=selected_config,
        capabilities=selected_capabilities,
        source_revision=source_revision,
        captions_path=captions_path,
        captions_sha256=captions_sha256,
        selected_wav=selected_wav,
        selected_wav_sha256=actual_wav_sha256,
        state_records=state_records,
        base_video=base_video,
        base_probe=base_probe,
        base_picture_sha256=base_picture_sha256,
        timeline_key=timeline_key,
        output_probes=output_probes,
        decoded_picture=decoded_picture,
        decoded_pcm_records=decoded_pcm_records,
    )
    _atomic_write_json(
        project.output.render_manifest,
        manifest,
        temporary_root=staging_root,
    )
    return RenderResult(
        base_video=base_video,
        narrated=project.output.narrated,
        speaker=project.output.speaker,
        manifest_path=project.output.render_manifest,
        rebuilt_states=tuple(rebuilt_states),
        timeline_rebuilt=timeline_rebuilt,
        base_picture_sha256=base_picture_sha256,
        decoded_picture_sha256=decoded_picture,
        decoded_pcm_sha256={
            name: cast(str, record["sha256"]) for name, record in decoded_pcm_records.items()
        },
    )


def render_production(
    repository_root: Path,
    *,
    selected_wav: Path,
    selected_wav_sha256: str,
) -> RenderResult:
    """Compose real production states and render without any fixture fallback."""
    root = repository_root.resolve()
    production_root = root / "media" / "repository-explainer"
    project = load_project(production_root / "project.json", repository_root=root)
    capabilities = probe_render_capabilities(work_root=project.output.root / "work")
    states = compose_scene_states(root)
    return render_timeline(
        repository_root=root,
        project=project,
        states=states,
        captions_path=production_root / "captions.srt",
        selected_wav=selected_wav,
        selected_wav_sha256=selected_wav_sha256,
        capabilities=capabilities,
    )


def _audio_filter_graph(project: ProjectManifest, config: RenderConfig) -> str:
    total_samples = _total_audio_samples(config)
    if config.cue_samples > total_samples:
        raise RenderError("fixture is too short for the declared cue synthesis")
    filters = [
        (
            f"sine=frequency={config.bed_frequency}:sample_rate={config.audio_sample_rate},"
            f"atrim=end_sample={total_samples},asetpts=N/SR/TB,"
            f"volume={config.bed_volume},"
            f"aformat=sample_fmts=fltp:sample_rates={config.audio_sample_rate}:"
            "channel_layouts=stereo[bed_0]"
        )
    ]
    cue_labels: list[str] = []
    for index, scene in enumerate(project.scenes[1:], start=1):
        delay_samples = _frame_to_sample(scene.start_frame, config)
        cue_label = f"cue_{index}"
        cue_labels.append(cue_label)
        filters.append(
            f"sine=frequency={config.cue_frequency}:"
            f"sample_rate={config.audio_sample_rate},"
            f"atrim=end_sample={config.cue_samples},"
            f"afade=t=out:start_sample={config.cue_fade_start_sample}:"
            f"nb_samples={config.cue_fade_samples},"
            f"adelay={delay_samples}S:all=1,"
            f"apad=whole_len={total_samples},atrim=end_sample={total_samples},"
            f"asetpts=N/SR/TB,volume={config.cue_volume},"
            f"aformat=sample_fmts=fltp:sample_rates={config.audio_sample_rate}:"
            f"channel_layouts=stereo[{cue_label}]"
        )
    mixed_inputs = "[bed_0]" + "".join(f"[{label}]" for label in cue_labels)
    filters.append(
        f"{mixed_inputs}amix=inputs={1 + len(cue_labels)}:"
        "duration=longest:dropout_transition=0:normalize=0,"
        f"atrim=end_sample={total_samples},asetpts=N/SR/TB,"
        "asplit=2[bed_for_narrated][bed_for_speaker]"
    )
    filters.append(
        f"[1:a:0]aresample={config.audio_sample_rate}:first_pts=0,"
        f"apad=whole_len={total_samples},atrim=end_sample={total_samples},"
        f"asetpts=N/SR/TB,aformat=sample_fmts=fltp:"
        f"sample_rates={config.audio_sample_rate}:channel_layouts=stereo[speech]"
    )
    filters.append(
        "[speech][bed_for_narrated]"
        "amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-16:LRA=7:TP=-1:linear=true,volume=1.3dB,"
        f"aresample={config.audio_sample_rate}:first_pts=0,"
        f"apad=whole_len={total_samples},atrim=end_sample={total_samples},"
        "asetpts=N/SR/TB[narrated_audio]"
    )
    filters.append(
        "[bed_for_speaker]"
        "loudnorm=I=-28:LRA=7:TP=-6:linear=true,"
        f"aresample={config.audio_sample_rate}:first_pts=0,"
        f"apad=whole_len={total_samples},atrim=end_sample={total_samples},"
        "asetpts=N/SR/TB[speaker_audio]"
    )
    return ";".join(filters)


def _render_state_clip(
    state: RenderedSceneState,
    *,
    state_root: Path,
    capabilities: RenderCapabilities,
    config: RenderConfig,
) -> tuple[dict[str, object], Path, bool]:
    _validate_identifier(state.scene_id, "scene id")
    _validate_identifier(state.state_id, "state id")
    frame_count = state.end_frame - state.start_frame
    source_sha256 = _sha256_bytes(state.svg)
    key = _cache_key(
        {
            "kind": "state-clip",
            "scene_id": state.scene_id,
            "state_id": state.state_id,
            "start_frame": state.start_frame,
            "end_frame": state.end_frame,
            "source_sha256": source_sha256,
            "command_contract": _scene_options_manifest(capabilities, config),
        }
    )
    prefix = f"{state.scene_id}--{state.state_id}--{key}"
    source = state_root / f"{prefix}.svg"
    clip = state_root / f"{prefix}.mp4"
    sidecar = state_root / f"{prefix}.json"
    if not source.exists() or _sha256_file(source, "cached SVG") != source_sha256:
        _atomic_write_bytes(source, state.svg)
    rebuilt = not _cache_entry_valid(clip, sidecar, key)
    if rebuilt:
        temporary = clip.with_name(f".{clip.name}.tmp.mp4")
        try:
            _run_checked(
                build_scene_clip_command(
                    capabilities=capabilities,
                    config=config,
                    source_svg=source,
                    destination=temporary,
                    frame_count=frame_count,
                ),
                f"state clip {state.scene_id}/{state.state_id}",
            )
            temporary.replace(clip)
        finally:
            temporary.unlink(missing_ok=True)
        _write_cache_sidecar(sidecar, key, clip)
    return (
        {
            "scene_id": state.scene_id,
            "state_id": state.state_id,
            "start_frame": state.start_frame,
            "end_frame": state.end_frame,
            "frame_count": frame_count,
            "source_sha256": source_sha256,
            "cache_key": key,
            "clip_sha256": _sha256_file(clip, "state clip"),
            "references": [
                {
                    "kind": reference.kind,
                    "path": reference.path,
                    "sha256": reference.sha256,
                    "revision": reference.revision,
                }
                for reference in state.references
            ],
        },
        clip,
        rebuilt,
    )


def _render_manifest(
    *,
    repository_root: Path,
    project: ProjectManifest,
    config: RenderConfig,
    capabilities: RenderCapabilities,
    source_revision: str,
    captions_path: Path,
    captions_sha256: str,
    selected_wav: Path,
    selected_wav_sha256: str,
    state_records: Sequence[dict[str, object]],
    base_video: Path,
    base_probe: Mapping[str, object],
    base_picture_sha256: str,
    timeline_key: str,
    output_probes: Mapping[str, Mapping[str, object]],
    decoded_picture: Mapping[str, str],
    decoded_pcm_records: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    output_inputs = {
        "narrated": [
            "shared_picture",
            "captions_srt",
            "selected_narration_wav",
            "procedural_tonal_bed_and_cues",
        ],
        "speaker": ["shared_picture", "procedural_tonal_bed_and_cues"],
    }
    output_paths = {
        "narrated": project.output.narrated,
        "speaker": project.output.speaker,
    }
    outputs = {
        name: {
            "path": _manifest_path(repository_root, path),
            "inputs": output_inputs[name],
            "sha256": _sha256_file(path, f"{name} output"),
            "decoded_video_sha256": decoded_picture[name],
            "decoded_pcm_sha256": decoded_pcm_records[name]["sha256"],
            "decoded_audio_samples_per_channel": decoded_pcm_records[name]["samples_per_channel"],
            "probe": output_probes[name],
        }
        for name, path in output_paths.items()
    }
    return {
        "schema_version": RENDER_SCHEMA_VERSION,
        "source_revision": source_revision,
        "project_timing": {
            "width": config.width,
            "height": config.height,
            "fps": config.fps,
            "total_frames": config.total_frames,
            "total_audio_samples": _total_audio_samples(config),
            "scenes": [
                {
                    "id": scene.id,
                    "start_frame": scene.start_frame,
                    "end_frame": scene.end_frame,
                }
                for scene in project.scenes
            ],
            "states": list(state_records),
        },
        "inputs": {
            "project_contract": {
                "sha256": _cache_key(_project_contract_payload(project)),
            },
            "captions_srt": {
                "path": _manifest_path(repository_root, captions_path),
                "sha256": captions_sha256,
            },
            "selected_narration_wav": {
                "path": _manifest_path(repository_root, selected_wav),
                "sha256": selected_wav_sha256,
                "provider_required_for_reproduction": False,
            },
            "render_recipe": {
                "path": _manifest_path(repository_root, Path(__file__).resolve()),
                "sha256": _sha256_file(Path(__file__), "render recipe"),
            },
        },
        "synthesis": _synthesis_manifest(project, config),
        "audio_targets": {
            "narrated": {"integrated_lufs": -16, "true_peak_dbtp": -1},
            "speaker": {"integrated_lufs": -28, "true_peak_dbtp": -6},
        },
        "toolchain": _toolchain_manifest(capabilities, config),
        "shared_picture": {
            "path": _manifest_path(repository_root, base_video),
            "cache_key": timeline_key,
            "sha256": _sha256_file(base_video, "shared picture"),
            "decoded_video_sha256": base_picture_sha256,
            "probe": base_probe,
        },
        "outputs": outputs,
    }


def _toolchain_manifest(
    capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    return {
        "ffmpeg": {
            "path": str(capabilities.ffmpeg),
            "version": capabilities.ffmpeg_version,
            "sha256": capabilities.ffmpeg_sha256,
            "configuration": list(capabilities.ffmpeg_configuration),
        },
        "ffprobe": {
            "path": str(capabilities.ffprobe),
            "version": capabilities.ffprobe_version,
            "sha256": capabilities.ffprobe_sha256,
        },
        "librsvg": {
            "decoder": LIBRSVG_DECODER,
            "soname": capabilities.librsvg.soname,
            "path": str(capabilities.librsvg.path),
            "version": capabilities.librsvg.version,
            "sha256": capabilities.librsvg.sha256,
        },
        "fontconfig": {
            "path": str(capabilities.fontconfig),
            "version": capabilities.fontconfig_version,
            "sha256": capabilities.fontconfig_sha256,
        },
        "fonts": [
            {
                "family": font.family,
                "style": font.style,
                "font_version": font.font_version,
                "path": str(font.path),
                "sha256": font.sha256,
            }
            for font in capabilities.fonts
        ],
        "encoder": {
            "name": capabilities.encoder,
            "verified": capabilities.encoder_verified,
            "help_sha256": capabilities.encoder_help_sha256,
            "library": {
                "soname": capabilities.encoder_library.soname,
                "path": str(capabilities.encoder_library.path),
                "version": capabilities.encoder_library.version,
                "sha256": capabilities.encoder_library.sha256,
            },
        },
        "audio_encoder": {
            "name": AAC_ENCODER,
            "profile": AAC_PROFILE,
            "frame_length": AAC_FRAME_LENGTH,
            "verified": capabilities.audio_encoder_verified,
            "help_sha256": capabilities.aac_help_sha256,
            "library": {
                "soname": capabilities.audio_encoder_library.soname,
                "path": str(capabilities.audio_encoder_library.path),
                "version": capabilities.audio_encoder_library.version,
                "sha256": capabilities.audio_encoder_library.sha256,
            },
        },
        "options": {
            "render_config": _render_config_manifest(config),
            "state_clip": _scene_command_manifest(capabilities, config),
            "concat": _concat_command_manifest(capabilities, config),
            "variants": {
                "video": list(_encoded_video_options(capabilities, config)),
                "audio": list(_encoded_audio_options(config)),
                "container": list(_deterministic_mp4_options(config)),
            },
        },
    }


def toolchain_manifest(
    capabilities: RenderCapabilities,
    config: RenderConfig,
) -> dict[str, object]:
    """Expose the exact renderer-owned toolchain contract to promotion verification."""
    return _toolchain_manifest(capabilities, config)


def _synthesis_manifest(project: ProjectManifest, config: RenderConfig) -> dict[str, object]:
    return {
        "method": "FFmpeg sine sources mixed in the render filter graph",
        "sample_rate": config.audio_sample_rate,
        "total_samples": _total_audio_samples(config),
        "bed": {
            "frequency_hz": config.bed_frequency,
            "volume": config.bed_volume,
        },
        "cues": {
            "frequency_hz": config.cue_frequency,
            "duration_samples": config.cue_samples,
            "fade_start_sample": config.cue_fade_start_sample,
            "fade_samples": config.cue_fade_samples,
            "volume": config.cue_volume,
            "start_frames": [scene.start_frame for scene in project.scenes[1:]],
            "start_samples": [
                _frame_to_sample(scene.start_frame, config) for scene in project.scenes[1:]
            ],
        },
        "external_music_inputs": [],
    }


def _project_contract_payload(project: ProjectManifest) -> dict[str, object]:
    return {
        "media": {
            "width": project.media.width,
            "height": project.media.height,
            "fps": project.media.fps,
            "total_frames": project.media.total_frames,
        },
        "scenes": [
            {
                "id": scene.id,
                "start_frame": scene.start_frame,
                "end_frame": scene.end_frame,
                "states": [
                    {
                        "id": state.id,
                        "start_frame": state.start_frame,
                        "end_frame": state.end_frame,
                    }
                    for state in scene.visual_states
                ],
            }
            for scene in project.scenes
        ],
        "output": {
            "root": str(project.output.root),
            "narrated": str(project.output.narrated),
            "speaker": str(project.output.speaker),
            "render_manifest": str(project.output.render_manifest),
        },
    }


def _validate_render_inputs(
    repository_root: Path,
    project: ProjectManifest,
    states: Sequence[RenderedSceneState],
    config: RenderConfig,
) -> None:
    _validate_config(config)
    if (
        project.media.width,
        project.media.height,
        project.media.fps,
        project.media.total_frames,
    ) != (config.width, config.height, config.fps, config.total_frames):
        raise RenderError("render configuration does not match the project media contract")
    if config.mode == "production" and config != RenderConfig.production():
        raise RenderError("production picture and encoder parameters are immutable")
    output_root = project.output.root.resolve()
    if output_root.name != "video" or output_root.parent.name != "dist":
        raise RenderError("render output root must be owned dist/video")
    for path in (
        project.output.narrated,
        project.output.speaker,
        project.output.render_manifest,
    ):
        _require_within(path.resolve(), output_root, "render output")
    expected = tuple(
        (scene.id, state.id, state.start_frame, state.end_frame)
        for scene in project.scenes
        for state in scene.visual_states
    )
    actual = tuple(
        (state.scene_id, state.state_id, state.start_frame, state.end_frame) for state in states
    )
    if len(expected) != 14 or actual != expected:
        raise RenderError("render states must match the exact ordered 14-state project graph")
    cursor = 0
    for state in states:
        if state.start_frame != cursor or state.end_frame <= state.start_frame:
            raise RenderError("render states must cover a positive, gap-free frame timeline")
        cursor = state.end_frame
    if cursor != config.total_frames:
        raise RenderError("render states do not end at the project frame boundary")
    if config.mode == "production":
        _require_within(
            project.output.root.resolve(),
            repository_root.resolve(),
            "output root",
        )


def _validate_config(config: RenderConfig) -> None:
    if config.mode not in {"production", "fixture"}:
        raise RenderError("render mode must be production or fixture")
    if (
        min(
            config.width,
            config.height,
            config.fps,
            config.total_frames,
            config.caption_size,
        )
        <= 0
    ):
        raise RenderError("render dimensions, timing, and caption size must be positive")
    if config.fps != PRODUCTION_FPS:
        raise RenderError("the frame graph must retain the approved 30 fps timebase")
    if config.audio_sample_rate != AUDIO_SAMPLE_RATE:
        raise RenderError("audio must retain the approved 48000 Hz sample clock")
    if config.audio_sample_rate % config.fps != 0:
        raise RenderError("audio sample rate must divide exactly by the picture frame rate")
    if _total_audio_samples(config) % AAC_FRAME_LENGTH != 0:
        raise RenderError("program audio must divide exactly into approved AAC frames")
    if re.fullmatch(r"[1-9][0-9]*[kM]", config.video_bitrate) is None:
        raise RenderError("video_bitrate must be a positive deterministic k/M value")
    if config.cue_fade_start_sample + config.cue_fade_samples != config.cue_samples:
        raise RenderError("cue fade must end exactly at the cue sample boundary")


def _validate_media_shape(
    *,
    base_video: Path,
    capabilities: RenderCapabilities,
    config: RenderConfig,
    require_audio: bool,
) -> dict[str, object]:
    probe = _ffprobe(base_video, capabilities)
    streams = cast(list[dict[str, object]], probe.get("streams", []))
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise RenderError("rendered media must contain exactly one video stream")
    video = videos[0]
    expected_video = {
        "codec_name": "h264",
        "width": config.width,
        "height": config.height,
        "r_frame_rate": f"{config.fps}/1",
    }
    if any(video.get(key) != value for key, value in expected_video.items()):
        raise RenderError("rendered video stream does not match H.264 picture settings")
    try:
        frame_count = int(cast(str, video["nb_read_frames"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError("ffprobe did not report a decoded frame count") from exc
    if frame_count != config.total_frames:
        raise RenderError("decoded video frame count does not match the program boundary")
    if require_audio:
        if len(audios) != 1:
            raise RenderError("delivery media must contain exactly one audio stream")
        audio = audios[0]
        if (
            audio.get("codec_name"),
            audio.get("profile"),
            audio.get("sample_rate"),
            audio.get("channels"),
        ) != ("aac", "LD", str(config.audio_sample_rate), 2):
            raise RenderError("delivery audio must be AAC-LD stereo at 48000 Hz")
        probe["program_audio_boundary"] = _validate_audio_packet_boundary(
            probe,
            audio_stream_index=cast(int, audio["index"]),
            total_samples=_total_audio_samples(config),
        )
    elif audios:
        raise RenderError("shared picture cache must not contain audio")
    probe.pop("packets", None)
    return probe


def _ffprobe(path: Path, capabilities: RenderCapabilities) -> dict[str, object]:
    raw = _run_text(
        (
            str(capabilities.ffprobe),
            "-v",
            "error",
            "-count_frames",
            "-show_packets",
            "-show_entries",
            (
                "format=format_name,duration:"
                "stream=index,codec_type,codec_name,profile,width,height,pix_fmt,"
                "r_frame_rate,duration,nb_read_frames,channels,sample_rate,time_base:"
                "packet=stream_index,pts,duration,side_data_list"
            ),
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ),
        "ffprobe media inspection",
    )
    try:
        decoded = cast(object, json.loads(raw))
    except json.JSONDecodeError as exc:
        raise RenderError("ffprobe returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise RenderError("ffprobe JSON must be an object")
    return cast(dict[str, object], decoded)


def _decoded_video_hash(path: Path, capabilities: RenderCapabilities) -> str:
    digest, _ = _hash_command_output(
        (
            str(capabilities.ffmpeg),
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ),
        "decoded video semantic hash",
        timeout_seconds=600,
        max_output_bytes=64 * 1024 * 1024,
    )
    return digest


def _decoded_pcm_record(
    path: Path, capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    total_samples = _total_audio_samples(config)
    digest, byte_count = _hash_command_output(
        (
            str(capabilities.ffmpeg),
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-c:a",
            "pcm_s16le",
            "-f",
            "s16le",
            "-",
        ),
        "decoded PCM semantic hash",
        timeout_seconds=600,
        max_output_bytes=total_samples * 2 * 2,
    )
    bytes_per_sample_frame = 2 * 2
    if byte_count % bytes_per_sample_frame != 0:
        raise RenderError("decoded stereo PCM ended between sample frames")
    samples_per_channel = byte_count // bytes_per_sample_frame
    if samples_per_channel != total_samples:
        raise RenderError("decoded program audio extends outside the exact frame boundary")
    return {
        "sha256": digest,
        "bytes": byte_count,
        "channels": 2,
        "sample_format": "s16le",
        "samples_per_channel": samples_per_channel,
    }


def _validate_audio_packet_boundary(
    probe: Mapping[str, object],
    *,
    audio_stream_index: int,
    total_samples: int,
) -> dict[str, object]:
    streams = cast(list[dict[str, object]], probe.get("streams", []))
    audio_stream = next(
        (
            stream
            for stream in streams
            if stream.get("index") == audio_stream_index and stream.get("codec_type") == "audio"
        ),
        None,
    )
    if audio_stream is None or audio_stream.get("time_base") != f"1/{AUDIO_SAMPLE_RATE}":
        raise RenderError("AAC packet time base must be exactly one audio sample")
    packets = [
        packet
        for packet in cast(list[dict[str, object]], probe.get("packets", []))
        if packet.get("stream_index") == audio_stream_index
    ]
    if not packets:
        raise RenderError("ffprobe reported no AAC packets")
    try:
        starts_and_ends = [
            (
                int(cast(int | str, packet["pts"])),
                int(cast(int | str, packet["pts"])) + int(cast(int | str, packet["duration"])),
            )
            for packet in packets
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError("ffprobe AAC packet timing was incomplete") from exc
    first_side_data = cast(list[dict[str, object]], packets[0].get("side_data_list", []))
    skip_samples = next(
        (
            int(cast(int | str, entry.get("skip_samples", 0)))
            for entry in first_side_data
            if entry.get("side_data_type") == "Skip Samples"
        ),
        0,
    )
    if skip_samples != AAC_FRAME_LENGTH or starts_and_ends[0][0] != -skip_samples:
        raise RenderError("AAC encoder priming is not represented as skip metadata")
    final_packet = packets[-1]
    try:
        final_packet_pts = int(cast(int | str, final_packet["pts"]))
        final_packet_duration = int(cast(int | str, final_packet["duration"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError("ffprobe final AAC packet timing was incomplete") from exc
    final_side_data = cast(list[dict[str, object]], final_packet.get("side_data_list", []))
    final_skip_samples = next(
        (
            int(cast(int | str, entry.get("skip_samples", 0)))
            for entry in final_side_data
            if entry.get("side_data_type") == "Skip Samples"
        ),
        0,
    )
    final_discard_padding = next(
        (
            int(cast(int | str, entry.get("discard_padding", 0)))
            for entry in final_side_data
            if entry.get("side_data_type") == "Skip Samples"
        ),
        0,
    )
    effective_final_end = final_packet_pts + final_packet_duration - final_discard_padding
    packet_after_boundary = any(start >= total_samples for start, _ in starts_and_ends)
    if (
        final_packet_pts != total_samples - AAC_FRAME_LENGTH
        or final_packet_duration != AAC_FRAME_LENGTH
        or final_skip_samples != 0
        or final_discard_padding != 0
        or effective_final_end != total_samples
        or packet_after_boundary
    ):
        raise RenderError("AAC packet metadata extends outside the program boundary")
    return {
        "priming_skip_samples": skip_samples,
        "final_packet_pts": final_packet_pts,
        "final_packet_duration": final_packet_duration,
        "final_packet_skip_samples": final_skip_samples,
        "final_discard_padding_samples": final_discard_padding,
        "first_program_sample": 0,
        "last_program_sample_exclusive": total_samples,
        "packet_after_program_boundary": packet_after_boundary,
    }


def _scene_options_manifest(
    capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    return {
        "command": _scene_command_manifest(capabilities, config),
        "render_toolchain": _toolchain_manifest(capabilities, config),
    }


def _scene_command_manifest(
    capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    return {
        "decoder": LIBRSVG_DECODER,
        "width": config.width,
        "height": config.height,
        "fps": config.fps,
        "pixel_format": "yuv420p",
        "encoder": capabilities.encoder,
        "video_options": list(_encoded_video_options(capabilities, config)),
        "container_options": list(_deterministic_mp4_options(config)),
    }


def _concat_options_manifest(
    capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    return {
        "command": _concat_command_manifest(capabilities, config),
        "render_toolchain": _toolchain_manifest(capabilities, config),
    }


def _concat_command_manifest(
    capabilities: RenderCapabilities, config: RenderConfig
) -> dict[str, object]:
    return {
        "state_count": 14,
        "filter": f"concat=n=14:v=1:a=0,setpts=N/({config.fps}*TB)",
        "total_frames": config.total_frames,
        "video_options": list(_encoded_video_options(capabilities, config)),
        "container_options": list(_deterministic_mp4_options(config)),
    }


def _render_config_manifest(config: RenderConfig) -> dict[str, object]:
    return {
        "mode": config.mode,
        "width": config.width,
        "height": config.height,
        "fps": config.fps,
        "total_frames": config.total_frames,
        "caption_size": config.caption_size,
        "video_bitrate": config.video_bitrate,
        "audio_sample_rate": config.audio_sample_rate,
        "audio_bitrate": config.audio_bitrate,
        "cue_frequency": config.cue_frequency,
        "cue_samples": config.cue_samples,
        "cue_fade_start_sample": config.cue_fade_start_sample,
        "cue_fade_samples": config.cue_fade_samples,
        "bed_frequency": config.bed_frequency,
        "bed_volume": config.bed_volume,
        "cue_volume": config.cue_volume,
    }


def _encoded_video_options(
    capabilities: RenderCapabilities, config: RenderConfig
) -> tuple[str, ...]:
    return (
        "-c:v",
        capabilities.encoder,
        "-b:v",
        config.video_bitrate,
        "-profile:v",
        "high",
        "-g",
        str(config.fps),
        "-bf",
        "0",
        "-allow_skip_frames",
        "0",
        "-threads",
        "1",
        "-pix_fmt",
        "yuv420p",
    )


def _encoded_audio_options(config: RenderConfig) -> tuple[str, ...]:
    return (
        "-c:a",
        AAC_ENCODER,
        "-profile:a",
        AAC_PROFILE,
        "-frame_length",
        str(AAC_FRAME_LENGTH),
        "-b:a",
        config.audio_bitrate,
        "-ar",
        str(config.audio_sample_rate),
        "-ac",
        "2",
    )


def _deterministic_mp4_options(config: RenderConfig) -> tuple[str, ...]:
    return (
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-metadata",
        "creation_time=1970-01-01T00:00:00Z",
        "-video_track_timescale",
        str(config.fps * 1000),
        "-use_editlist",
        "1",
        "-movflags",
        "+faststart",
    )


def _parse_version(raw: str, expected_tool: str, expected_path: Path) -> tuple[str, frozenset[str]]:
    lines = raw.splitlines()
    if not lines:
        raise RenderError(f"{expected_tool} version output was empty")
    match = _VERSION_LINE.match(lines[0])
    if match is None or match.group("tool") != expected_tool:
        raise RenderError(f"{expected_tool} version output was not recognized")
    configuration_line = next((line for line in lines if line.startswith("configuration: ")), "")
    configuration = frozenset(configuration_line.removeprefix("configuration: ").split())
    if not expected_path.is_absolute():
        raise RenderError(f"{expected_tool} path must be absolute")
    return match.group("version"), configuration


def _parse_fonts(
    expected_fonts: Sequence[ExpectedFont], queries: Sequence[str]
) -> tuple[FontSnapshot, ...]:
    if len(expected_fonts) != len(queries):
        raise RenderError("font query count does not match the exact font contract")
    snapshots: list[FontSnapshot] = []
    for expected, query in zip(expected_fonts, queries, strict=True):
        fields = query.strip().split("\t")
        if len(fields) != 4:
            raise RenderError(f"{expected.family} font query was incomplete")
        family, style, font_version, raw_path = fields
        resolved = Path(raw_path).resolve()
        if (
            family != expected.family
            or style != expected.style
            or resolved != expected.path.resolve()
        ):
            raise RenderError(f"{expected.family} resolved to an unapproved font face")
        sha256 = _sha256_file(resolved, f"{expected.family} font")
        if sha256 != expected.sha256:
            raise RenderError(f"{expected.family} font file checksum changed")
        snapshots.append(
            FontSnapshot(
                family=family,
                style=style,
                font_version=font_version,
                path=resolved,
                sha256=sha256,
            )
        )
    return tuple(snapshots)


def _parse_linked_libraries(raw: str) -> dict[str, Path]:
    libraries: dict[str, Path] = {}
    for line in raw.splitlines():
        match = _LIBRARY_LINE.match(line)
        if match is not None:
            libraries[match.group("name")] = Path(match.group("path"))
    return libraries


def _library_snapshot(libraries: Mapping[str, Path], soname: str, label: str) -> LibrarySnapshot:
    try:
        linked_path = libraries[soname]
    except KeyError as exc:
        raise RenderError(f"ffmpeg is not linked to the required {label} library") from exc
    path = linked_path.resolve()
    if not path.is_file():
        raise RenderError(f"{label} linked library does not resolve to a file")
    version_match = re.search(r"\.so\.(?P<version>\d+(?:\.\d+)+)$", path.name)
    if version_match is None:
        raise RenderError(f"{label} linked library version was not recognizable")
    return LibrarySnapshot(
        soname=soname,
        path=path,
        version=version_match.group("version"),
        sha256=_sha256_file(path, f"{label} library"),
    )


def _cache_entry_valid(path: Path, sidecar: Path, key: str) -> bool:
    if not path.is_file() or not sidecar.is_file():
        return False
    try:
        decoded = cast(object, json.loads(sidecar.read_text(encoding="utf-8")))
    except OSError, UnicodeDecodeError, json.JSONDecodeError:
        return False
    if not isinstance(decoded, dict):
        return False
    record = cast(dict[str, object], decoded)
    return record.get("cache_key") == key and record.get("sha256") == _sha256_file(
        path, "cache entry"
    )


def _write_cache_sidecar(sidecar: Path, key: str, media: Path) -> None:
    _atomic_write_json(
        sidecar,
        {
            "schema_version": 1,
            "cache_key": key,
            "sha256": _sha256_file(media, "cache entry"),
        },
    )


def _cache_key(payload: Mapping[str, object]) -> str:
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return _sha256_bytes(serialized)


def _frame_to_sample(frame: int, config: RenderConfig) -> int:
    numerator = frame * config.audio_sample_rate
    quotient, remainder = divmod(numerator, config.fps)
    if remainder:
        raise RenderError("frame boundary does not map to an exact audio sample")
    return quotient


def _total_audio_samples(config: RenderConfig) -> int:
    return _frame_to_sample(config.total_frames, config)


def _resolve_executable(name: str, label: str) -> Path:
    resolved = shutil.which(name)
    if resolved is None:
        raise RenderError(f"{label} executable was not found")
    return Path(resolved).resolve()


def _run_text(argv: Sequence[str], label: str) -> str:
    try:
        completed = subprocess.run(
            tuple(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"{label} could not complete") from exc
    if completed.returncode != 0:
        raise RenderError(f"{label} failed: {_safe_stderr(completed.stderr)}")
    return f"{completed.stdout}{completed.stderr}"


def _run_binary(argv: Sequence[str], label: str) -> bytes:
    try:
        completed = subprocess.run(
            tuple(argv),
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"{label} could not complete") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise RenderError(f"{label} failed: {_safe_stderr(stderr)}")
    return completed.stdout


def _run_checked(argv: Sequence[str], label: str) -> None:
    try:
        completed = subprocess.run(
            tuple(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"{label} could not complete") from exc
    if completed.returncode != 0:
        raise RenderError(f"{label} failed: {_safe_stderr(completed.stderr)}")


def _hash_command_output(
    argv: Sequence[str],
    label: str,
    *,
    timeout_seconds: float,
    max_output_bytes: int,
) -> tuple[str, int]:
    if timeout_seconds <= 0:
        raise RenderError(f"{label} timeout must be positive")
    if max_output_bytes <= 0:
        raise RenderError(f"{label} output limit must be positive")
    digest = hashlib.sha256()
    byte_count = 0
    stderr_tail = b""
    try:
        process = subprocess.Popen(
            tuple(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise RenderError(f"{label} could not start") from exc
    if process.stdout is None or process.stderr is None:
        _terminate_process_group(process)
        raise RenderError(f"{label} did not expose decoded output")
    deadline = time.monotonic() + timeout_seconds
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(tuple(argv), timeout_seconds)
            events = selector.select(remaining)
            if not events:
                raise subprocess.TimeoutExpired(tuple(argv), timeout_seconds)
            for key, _ in events:
                chunk = os.read(key.fd, 1024 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    byte_count += len(chunk)
                    if byte_count > max_output_bytes:
                        raise RenderError(
                            f"{label} exceeded its {max_output_bytes}-byte output limit"
                        )
                    digest.update(chunk)
                else:
                    stderr_tail = (stderr_tail + chunk)[-65_536:]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(tuple(argv), timeout_seconds)
        returncode = process.wait(timeout=remaining)
        if returncode != 0:
            detail = stderr_tail.decode("utf-8", errors="replace")
            raise RenderError(f"{label} failed: {_safe_stderr(detail)}")
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        raise RenderError(f"{label} timed out after {timeout_seconds:g} seconds") from exc
    except BaseException:
        _terminate_process_group(process)
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return digest.hexdigest(), byte_count


def hash_command_output(
    argv: Sequence[str],
    label: str,
    *,
    timeout_seconds: float,
    max_output_bytes: int,
) -> tuple[str, int]:
    """Hash bounded process output with the renderer's process-group guarantees."""
    return _hash_command_output(
        argv,
        label,
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
    )


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    # Waiting for the leader does not prove its descendants exited: a helper can
    # ignore SIGTERM after the leader is already reaped and keep the pipe open.
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=1)
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        process.wait()


def _safe_stderr(stderr: str) -> str:
    compact = " ".join(stderr.split())
    return compact[-1000:] if compact else "no diagnostic output"


def _sha256_file(path: Path, label: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise RenderError(f"{label} could not be read") from exc
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_write_json(
    path: Path,
    payload: Mapping[str, object],
    *,
    temporary_root: Path | None = None,
) -> None:
    _atomic_write_bytes(
        path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        temporary_root=temporary_root,
    )


def _atomic_write_bytes(
    path: Path,
    payload: bytes,
    *,
    temporary_root: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected_temporary_root = temporary_root or path.parent
    selected_temporary_root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=selected_temporary_root,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _staging_path(root: Path, label: str, suffix: str) -> Path:
    _validate_identifier(label, "staging label")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=root,
        prefix=f"{label}-",
        suffix=suffix,
    )
    os.close(descriptor)
    return Path(temporary_name)


def _validate_identifier(value: str, label: str) -> None:
    if _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise RenderError(f"{label} contains unsafe cache-path characters")


def _require_filter_path(path: Path, label: str) -> None:
    if any(character in path.as_posix() for character in "\\':,;[]"):
        raise RenderError(f"{label} contains an unsupported FFmpeg filter character")


def _require_within(path: Path, root: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RenderError(f"{label} escapes its owned root") from exc


def _prepare_owned_work_root(path: Path) -> Path:
    resolved = path.resolve()
    if (
        resolved.name,
        resolved.parent.name,
        resolved.parent.parent.name,
    ) != ("work", "video", "dist"):
        raise RenderError("render work root must be exactly dist/video/work")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _manifest_path(repository_root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repository_root).as_posix()
    except ValueError:
        return str(resolved)
