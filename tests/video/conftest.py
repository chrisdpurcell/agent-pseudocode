"""Shared fixtures for the repository explainer video production tests."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    """Return a repository-shaped root whose selected output path is ignored."""
    (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def approved_manifest_data() -> dict[str, object]:
    """Return the approved six-scene manifest as mutable JSON-compatible data."""
    return {
        "media": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "total_frames": 4050,
        },
        "safe_area": {
            "x": 96,
            "y": 54,
            "width": 1728,
            "height": 972,
            "text_sizes": {"caption": 44, "code": 32, "label": 32},
        },
        "output": {
            "root": "dist/video",
            "narrated": "final/agent-pseudocode-explainer-narrated.mp4",
            "speaker": "final/agent-pseudocode-explainer-speaker.mp4",
            "render_manifest": "candidate/render-manifest.json",
            "container": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "deterministic": True,
        },
        "scenes": [
            {
                "id": "problem",
                "start_frame": 0,
                "end_frame": 450,
                "source_paths": ["docs/specs/repository-explainer-video.md"],
                "visual_states": [
                    {
                        "id": "question",
                        "start_frame": 0,
                        "end_frame": 450,
                        "evidence_rectangles": [],
                    }
                ],
            },
            {
                "id": "visible-workflow",
                "start_frame": 450,
                "end_frame": 1050,
                "source_paths": ["docs/apseudo-docs/examples/review-loop.apseudo"],
                "visual_states": [
                    {
                        "id": "workflow",
                        "start_frame": 450,
                        "end_frame": 1050,
                        "evidence_rectangles": [{"x": 120, "y": 90, "width": 1680, "height": 840}],
                    }
                ],
            },
            {
                "id": "caught-defect",
                "start_frame": 1050,
                "end_frame": 1800,
                "source_paths": ["tests/fixtures/invalid/unbounded_while.apseudo"],
                "visual_states": [
                    {
                        "id": "diagnostic",
                        "start_frame": 1050,
                        "end_frame": 1800,
                        "evidence_rectangles": [{"x": 120, "y": 90, "width": 1680, "height": 840}],
                    }
                ],
            },
            {
                "id": "shared-policy",
                "start_frame": 1800,
                "end_frame": 2550,
                "source_paths": ["src/apseudo_lint/rules.py"],
                "visual_states": [
                    {
                        "id": "system-map",
                        "start_frame": 1800,
                        "end_frame": 2550,
                        "evidence_rectangles": [{"x": 120, "y": 90, "width": 1680, "height": 840}],
                    }
                ],
            },
            {
                "id": "guarded-execution",
                "start_frame": 2550,
                "end_frame": 3450,
                "source_paths": ["docs/apseudo-docs/examples/review-loop.apseudo"],
                "visual_states": [
                    {
                        "id": "runner",
                        "start_frame": 2550,
                        "end_frame": 3450,
                        "evidence_rectangles": [{"x": 120, "y": 90, "width": 1680, "height": 840}],
                    }
                ],
            },
            {
                "id": "promise",
                "start_frame": 3450,
                "end_frame": 4050,
                "source_paths": ["README.md"],
                "visual_states": [
                    {
                        "id": "end-card",
                        "start_frame": 3450,
                        "end_frame": 4050,
                        "evidence_rectangles": [],
                    }
                ],
            },
        ],
    }


@pytest.fixture
def write_manifest() -> Callable[[Path, Mapping[str, object]], Path]:
    """Write a JSON manifest below a supplied repository root."""

    def write(root: Path, payload: Mapping[str, object]) -> Path:
        manifest_path = root / "media" / "repository-explainer" / "project.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        return manifest_path

    return write
