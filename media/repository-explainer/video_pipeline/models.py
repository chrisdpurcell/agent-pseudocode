"""Immutable records consumed by the repository explainer production stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Rectangle:
    """A pixel rectangle whose right and bottom edges are exclusive."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class MediaSettings:
    """The fixed picture format shared by both delivery variants."""

    width: int
    height: int
    fps: int
    total_frames: int


@dataclass(frozen=True, slots=True)
class TextSizes:
    """Minimum pixel sizes for text that carries essential film meaning."""

    caption: int
    code: int
    label: int


@dataclass(frozen=True, slots=True)
class SafeArea:
    """The central title-safe rectangle and its minimum essential text sizes."""

    rectangle: Rectangle
    text_sizes: TextSizes


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Deterministic local delivery paths and the approved media encodings."""

    root: Path
    narrated: Path
    speaker: Path
    render_manifest: Path
    container: str
    video_codec: str
    audio_codec: str
    pixel_format: str
    deterministic: bool


@dataclass(frozen=True, slots=True)
class VisualState:
    """One frame interval and its renderer-consumed evidence rectangles."""

    id: str
    start_frame: int
    end_frame: int
    evidence_rectangles: tuple[Rectangle, ...]


@dataclass(frozen=True, slots=True)
class Scene:
    """One approved narrative segment with source ownership and visual timing."""

    id: str
    start_frame: int
    end_frame: int
    source_paths: tuple[Path, ...]
    visual_states: tuple[VisualState, ...]


@dataclass(frozen=True, slots=True)
class ProjectManifest:
    """The complete immutable production contract for one repository explainer film."""

    media: MediaSettings
    safe_area: SafeArea
    output: OutputConfig
    scenes: tuple[Scene, ...]
    evidence_dominant_frames: int
