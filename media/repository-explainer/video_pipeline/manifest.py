"""Strict JSON loading and invariant checks for the repository explainer project."""

from __future__ import annotations

import json
from collections.abc import Iterable
from itertools import pairwise
from pathlib import Path
from typing import cast

from .models import (
    MediaSettings,
    OutputConfig,
    ProjectManifest,
    Rectangle,
    SafeArea,
    Scene,
    TextSizes,
    VisualState,
)

APPROVED_SCENES: tuple[tuple[str, int, int], ...] = (
    ("problem", 0, 450),
    ("visible-workflow", 450, 1050),
    ("caught-defect", 1050, 1800),
    ("shared-policy", 1800, 2550),
    ("guarded-execution", 2550, 3450),
    ("promise", 3450, 4050),
)
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FRAME_RATE = 30
TOTAL_FRAMES = 4050
TITLE_SAFE = Rectangle(x=96, y=54, width=1728, height=972)


class ManifestError(ValueError):
    """Raised when a project manifest cannot safely drive a deterministic render."""


def load_project(path: Path, *, repository_root: Path | None = None) -> ProjectManifest:
    """Load a project manifest and reject every unsupported or unsafe production setting.

    Source paths are resolved only below ``repository_root``. Generated paths are resolved
    only below the selected ignored output root, so a malformed manifest cannot redirect a
    capture or render stage into unrelated repository content.
    """
    manifest_path = path.resolve()
    root = (
        repository_root.resolve()
        if repository_root is not None
        else _repository_root(manifest_path)
    )
    try:
        decoded: object = cast(object, json.loads(manifest_path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest: file not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest: invalid JSON: {exc.msg}") from exc

    payload = _object(decoded, "manifest")
    _exact_fields(payload, {"media", "safe_area", "output", "scenes"}, "manifest")
    media = _parse_media(_object(_required(payload, "media", "manifest"), "media"))
    safe_area = _parse_safe_area(_object(_required(payload, "safe_area", "manifest"), "safe_area"))
    output = _parse_output(_object(_required(payload, "output", "manifest"), "output"), root)
    scenes = _parse_scenes(_array(_required(payload, "scenes", "manifest"), "scenes"), root, media)
    evidence_dominant_frames = _validate_evidence_dominant_frame_share(scenes, media)
    return ProjectManifest(
        media=media,
        safe_area=safe_area,
        output=output,
        scenes=scenes,
        evidence_dominant_frames=evidence_dominant_frames,
    )


def _repository_root(manifest_path: Path) -> Path:
    for parent in manifest_path.parents:
        if (parent / ".git").exists():
            return parent
    raise ManifestError("manifest: repository_root is required outside a Git repository")


def _parse_media(payload: dict[str, object]) -> MediaSettings:
    _exact_fields(payload, {"width", "height", "fps", "total_frames"}, "media")
    width = _integer(_required(payload, "width", "media"), "media.width")
    height = _integer(_required(payload, "height", "media"), "media.height")
    fps = _integer(_required(payload, "fps", "media"), "media.fps")
    total_frames = _integer(_required(payload, "total_frames", "media"), "media.total_frames")
    if (width, height) != (FRAME_WIDTH, FRAME_HEIGHT):
        raise ManifestError("media: expected 1920x1080")
    if fps != FRAME_RATE:
        raise ManifestError("media.fps: expected 30")
    if total_frames != TOTAL_FRAMES:
        raise ManifestError("media.total_frames: expected 4050")
    return MediaSettings(width=width, height=height, fps=fps, total_frames=total_frames)


def _parse_safe_area(payload: dict[str, object]) -> SafeArea:
    _exact_fields(payload, {"x", "y", "width", "height", "text_sizes"}, "safe_area")
    rectangle = _rectangle_from_fields(payload, "safe_area")
    if rectangle != TITLE_SAFE:
        raise ManifestError("safe_area: expected the central 90% title-safe rectangle")
    text_payload = _object(_required(payload, "text_sizes", "safe_area"), "safe_area.text_sizes")
    _exact_fields(text_payload, {"caption", "code", "label"}, "safe_area.text_sizes")
    text_sizes = TextSizes(
        caption=_integer(
            _required(text_payload, "caption", "safe_area.text_sizes"),
            "safe_area.text_sizes.caption",
        ),
        code=_integer(
            _required(text_payload, "code", "safe_area.text_sizes"), "safe_area.text_sizes.code"
        ),
        label=_integer(
            _required(text_payload, "label", "safe_area.text_sizes"), "safe_area.text_sizes.label"
        ),
    )
    if text_sizes.caption < 44:
        raise ManifestError("safe_area.text_sizes.caption: must be at least 44")
    if text_sizes.code < 32:
        raise ManifestError("safe_area.text_sizes.code: must be at least 32")
    if text_sizes.label < 32:
        raise ManifestError("safe_area.text_sizes.label: must be at least 32")
    return SafeArea(rectangle=rectangle, text_sizes=text_sizes)


def _parse_output(payload: dict[str, object], repository_root: Path) -> OutputConfig:
    _exact_fields(
        payload,
        {
            "root",
            "narrated",
            "speaker",
            "render_manifest",
            "container",
            "video_codec",
            "audio_codec",
            "pixel_format",
            "deterministic",
        },
        "output",
    )
    root_value = _string(_required(payload, "root", "output"), "output.root")
    root = _resolve_relative_path(root_value, repository_root, "output.root")
    if not _is_ignored_output_root(root, repository_root):
        raise ManifestError("output.root: must be ignored by the repository")
    narrated = _resolve_output_path(
        _string(_required(payload, "narrated", "output"), "output.narrated"),
        root,
        "output.narrated",
    )
    speaker = _resolve_output_path(
        _string(_required(payload, "speaker", "output"), "output.speaker"), root, "output.speaker"
    )
    render_manifest = _resolve_output_path(
        _string(_required(payload, "render_manifest", "output"), "output.render_manifest"),
        root,
        "output.render_manifest",
    )
    container = _string(_required(payload, "container", "output"), "output.container")
    video_codec = _string(_required(payload, "video_codec", "output"), "output.video_codec")
    audio_codec = _string(_required(payload, "audio_codec", "output"), "output.audio_codec")
    pixel_format = _string(_required(payload, "pixel_format", "output"), "output.pixel_format")
    deterministic = _boolean(_required(payload, "deterministic", "output"), "output.deterministic")
    if container != "mp4":
        raise ManifestError("output.container: expected mp4")
    if video_codec != "h264":
        raise ManifestError("output.video_codec: expected h264")
    if audio_codec != "aac":
        raise ManifestError("output.audio_codec: expected aac")
    if pixel_format != "yuv420p":
        raise ManifestError("output.pixel_format: expected yuv420p")
    if not deterministic:
        raise ManifestError("output.deterministic: must be true")
    if narrated.suffix != ".mp4":
        raise ManifestError("output.narrated: must end in .mp4")
    if speaker.suffix != ".mp4":
        raise ManifestError("output.speaker: must end in .mp4")
    if render_manifest.suffix != ".json":
        raise ManifestError("output.render_manifest: must end in .json")
    if len({narrated, speaker, render_manifest}) != 3:
        raise ManifestError("output: generated paths must be distinct")
    return OutputConfig(
        root=root,
        narrated=narrated,
        speaker=speaker,
        render_manifest=render_manifest,
        container=container,
        video_codec=video_codec,
        audio_codec=audio_codec,
        pixel_format=pixel_format,
        deterministic=deterministic,
    )


def _parse_scenes(
    payload: list[object], repository_root: Path, media: MediaSettings
) -> tuple[Scene, ...]:
    if len(payload) != len(APPROVED_SCENES):
        raise ManifestError(f"scenes: expected {len(APPROVED_SCENES)} scenes")
    scenes = tuple(
        _parse_scene(_object(value, f"scenes[{index}]"), index, repository_root, media)
        for index, value in enumerate(payload)
    )
    for index, (scene, (scene_id, start_frame, end_frame)) in enumerate(
        zip(scenes, APPROVED_SCENES, strict=True)
    ):
        field = f"scenes[{index}]"
        if scene.id != scene_id:
            raise ManifestError(f"{field}.id: expected {scene_id!r}")
        if scene.start_frame != start_frame:
            raise ManifestError(f"{field}.start_frame: expected {start_frame}")
        if scene.end_frame != end_frame:
            raise ManifestError(f"{field}.end_frame: expected {end_frame}")
        _validate_visual_state_coverage(scene, field)
    return scenes


def _parse_scene(
    payload: dict[str, object], index: int, repository_root: Path, media: MediaSettings
) -> Scene:
    field = f"scenes[{index}]"
    _exact_fields(
        payload, {"id", "start_frame", "end_frame", "source_paths", "visual_states"}, field
    )
    source_values = _array(_required(payload, "source_paths", field), f"{field}.source_paths")
    if not source_values:
        raise ManifestError(f"{field}.source_paths: must not be empty")
    source_paths = tuple(
        _resolve_relative_path(
            _string(value, f"{field}.source_paths[{path_index}]"),
            repository_root,
            f"{field}.source_paths[{path_index}]",
        )
        for path_index, value in enumerate(source_values)
    )
    visual_values = _array(_required(payload, "visual_states", field), f"{field}.visual_states")
    if not visual_values:
        raise ManifestError(f"{field}.visual_states: must not be empty")
    return Scene(
        id=_string(_required(payload, "id", field), f"{field}.id"),
        start_frame=_integer(_required(payload, "start_frame", field), f"{field}.start_frame"),
        end_frame=_integer(_required(payload, "end_frame", field), f"{field}.end_frame"),
        source_paths=source_paths,
        visual_states=tuple(
            _parse_visual_state(
                _object(value, f"{field}.visual_states[{state_index}]"),
                f"{field}.visual_states[{state_index}]",
                media,
            )
            for state_index, value in enumerate(visual_values)
        ),
    )


def _parse_visual_state(
    payload: dict[str, object], field: str, media: MediaSettings
) -> VisualState:
    _exact_fields(payload, {"id", "start_frame", "end_frame", "evidence_rectangles"}, field)
    rectangle_values = _array(
        _required(payload, "evidence_rectangles", field), f"{field}.evidence_rectangles"
    )
    rectangles = tuple(
        _parse_evidence_rectangle(
            _object(value, f"{field}.evidence_rectangles[{index}]"),
            f"{field}.evidence_rectangles[{index}]",
            media,
        )
        for index, value in enumerate(rectangle_values)
    )
    _validate_non_overlapping_rectangles(rectangles, f"{field}.evidence_rectangles")
    return VisualState(
        id=_string(_required(payload, "id", field), f"{field}.id"),
        start_frame=_integer(_required(payload, "start_frame", field), f"{field}.start_frame"),
        end_frame=_integer(_required(payload, "end_frame", field), f"{field}.end_frame"),
        evidence_rectangles=rectangles,
    )


def _validate_visual_state_coverage(scene: Scene, field: str) -> None:
    cursor = scene.start_frame
    for index, state in enumerate(scene.visual_states):
        state_field = f"{field}.visual_states[{index}]"
        if state.start_frame != cursor:
            raise ManifestError(f"{state_field}.start_frame: expected {cursor}")
        if state.end_frame <= state.start_frame:
            raise ManifestError(f"{state_field}.end_frame: must be greater than start_frame")
        if state.end_frame > scene.end_frame:
            raise ManifestError(f"{state_field}.end_frame: exceeds scene end_frame")
        cursor = state.end_frame
    if cursor != scene.end_frame:
        raise ManifestError(
            f"{field}.visual_states: must cover the scene through frame {scene.end_frame}"
        )


def _parse_evidence_rectangle(
    payload: dict[str, object], field: str, media: MediaSettings
) -> Rectangle:
    rectangle = _parse_rectangle(payload, field)
    if rectangle.x + rectangle.width > media.width or rectangle.y + rectangle.height > media.height:
        raise ManifestError(f"{field}: must stay within the {media.width}x{media.height} frame")
    return rectangle


def _parse_rectangle(payload: dict[str, object], field: str) -> Rectangle:
    _exact_fields(payload, {"x", "y", "width", "height"}, field)
    return _rectangle_from_fields(payload, field)


def _rectangle_from_fields(payload: dict[str, object], field: str) -> Rectangle:
    rectangle = Rectangle(
        x=_integer(_required(payload, "x", field), f"{field}.x"),
        y=_integer(_required(payload, "y", field), f"{field}.y"),
        width=_integer(_required(payload, "width", field), f"{field}.width"),
        height=_integer(_required(payload, "height", field), f"{field}.height"),
    )
    if rectangle.x < 0 or rectangle.y < 0:
        raise ManifestError(f"{field}: x and y must be non-negative")
    if rectangle.width <= 0:
        raise ManifestError(f"{field}.width: must be positive")
    if rectangle.height <= 0:
        raise ManifestError(f"{field}.height: must be positive")
    return rectangle


def _validate_non_overlapping_rectangles(rectangles: tuple[Rectangle, ...], field: str) -> None:
    for index, rectangle in enumerate(rectangles):
        for other_index in range(index):
            if _rectangles_overlap(rectangle, rectangles[other_index]):
                raise ManifestError(f"{field}[{index}]: overlaps {field}[{other_index}]")


def _validate_evidence_dominant_frame_share(scenes: tuple[Scene, ...], media: MediaSettings) -> int:
    frame_area = media.width * media.height
    dominant_frames = sum(
        state.end_frame - state.start_frame
        for scene in scenes
        for state in scene.visual_states
        if _rectangle_union_area(state.evidence_rectangles) * 2 >= frame_area
    )
    if dominant_frames * 100 < media.total_frames * 60:
        raise ManifestError("scenes: evidence-dominant frames must occupy 60%-80% of the timeline")
    if dominant_frames * 100 > media.total_frames * 80:
        raise ManifestError("scenes: evidence-dominant frames must occupy 60%-80% of the timeline")
    return dominant_frames


def _rectangle_union_area(rectangles: tuple[Rectangle, ...]) -> int:
    """Return the exact union area instead of trusting manifest-authored evidence ratios."""
    x_edges = sorted(
        {edge for rectangle in rectangles for edge in (rectangle.x, rectangle.x + rectangle.width)}
    )
    area = 0
    for left, right in pairwise(x_edges):
        intervals = sorted(
            (rectangle.y, rectangle.y + rectangle.height)
            for rectangle in rectangles
            if rectangle.x < right and rectangle.x + rectangle.width > left
        )
        covered_until = 0
        for bottom, top in intervals:
            if top <= covered_until:
                continue
            area += (right - left) * (top - max(bottom, covered_until))
            covered_until = top
    return area


def _rectangles_overlap(left: Rectangle, right: Rectangle) -> bool:
    return (
        left.x < right.x + right.width
        and right.x < left.x + left.width
        and left.y < right.y + right.height
        and right.y < left.y + left.height
    )


def _resolve_relative_path(value: str, root: Path, field: str) -> Path:
    candidate = Path(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        raise ManifestError(f"{field}: must be a repository-relative path without traversal")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ManifestError(f"{field}: escapes the repository root")
    return resolved


def _resolve_output_path(value: str, output_root: Path, field: str) -> Path:
    candidate = Path(value)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {".", ".."} for part in candidate.parts)
    ):
        raise ManifestError(f"{field}: must be a relative path inside output.root")
    resolved = (output_root / candidate).resolve()
    if not resolved.is_relative_to(output_root):
        raise ManifestError(f"{field}: escapes output.root")
    return resolved


def _is_ignored_output_root(output_root: Path, repository_root: Path) -> bool:
    ignore_path = repository_root / ".gitignore"
    if not ignore_path.exists():
        return False
    relative = output_root.relative_to(repository_root).as_posix()
    for raw_pattern in ignore_path.read_text(encoding="utf-8").splitlines():
        pattern = raw_pattern.strip()
        if not pattern or pattern.startswith(("!", "#")):
            continue
        normalized = pattern.removeprefix("/")
        if normalized.endswith("/") and relative.startswith(normalized):
            return True
        if relative == normalized or relative.startswith(f"{normalized}/"):
            return True
    return False


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ManifestError(f"{field}: expected an object")
    typed_value = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in typed_value):
        raise ManifestError(f"{field}: expected an object with string keys")
    return cast(dict[str, object], typed_value)


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ManifestError(f"{field}: expected an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ManifestError(f"{field}: expected a string")
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ManifestError(f"{field}: expected an integer frame or pixel value")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestError(f"{field}: expected a boolean")
    return value


def _required(payload: dict[str, object], key: str, field: str) -> object:
    try:
        return payload[key]
    except KeyError as exc:
        raise ManifestError(f"{field}.{key}: is required") from exc


def _exact_fields(payload: dict[str, object], expected: Iterable[str], field: str) -> None:
    expected_set = set(expected)
    unknown = sorted(set(payload) - expected_set)
    if unknown:
        raise ManifestError(f"{field}: unknown field {unknown[0]!r}")
    missing = sorted(expected_set - set(payload))
    if missing:
        raise ManifestError(f"{field}.{missing[0]}: is required")
