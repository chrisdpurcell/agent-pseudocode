"""Contracts for the deterministic narration-to-SRT compilation stage."""

from __future__ import annotations

import copy
import importlib
import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from video_pipeline.manifest import load_project
from video_pipeline.models import ProjectManifest

REPOSITORY_ROOT = Path(__file__).parents[2]
NARRATION_PATH = REPOSITORY_ROOT / "media" / "repository-explainer" / "narration.json"
CAPTIONS_PATH = REPOSITORY_ROOT / "media" / "repository-explainer" / "captions.srt"
PROJECT_PATH = REPOSITORY_ROOT / "media" / "repository-explainer" / "project.json"

CompileCaptions = Callable[[Path, ProjectManifest], bytes]
ValidateTakeDurations = Callable[[Path, ProjectManifest, Mapping[str, int]], None]


def _caption_module() -> ModuleType:
    """Return the compiler module, reporting an intentional RED failure if it is absent."""
    if importlib.util.find_spec("video_pipeline.captions") is None:
        pytest.fail("caption compiler is missing")
    return importlib.import_module("video_pipeline.captions")


def _compiler_entrypoint(name: str) -> object:
    """Look up a public compiler entry point after the intentional RED guard."""
    return getattr(_caption_module(), name)


def _compile_captions() -> CompileCaptions:
    return cast(CompileCaptions, _compiler_entrypoint("compile_captions"))


def _validate_take_durations() -> ValidateTakeDurations:
    return cast(ValidateTakeDurations, _compiler_entrypoint("validate_take_durations"))


def _project() -> ProjectManifest:
    return load_project(PROJECT_PATH, repository_root=REPOSITORY_ROOT)


def _read_narration() -> dict[str, object]:
    return cast(dict[str, object], json.loads(NARRATION_PATH.read_text(encoding="utf-8")))


def _segments(payload: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], payload["segments"])


def _write_narration(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _frame(value: object) -> int:
    """Return a JSON frame value after confirming the source stayed integer-timed."""
    assert type(value) is int
    return value


def test_compiles_mute_safe_captions() -> None:
    """Compile the approved six-scene source into its checked-in reusable SRT."""
    compiled = _compile_captions()(NARRATION_PATH, _project())
    source = _read_narration()

    assert compiled == CAPTIONS_PATH.read_bytes()
    assert compiled.count(b" --> ") == 6
    assert [segment["scene_id"] for segment in _segments(source)] == [
        "problem",
        "visible-workflow",
        "caught-defect",
        "shared-policy",
        "guarded-execution",
        "promise",
    ]
    assert all(segment["mute_safe_copy"] for segment in _segments(source))
    assert b"AI-generated narration." in compiled


@pytest.mark.parametrize(
    "case",
    [
        pytest.param("outside-margin", id="outside-scene-margin"),
        pytest.param("overlap", id="overlap"),
        pytest.param("invalid-timing", id="invalid-timing"),
        pytest.param("unreadable", id="unreadable-caption"),
        pytest.param("missing-disclosure", id="missing-disclosure"),
    ],
)
def test_rejects_outside_scene_margins_or_missing_disclosure(case: str, tmp_path: Path) -> None:
    """Reject invalid timing, unreadable copy, and any absent AI disclosure."""
    payload = copy.deepcopy(_read_narration())
    segments = _segments(payload)
    expected_message = ""
    if case == "outside-margin":
        segments[0]["start_frame"] = 14
        expected_message = "scene margin"
    elif case == "overlap":
        segments[0]["end_frame"] = _frame(segments[1]["start_frame"]) + 1
        expected_message = "overlaps"
    elif case == "invalid-timing":
        segments[2]["end_frame"] = segments[2]["start_frame"]
        expected_message = "greater than"
    elif case == "unreadable":
        segments[3]["caption"] = " ".join(["readable"] * 30)
        expected_message = "readable lines"
    else:
        delivery = cast(dict[str, object], payload["delivery"])
        delivery["disclosure"] = ""
        expected_message = "non-empty string"

    with pytest.raises(ValueError, match=expected_message):
        _compile_captions()(_write_narration(tmp_path / "narration.json", payload), _project())


def test_rejects_overlong_take_for_line_shortening() -> None:
    """Keep picture timing fixed when a measured narration take exceeds its slot."""
    source = _read_narration()
    first = _segments(source)[0]
    measured_frames = _frame(first["end_frame"]) - _frame(first["start_frame"]) + 1

    with pytest.raises(ValueError, match="shorten"):
        _validate_take_durations()(NARRATION_PATH, _project(), {"problem": measured_frames})


def test_srt_compilation_is_deterministic() -> None:
    """Emit byte-identical captions for identical narration and manifest inputs."""
    compiler = _compile_captions()

    assert compiler(NARRATION_PATH, _project()) == compiler(NARRATION_PATH, _project())
