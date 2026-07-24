"""Content-lock contracts for the repository explainer scene source."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import cast

import pytest

from video_pipeline.capture import verify_evidence_manifest
from video_pipeline.manifest import load_project
from video_pipeline.runner_capture import expand_display_command

REPOSITORY_ROOT = Path(__file__).parents[2]
PRODUCTION_ROOT = REPOSITORY_ROOT / "media" / "repository-explainer"
PROJECT_PATH = PRODUCTION_ROOT / "project.json"
NARRATION_PATH = PRODUCTION_ROOT / "narration.json"
CAPTURE_MANIFEST_PATH = PRODUCTION_ROOT / "captures" / "manifest.json"
THEME_PATH = PRODUCTION_ROOT / "theme.json"
ASSET_PROVENANCE_PATH = PRODUCTION_ROOT / "asset-provenance.json"
HERO_PATH = "docs/apseudo-docs/examples/review-loop.apseudo"
TEACHING_PATH = "tests/fixtures/invalid/unbounded_while.apseudo"
TEACHING_COMMAND = (
    "uv run apseudo-lint --stdin-filename tests/fixtures/invalid/unbounded_while.apseudo "
    "< tests/fixtures/invalid/unbounded_while.apseudo"
)


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_tc_t5_003__pinned_workflow_defect_aliases_and_disclosure__match_evidence() -> None:
    project = load_project(PROJECT_PATH)
    capture = verify_evidence_manifest(
        CAPTURE_MANIFEST_PATH,
        repository_root=REPOSITORY_ROOT,
        allow_blocked_editor=True,
    )
    narration = _json_object(NARRATION_PATH)
    segments = cast(list[dict[str, object]], narration["segments"])
    teaching = next(command for command in capture.commands if command.id == "teaching-defect")
    runner_commands = _json_object(
        PRODUCTION_ROOT / "captures" / "evidence" / "runner" / "runner-commands.json"
    )
    display = cast(dict[str, object], runner_commands["display"])
    aliases = cast(dict[str, object], display["aliases"])
    display_command = cast(str, display["command"])
    base_argv = cast(list[str], runner_commands["base_argv"])

    assert [
        path.relative_to(REPOSITORY_ROOT).as_posix() for path in project.scenes[1].source_paths
    ] == [HERO_PATH]
    assert teaching.argv == (
        "uv",
        "run",
        "apseudo-lint",
        "--stdin-filename",
        TEACHING_PATH,
    )
    assert teaching.stdin_source == TEACHING_PATH
    assert f"{shlex.join(teaching.argv)} < {shlex.quote(teaching.stdin_source)}" == TEACHING_COMMAND
    assert teaching.stdin_sha256 == teaching.source_sha256
    assert (
        teaching.source_sha256
        == hashlib.sha256((REPOSITORY_ROOT / TEACHING_PATH).read_bytes()).hexdigest()
    )
    assert "APSEUDO-WHILE-001" in teaching.promoted_outputs[0].path.read_text(encoding="utf-8")
    assert expand_display_command(display_command, aliases) == tuple(base_argv)
    assert not Path(shlex.split(display_command)[0]).is_absolute()
    assert all(
        not Path(token).is_absolute()
        for token in shlex.split(display_command)
        if token in {"apseudo-run", "apseudo-lint"}
    )
    assert "AI-generated narration." in cast(str, segments[-1]["mute_safe_copy"])
    assert "AI-generated narration." in cast(str, segments[-1]["caption"])


def test_tc_t5_003__theme_and_every_render_input__have_rights_and_checksums() -> None:
    from video_pipeline.scenes import load_asset_catalog, load_theme

    theme = load_theme(THEME_PATH)
    catalog = load_asset_catalog(ASSET_PROVENANCE_PATH, repository_root=REPOSITORY_ROOT)

    assert theme.font_sans_asset_id in catalog.ids
    assert theme.font_mono_asset_id in catalog.ids
    assert {"apseudo-mark", "policy-map"} <= catalog.ids
    assert all(asset.license_id or asset.generation_method for asset in catalog.assets)
    assert all(len(asset.sha256) == 64 for asset in catalog.assets)


def test_tc_t5_003__hero_source__formats_then_lints_cleanly() -> None:
    formatter = subprocess.run(
        ["uv", "run", "apseudo-format", "--check", HERO_PATH],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert formatter.returncode == 0, formatter.stdout + formatter.stderr
    lint = subprocess.run(
        ["uv", "run", "apseudo-lint", HERO_PATH],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr


def test_tc_t5_003__production_editor_pixels__are_real_and_revision_bound() -> None:
    try:
        from video_pipeline.scenes import PRODUCTION_EDITOR_BLOCKER, compose_scene_states
    except ModuleNotFoundError:
        pytest.fail("scene renderer is missing")

    capture = verify_evidence_manifest(
        CAPTURE_MANIFEST_PATH,
        repository_root=REPOSITORY_ROOT,
        allow_blocked_editor=True,
    )
    if capture.editor is None:
        pytest.fail(f"{PRODUCTION_EDITOR_BLOCKER}: {capture.editor_blocker}")

    # Once the capture operator unlocks KDE, this composes the production source and
    # exercises the same geometry binding used by the renderer and C-003 verifier.
    states = compose_scene_states(REPOSITORY_ROOT)
    assert any(state.scene_id == "visible-workflow" for state in states)
