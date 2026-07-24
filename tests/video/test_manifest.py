"""Behavior contracts for the strict repository explainer project manifest."""

from __future__ import annotations

import copy
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import pytest

from video_pipeline.manifest import ManifestError, load_project
from video_pipeline.models import ProjectManifest


def _load_manifest(path: Path, repository_root: Path) -> ProjectManifest:
    return load_project(path, repository_root=repository_root)


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _scene(payload: dict[str, object], index: int) -> dict[str, object]:
    return _mapping(cast(list[object], payload["scenes"])[index])


def _state(payload: dict[str, object], scene_index: int) -> dict[str, object]:
    return _mapping(cast(list[object], _scene(payload, scene_index)["visual_states"])[0])


def test_loads_approved_4050_frame_six_scene_manifest(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    manifest = _load_manifest(
        write_manifest(repository_root, approved_manifest_data), repository_root
    )

    assert [scene.id for scene in manifest.scenes] == [
        "problem",
        "visible-workflow",
        "caught-defect",
        "shared-policy",
        "guarded-execution",
        "promise",
    ]
    assert [(scene.start_frame, scene.end_frame) for scene in manifest.scenes] == [
        (0, 450),
        (450, 1050),
        (1050, 1800),
        (1800, 2550),
        (2550, 3450),
        (3450, 4050),
    ]
    assert (manifest.media.width, manifest.media.height, manifest.media.fps) == (1920, 1080, 30)
    assert manifest.media.total_frames == 4050


def test_module_help_describes_the_local_pipeline() -> None:
    production_root = Path(__file__).parents[2] / "media" / "repository-explainer"
    completed = subprocess.run(
        [sys.executable, "-m", "video_pipeline", "--help"],
        cwd=production_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0
    assert "Repository explainer video pipeline" in completed.stdout


Mutation = Callable[[dict[str, object]], None]


def _add_unknown_key(payload: dict[str, object]) -> None:
    payload["unexpected"] = "not allowed"


def _escape_source_path(payload: dict[str, object]) -> None:
    _scene(payload, 0)["source_paths"] = ["../secret.txt"]


def _remove_scene_id(payload: dict[str, object]) -> None:
    del _scene(payload, 0)["id"]


def _overlap_scenes(payload: dict[str, object]) -> None:
    _scene(payload, 1)["start_frame"] = 449


def _gap_between_scenes(payload: dict[str, object]) -> None:
    _scene(payload, 1)["start_frame"] = 451


def _wrong_total(payload: dict[str, object]) -> None:
    _mapping(payload["media"])["total_frames"] = 4049


def _unsafe_caption_text(payload: dict[str, object]) -> None:
    _mapping(_mapping(payload["safe_area"])["text_sizes"])["caption"] = 43


def _unsafe_title_safe_area(payload: dict[str, object]) -> None:
    _mapping(payload["safe_area"])["x"] = 95


def _nondeterministic_output(payload: dict[str, object]) -> None:
    _mapping(payload["output"])["deterministic"] = False


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        pytest.param(_add_unknown_key, "manifest", id="unknown-key"),
        pytest.param(_escape_source_path, "scenes[0].source_paths[0]", id="source-path-escape"),
        pytest.param(_remove_scene_id, "scenes[0].id", id="missing-scene-id"),
        pytest.param(_overlap_scenes, "scenes[1].start_frame", id="scene-overlap"),
        pytest.param(_gap_between_scenes, "scenes[1].start_frame", id="scene-gap"),
        pytest.param(_wrong_total, "media.total_frames", id="wrong-total"),
        pytest.param(_unsafe_caption_text, "safe_area.text_sizes.caption", id="unsafe-caption"),
        pytest.param(_unsafe_title_safe_area, "safe_area", id="unsafe-area"),
        pytest.param(
            _nondeterministic_output, "output.deterministic", id="nondeterministic-output"
        ),
    ],
)
def test_rejects_invalid_manifest_invariants(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    mutate: Mutation,
    field: str,
) -> None:
    payload = copy.deepcopy(approved_manifest_data)
    mutate(payload)

    with pytest.raises(ManifestError, match=re.escape(field)):
        _load_manifest(write_manifest(repository_root, payload), repository_root)


def test_rejects_paths_outside_owned_roots(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    source_escape = copy.deepcopy(approved_manifest_data)
    _scene(source_escape, 0)["source_paths"] = ["../outside.apseudo"]
    with pytest.raises(ManifestError, match="scenes\\[0\\]\\.source_paths\\[0\\]"):
        _load_manifest(write_manifest(repository_root, source_escape), repository_root)

    absolute_output = copy.deepcopy(approved_manifest_data)
    _mapping(absolute_output["output"])["narrated"] = "/tmp/narrated.mp4"
    with pytest.raises(ManifestError, match=re.escape("output.narrated")):
        _load_manifest(write_manifest(repository_root, absolute_output), repository_root)


def _state_interval_gap(payload: dict[str, object]) -> None:
    _state(payload, 1)["start_frame"] = 451


def _state_interval_overflow(payload: dict[str, object]) -> None:
    _state(payload, 1)["end_frame"] = 1051


def _rectangle_out_of_bounds(payload: dict[str, object]) -> None:
    rectangles = cast(list[dict[str, object]], _state(payload, 1)["evidence_rectangles"])
    rectangles[0]["x"] = 1801


def _rectangle_has_no_area(payload: dict[str, object]) -> None:
    rectangles = cast(list[dict[str, object]], _state(payload, 1)["evidence_rectangles"])
    rectangles[0]["width"] = 0


def _rectangles_overlap(payload: dict[str, object]) -> None:
    _state(payload, 1)["evidence_rectangles"] = [
        {"x": 100, "y": 100, "width": 800, "height": 600},
        {"x": 800, "y": 100, "width": 800, "height": 600},
    ]


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        pytest.param(_state_interval_gap, "visual_states[0].start_frame", id="state-gap"),
        pytest.param(_state_interval_overflow, "visual_states[0].end_frame", id="state-overflow"),
        pytest.param(
            _rectangle_out_of_bounds, "evidence_rectangles[0]", id="rectangle-out-of-bounds"
        ),
        pytest.param(
            _rectangle_has_no_area, "evidence_rectangles[0].width", id="rectangle-zero-width"
        ),
        pytest.param(_rectangles_overlap, "evidence_rectangles[1]", id="rectangles-overlap"),
    ],
)
def test_validates_visual_state_classification_inputs(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    mutate: Mutation,
    field: str,
) -> None:
    payload = copy.deepcopy(approved_manifest_data)
    mutate(payload)

    with pytest.raises(ManifestError, match=re.escape(field)):
        _load_manifest(write_manifest(repository_root, payload), repository_root)
