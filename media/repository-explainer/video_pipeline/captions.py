"""Validate the locked narration source and render its reusable SRT captions.

The JSON source carries narration, caption, and mute-safe copy together so a
caption edit cannot silently diverge from the approved spoken script. Picture
scene boundaries are owned by the project manifest; measured audio may fit
inside a segment but may never move those boundaries.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .models import ProjectManifest

FRAME_MARGIN = 15
MAX_CAPTION_LINES = 2
MAX_CAPTION_LINE_LENGTH = 42
MIN_CAPTION_DWELL_FRAMES = 45
READING_CHARACTERS_PER_SECOND = 15
AI_NARRATION_DISCLOSURE = "AI-generated narration."


class CaptionError(ValueError):
    """Raised when narration cannot safely fit the approved visual timeline."""


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    """One locked narration interval and its mute-safe visual counterpart."""

    scene_id: str
    start_frame: int
    end_frame: int
    narration: str
    caption: str
    mute_safe_copy: str


@dataclass(frozen=True, slots=True)
class NarrationPackage:
    """The approved TTS directions and the ordered scene narration source."""

    model: str
    voice: str
    instructions: str
    disclosure: str
    segments: tuple[NarrationSegment, ...]


def load_narration(path: Path, project: ProjectManifest) -> NarrationPackage:
    """Load narration JSON and enforce its scene, accessibility, and disclosure contracts."""
    payload = _load_json(path)
    _exact_fields(payload, {"delivery", "segments"}, "narration")
    delivery = _object(_required(payload, "delivery", "narration"), "narration.delivery")
    _exact_fields(delivery, {"model", "voice", "instructions", "disclosure"}, "narration.delivery")
    segments = tuple(
        _parse_segment(value, index)
        for index, value in enumerate(
            _array(_required(payload, "segments", "narration"), "segments")
        )
    )
    package = NarrationPackage(
        model=_nonempty_string(
            _required(delivery, "model", "narration.delivery"), "delivery.model"
        ),
        voice=_nonempty_string(
            _required(delivery, "voice", "narration.delivery"), "delivery.voice"
        ),
        instructions=_nonempty_string(
            _required(delivery, "instructions", "narration.delivery"), "delivery.instructions"
        ),
        disclosure=_nonempty_string(
            _required(delivery, "disclosure", "narration.delivery"), "delivery.disclosure"
        ),
        segments=segments,
    )
    _validate_package(package, project)
    return package


def compile_captions(path: Path, project: ProjectManifest) -> bytes:
    """Compile one validated narration source into stable UTF-8 SRT bytes."""
    package = load_narration(path, project)
    entries = tuple(
        "\n".join(
            (
                str(index),
                f"{_timestamp(segment.start_frame, project.media.fps)} --> "
                f"{_timestamp(segment.end_frame, project.media.fps)}",
                *_wrap_caption(segment.caption),
            )
        )
        for index, segment in enumerate(package.segments, start=1)
    )
    return ("\n\n".join(entries) + "\n").encode("utf-8")


def validate_take_durations(
    path: Path, project: ProjectManifest, measured_frames: Mapping[str, int]
) -> None:
    """Reject measured TTS segment durations that cannot fit their locked slots.

    The speech stage calls this after local WAV measurement. A rejected take
    must be shortened and regenerated; expanding a scene would desynchronize
    the shared picture timeline and the speaker cut.
    """
    package = load_narration(path, project)
    expected_ids = {segment.scene_id for segment in package.segments}
    for scene_id, duration in measured_frames.items():
        if scene_id not in expected_ids:
            raise CaptionError(f"measured_frames.{scene_id}: has no narration segment")
        if type(duration) is not int or duration <= 0:
            raise CaptionError(f"measured_frames.{scene_id}: must be a positive integer")
        segment = next(segment for segment in package.segments if segment.scene_id == scene_id)
        budget = segment.end_frame - segment.start_frame
        if duration > budget:
            raise CaptionError(
                f"measured_frames.{scene_id}: exceeds its fixed {budget}-frame budget; "
                "shorten the line and regenerate without moving picture boundaries"
            )
    if set(measured_frames) != expected_ids:
        raise CaptionError("measured_frames: must include every narration segment")


def _load_json(path: Path) -> dict[str, object]:
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise CaptionError("narration: source file not found") from exc
    except UnicodeDecodeError as exc:
        raise CaptionError("narration: source is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise CaptionError(f"narration: invalid JSON: {exc.msg}") from exc
    return _object(decoded, "narration")


def _parse_segment(value: object, index: int) -> NarrationSegment:
    field = f"segments[{index}]"
    payload = _object(value, field)
    _exact_fields(
        payload,
        {"scene_id", "start_frame", "end_frame", "narration", "caption", "mute_safe_copy"},
        field,
    )
    return NarrationSegment(
        scene_id=_nonempty_string(_required(payload, "scene_id", field), f"{field}.scene_id"),
        start_frame=_integer(_required(payload, "start_frame", field), f"{field}.start_frame"),
        end_frame=_integer(_required(payload, "end_frame", field), f"{field}.end_frame"),
        narration=_nonempty_string(_required(payload, "narration", field), f"{field}.narration"),
        caption=_nonempty_string(_required(payload, "caption", field), f"{field}.caption"),
        mute_safe_copy=_nonempty_string(
            _required(payload, "mute_safe_copy", field), f"{field}.mute_safe_copy"
        ),
    )


def _validate_package(package: NarrationPackage, project: ProjectManifest) -> None:
    if package.model != "gpt-4o-mini-tts":
        raise CaptionError("delivery.model: expected gpt-4o-mini-tts")
    if package.voice != "marin":
        raise CaptionError("delivery.voice: expected marin")
    if package.disclosure != AI_NARRATION_DISCLOSURE:
        raise CaptionError("delivery.disclosure: expected explicit AI narration disclosure")
    if len(package.segments) != len(project.scenes):
        raise CaptionError(f"segments: expected {len(project.scenes)} ordered scene messages")

    _validate_temporal_order(package.segments)
    for index, (segment, scene) in enumerate(zip(package.segments, project.scenes, strict=True)):
        field = f"segments[{index}]"
        if segment.scene_id != scene.id:
            raise CaptionError(f"{field}.scene_id: expected {scene.id!r}")
        if segment.start_frame < scene.start_frame + FRAME_MARGIN:
            raise CaptionError(
                f"{field}.start_frame: must leave a {FRAME_MARGIN}-frame scene margin"
            )
        if segment.end_frame > scene.end_frame - FRAME_MARGIN:
            raise CaptionError(f"{field}.end_frame: must leave a {FRAME_MARGIN}-frame scene margin")
        _validate_caption_readability(segment, project.media.fps, field)

    if AI_NARRATION_DISCLOSURE not in package.segments[-1].caption:
        raise CaptionError("segments[-1].caption: must include the AI narration disclosure")
    if AI_NARRATION_DISCLOSURE not in package.segments[-1].mute_safe_copy:
        raise CaptionError("segments[-1].mute_safe_copy: must include the AI narration disclosure")


def _validate_temporal_order(segments: tuple[NarrationSegment, ...]) -> None:
    """Reject structural timing defects before checking scene-specific margins."""
    previous_end: int | None = None
    for index, segment in enumerate(segments):
        field = f"segments[{index}]"
        if segment.end_frame <= segment.start_frame:
            raise CaptionError(f"{field}: end_frame must be greater than start_frame")
        if previous_end is not None and segment.start_frame < previous_end:
            raise CaptionError(f"{field}.start_frame: overlaps the preceding segment")
        previous_end = segment.end_frame


def _validate_caption_readability(segment: NarrationSegment, fps: int, field: str) -> None:
    lines = _wrap_caption(segment.caption)
    if len(lines) > MAX_CAPTION_LINES:
        raise CaptionError(f"{field}.caption: exceeds {MAX_CAPTION_LINES} readable lines")
    visible_characters = len("".join(lines))
    required_dwell_frames = max(
        MIN_CAPTION_DWELL_FRAMES,
        _ceiling_division(visible_characters * fps, READING_CHARACTERS_PER_SECOND),
    )
    if segment.end_frame - segment.start_frame < required_dwell_frames:
        raise CaptionError(
            f"{field}.caption: requires at least {required_dwell_frames} frames of readable dwell time"
        )


def _wrap_caption(caption: str) -> tuple[str, ...]:
    words = caption.split()
    if not words:
        raise CaptionError("caption: must contain readable text")
    lines: list[str] = []
    line = ""
    for word in words:
        if len(word) > MAX_CAPTION_LINE_LENGTH:
            raise CaptionError(
                f"caption: word {word!r} exceeds the {MAX_CAPTION_LINE_LENGTH}-character line limit"
            )
        candidate = word if not line else f"{line} {word}"
        if len(candidate) <= MAX_CAPTION_LINE_LENGTH:
            line = candidate
            continue
        lines.append(line)
        line = word
    lines.append(line)
    if len(lines) > MAX_CAPTION_LINES:
        raise CaptionError(f"caption: exceeds {MAX_CAPTION_LINES} readable lines")
    return tuple(lines)


def _timestamp(frame: int, fps: int) -> str:
    milliseconds = frame * 1000 // fps
    hours, remaining = divmod(milliseconds, 3_600_000)
    minutes, remaining = divmod(remaining, 60_000)
    seconds, milliseconds = divmod(remaining, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def _ceiling_division(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CaptionError(f"{field}: must be an object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise CaptionError(f"{field}: must be an array")
    return cast(list[object], value)


def _required(payload: dict[str, object], key: str, field: str) -> object:
    try:
        return payload[key]
    except KeyError as exc:
        raise CaptionError(f"{field}: missing required field {key!r}") from exc


def _exact_fields(payload: dict[str, object], expected: set[str], field: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise CaptionError(f"{field}: expected exactly {sorted(expected)!r}")


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaptionError(f"{field}: must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise CaptionError(f"{field}: must be an integer")
    return value
