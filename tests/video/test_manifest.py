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
from video_pipeline.models import ProjectManifest, Rectangle

COMMITTED_MANIFEST_PATH = (
    Path(__file__).parents[2] / "media" / "repository-explainer" / "project.json"
)


def _load_manifest(path: Path, repository_root: Path) -> ProjectManifest:
    return load_project(path, repository_root=repository_root)


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _scene(payload: dict[str, object], index: int) -> dict[str, object]:
    return _mapping(cast(list[object], payload["scenes"])[index])


def _state(payload: dict[str, object], scene_index: int) -> dict[str, object]:
    return _mapping(cast(list[object], _scene(payload, scene_index)["visual_states"])[0])


def test_loads_approved_4050_frame_six_scene_manifest() -> None:
    manifest = load_project(COMMITTED_MANIFEST_PATH)

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
    assert manifest.evidence_dominant_frames == 3000
    assert 0.6 <= manifest.evidence_dominant_frames / manifest.media.total_frames <= 0.8
    assert manifest.scenes[1].visual_states[0].evidence_rectangles == (
        Rectangle(x=96, y=54, width=1728, height=786),
    )


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


@pytest.mark.parametrize(
    ("text", "key"),
    [
        pytest.param('{"media": {}, "media": {}}', "media", id="top-level"),
        pytest.param(None, "width", id="nested"),
    ],
)
def test_rejects_duplicate_json_keys(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    text: str | None,
    key: str,
) -> None:
    manifest_path = write_manifest(repository_root, approved_manifest_data)
    if text is None:
        text = COMMITTED_MANIFEST_PATH.read_text(encoding="utf-8").replace(
            '"width": 1920', '"width": 1920, "width": 1920', 1
        )
    manifest_path.write_text(text, encoding="utf-8")

    with pytest.raises(ManifestError, match=re.escape(f"duplicate JSON key {key!r}")):
        _load_manifest(manifest_path, repository_root)


def test_rejects_manifest_with_invalid_utf8(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    manifest_path = write_manifest(repository_root, approved_manifest_data)
    manifest_path.write_bytes(b'\xff{"media": {}}')

    with pytest.raises(ManifestError, match=re.escape("manifest: invalid UTF-8")):
        _load_manifest(manifest_path, repository_root)


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


def _full_frame_rectangle() -> dict[str, int]:
    return {"x": 0, "y": 0, "width": 1920, "height": 1080}


def _replace_visual_states(
    payload: dict[str, object], scene_index: int, states: list[dict[str, object]]
) -> None:
    _scene(payload, scene_index)["visual_states"] = states


def _below_evidence_share(payload: dict[str, object]) -> None:
    _state(payload, 1)["evidence_rectangles"] = []


def _exactly_sixty_percent_evidence_share(payload: dict[str, object]) -> None:
    _replace_visual_states(
        payload,
        1,
        [
            {
                "id": "brief-evidence",
                "start_frame": 450,
                "end_frame": 480,
                "evidence_rectangles": [_full_frame_rectangle()],
            },
            {
                "id": "workflow-copy",
                "start_frame": 480,
                "end_frame": 1050,
                "evidence_rectangles": [],
            },
        ],
    )


def _exactly_eighty_percent_evidence_share(payload: dict[str, object]) -> None:
    _replace_visual_states(
        payload,
        0,
        [
            {
                "id": "opening-evidence",
                "start_frame": 0,
                "end_frame": 240,
                "evidence_rectangles": [_full_frame_rectangle()],
            },
            {
                "id": "question-copy",
                "start_frame": 240,
                "end_frame": 450,
                "evidence_rectangles": [],
            },
        ],
    )


def _above_evidence_share(payload: dict[str, object]) -> None:
    _state(payload, 0)["evidence_rectangles"] = [_full_frame_rectangle()]


@pytest.mark.parametrize(
    ("mutate", "expected_frames", "should_raise"),
    [
        pytest.param(_below_evidence_share, 2400, True, id="below-sixty-percent"),
        pytest.param(
            _exactly_sixty_percent_evidence_share, 2430, False, id="exactly-sixty-percent"
        ),
        pytest.param(
            _exactly_eighty_percent_evidence_share, 3240, False, id="exactly-eighty-percent"
        ),
        pytest.param(_above_evidence_share, 3450, True, id="above-eighty-percent"),
    ],
)
def test_enforces_evidence_dominant_frame_share_boundaries(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    mutate: Mutation,
    expected_frames: int,
    should_raise: bool,
) -> None:
    payload = copy.deepcopy(approved_manifest_data)
    mutate(payload)
    manifest_path = write_manifest(repository_root, payload)

    if should_raise:
        with pytest.raises(ManifestError, match=re.escape("evidence-dominant frames")):
            _load_manifest(manifest_path, repository_root)
    else:
        manifest = _load_manifest(manifest_path, repository_root)
        assert manifest.evidence_dominant_frames == expected_frames


def test_accepts_contiguous_states_and_touching_evidence_rectangles(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    payload = copy.deepcopy(approved_manifest_data)
    _replace_visual_states(
        payload,
        1,
        [
            {
                "id": "left-half",
                "start_frame": 450,
                "end_frame": 750,
                "evidence_rectangles": [{"x": 0, "y": 0, "width": 960, "height": 1080}],
            },
            {
                "id": "right-half",
                "start_frame": 750,
                "end_frame": 1050,
                "evidence_rectangles": [
                    {"x": 0, "y": 0, "width": 960, "height": 1080},
                    {"x": 960, "y": 0, "width": 960, "height": 1080},
                ],
            },
        ],
    )

    manifest = _load_manifest(write_manifest(repository_root, payload), repository_root)

    assert len(manifest.scenes[1].visual_states) == 2
    assert manifest.evidence_dominant_frames == 3000


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        pytest.param("narrated", "final/narrated.txt", id="narrated-text"),
        pytest.param("speaker", "final/speaker", id="speaker-without-suffix"),
        pytest.param("render_manifest", "candidate/render-manifest.mp4", id="manifest-mp4"),
    ],
)
def test_rejects_invalid_output_filename_suffixes(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    field: str,
    replacement: str,
) -> None:
    payload = copy.deepcopy(approved_manifest_data)
    _mapping(payload["output"])[field] = replacement

    with pytest.raises(ManifestError, match=re.escape(f"output.{field}")):
        _load_manifest(write_manifest(repository_root, payload), repository_root)


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
