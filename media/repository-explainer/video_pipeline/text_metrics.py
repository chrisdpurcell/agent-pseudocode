"""Measure rendered text with the pipeline's declared FFmpeg/fontconfig tools."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type TextAnchor = Literal["start", "middle", "end"]

_REQUIRED_FFMPEG_FILTERS = frozenset({"bbox", "drawtext"})
_BBOX = re.compile(
    r"x1:(?P<x1>\d+) x2:(?P<x2>\d+) "
    r"y1:(?P<y1>\d+) y2:(?P<y2>\d+) "
    r"w:(?P<width>\d+) h:(?P<height>\d+)"
)


class TextMetricError(ValueError):
    """Reject unavailable tools, unresolved fonts, or unusable metric output."""


@dataclass(frozen=True, slots=True)
class TextMetricCapabilities:
    """Resolved tools that satisfy the text-measurement capability contract."""

    ffmpeg: Path
    fontconfig: Path


@dataclass(frozen=True, slots=True)
class TextBounds:
    """Exclusive pixel bounds of one text run on the 1920x1080 canvas."""

    left: int
    top: int
    right: int
    bottom: int


def probe_text_metric_capabilities(
    *,
    ffmpeg: str = "ffmpeg",
    fontconfig: str = "fc-match",
) -> TextMetricCapabilities:
    """Resolve declared executables and require FFmpeg's text/bounds filters."""
    ffmpeg_path = _resolve_executable(ffmpeg, "ffmpeg")
    fontconfig_path = _resolve_executable(fontconfig, "fc-match")
    try:
        completed = subprocess.run(
            [str(ffmpeg_path), "-hide_banner", "-filters"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TextMetricError("ffmpeg capability probe could not complete") from exc
    if completed.returncode != 0:
        raise TextMetricError("ffmpeg capability probe failed")
    listing = f"{completed.stdout}\n{completed.stderr}"
    missing = sorted(
        name
        for name in _REQUIRED_FFMPEG_FILTERS
        if re.search(rf"^\s*\S+\s+{re.escape(name)}\s", listing, re.MULTILINE) is None
    )
    if missing:
        raise TextMetricError(f"ffmpeg is missing required text filters: {', '.join(missing)}")
    return TextMetricCapabilities(ffmpeg=ffmpeg_path, fontconfig=fontconfig_path)


def resolve_regular_font(
    family: str,
    *,
    capabilities: TextMetricCapabilities,
) -> Path:
    """Resolve the exact regular face selected by fontconfig."""
    if not family or family != family.strip():
        raise TextMetricError("font family must be a nonempty trimmed string")
    try:
        completed = subprocess.run(
            [
                str(capabilities.fontconfig),
                "-f",
                "%{file}",
                f"{family}:style=Regular",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TextMetricError("fc-match font resolution could not complete") from exc
    if completed.returncode != 0:
        raise TextMetricError("fc-match font resolution failed")
    resolved = Path(completed.stdout)
    if not resolved.is_absolute() or not resolved.is_file():
        raise TextMetricError("fc-match did not resolve an absolute font file")
    return resolved


def measure_text_bounds(
    text: str,
    *,
    font_path: Path,
    font_size: int,
    x: int,
    baseline: int,
    anchor: TextAnchor | str,
    capabilities: TextMetricCapabilities,
) -> TextBounds:
    """Render one SVG-equivalent text run and return its actual ink bounds."""
    if not text or not text.strip() or "\n" in text or "\r" in text:
        raise TextMetricError("text must be one nonblank line")
    if font_size <= 0:
        raise TextMetricError("font_size must be positive")
    if anchor not in {"start", "middle", "end"}:
        raise TextMetricError("anchor must be start, middle, or end")
    font = font_path.resolve()
    if not font.is_file():
        raise TextMetricError("font_path must resolve to a file")
    _require_filter_safe_path(font, "font_path")

    x_expression = {
        "start": str(x),
        "middle": f"{x}-text_w/2",
        "end": f"{x}-text_w",
    }[anchor]
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="apseudo-text-",
            suffix=".txt",
            delete=False,
        ) as handle:
            handle.write(text)
            temporary_path = Path(handle.name)
        _require_filter_safe_path(temporary_path, "textfile")
        filter_graph = (
            f"drawtext=fontfile={font.as_posix()}:"
            f"textfile={temporary_path.as_posix()}:"
            f"fontcolor=white:fontsize={font_size}:"
            f"x={x_expression}:y={baseline}-ascent,"
            "bbox=min_val=24"
        )
        completed = subprocess.run(
            [
                str(capabilities.ffmpeg),
                "-hide_banner",
                "-loglevel",
                "verbose",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=1920x1080:d=0.1:r=30",
                "-vf",
                filter_graph,
                "-frames:v",
                "1",
                "-f",
                "null",
                "-",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TextMetricError("ffmpeg text measurement could not complete") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    if completed.returncode != 0:
        raise TextMetricError("ffmpeg text measurement failed")
    matches = tuple(_BBOX.finditer(f"{completed.stdout}\n{completed.stderr}"))
    if not matches:
        raise TextMetricError("ffmpeg text measurement produced no bounding box")
    values = {name: int(value) for name, value in matches[0].groupdict().items()}
    if values["width"] <= 0 or values["height"] <= 0:
        raise TextMetricError("ffmpeg text measurement produced empty bounds")
    return TextBounds(
        left=values["x1"],
        top=values["y1"],
        right=values["x2"] + 1,
        bottom=values["y2"] + 1,
    )


def _resolve_executable(name: str, label: str) -> Path:
    resolved = shutil.which(name)
    if resolved is None:
        raise TextMetricError(f"{label} executable was not found")
    return Path(resolved).resolve()


def _require_filter_safe_path(path: Path, field: str) -> None:
    if any(character in path.as_posix() for character in "\\':,;[]"):
        raise TextMetricError(f"{field} contains an unsupported FFmpeg filter character")
