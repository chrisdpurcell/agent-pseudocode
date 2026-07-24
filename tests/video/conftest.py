"""Shared fixtures for the repository explainer video production tests."""

from __future__ import annotations

import copy
import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
COMMITTED_MANIFEST_PATH = REPOSITORY_ROOT / "media" / "repository-explainer" / "project.json"
COMMITTED_MANIFEST_DATA = json.loads(COMMITTED_MANIFEST_PATH.read_text(encoding="utf-8"))


def _committed_source_paths() -> list[str]:
    return [
        source_path
        for scene in COMMITTED_MANIFEST_DATA["scenes"]
        for source_path in scene["source_paths"]
    ]


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    """Return a repository-shaped root whose selected output path is ignored."""
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
    for source_path in _committed_source_paths():
        path = tmp_path / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tracked source\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--", ".gitignore", *_committed_source_paths()],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


@pytest.fixture
def approved_manifest_data() -> dict[str, object]:
    """Return the approved six-scene manifest as mutable JSON-compatible data."""
    return copy.deepcopy(COMMITTED_MANIFEST_DATA)


@pytest.fixture
def write_manifest() -> Callable[[Path, Mapping[str, object]], Path]:
    """Write a JSON manifest below a supplied repository root."""

    def write(root: Path, payload: Mapping[str, object]) -> Path:
        manifest_path = root / "media" / "repository-explainer" / "project.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        return manifest_path

    return write
