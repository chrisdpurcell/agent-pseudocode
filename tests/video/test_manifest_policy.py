"""Path ownership and Git-index policy contracts for project manifests."""

from __future__ import annotations

import copy
import re
import subprocess
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


def test_rejects_unrelated_ignored_output_root(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / ".gitignore").write_text("dist/\n.venv/\n", encoding="utf-8")
    _mapping(approved_manifest_data["output"])["root"] = ".venv"

    with pytest.raises(ManifestError, match=re.escape("output.root")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_unignored_default_output_root(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / ".gitignore").write_text("", encoding="utf-8")

    with pytest.raises(ManifestError, match=re.escape("output.root")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_git_tracked_generated_target(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    target = (
        repository_root / "dist" / "video" / "final" / "agent-pseudocode-explainer-narrated.mp4"
    )
    target.parent.mkdir(parents=True)
    target.write_bytes(b"not a delivery artifact")
    subprocess.run(
        ["git", "add", "--force", "--", target.relative_to(repository_root)],
        cwd=repository_root,
        check=True,
    )

    with pytest.raises(ManifestError, match=re.escape("output.narrated")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_generated_target_unignored_by_a_negated_rule(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / ".gitignore").write_text(
        "dist/*\n!dist/video/\ndist/video/*\n!dist/video/final/\n"
        "dist/video/final/*\n!dist/video/final/agent-pseudocode-explainer-narrated.mp4\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match=re.escape("output.narrated")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_reports_sanitized_context_for_an_unexpected_git_result(
    monkeypatch: pytest.MonkeyPatch,
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    def fail_git(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=["git"], returncode=2, stderr=b"fatal: secret-token=must-not-appear"
        )

    monkeypatch.setattr("video_pipeline.policy.subprocess.run", fail_git)

    with pytest.raises(
        ManifestError,
        match=re.escape("output.root: Git ignore evaluation failed (exit 2; diagnostic redacted)"),
    ) as raised:
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)

    assert "must-not-appear" not in str(raised.value)


@pytest.mark.parametrize(
    "replacement",
    [
        pytest.param("../outside.mp4", id="outside-output-root"),
        pytest.param("final/unapproved.mp4", id="unapproved-target"),
    ],
)
def test_rejects_output_target_outside_exact_authorized_target(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
    replacement: str,
) -> None:
    _mapping(approved_manifest_data["output"])["narrated"] = replacement

    with pytest.raises(ManifestError, match=re.escape("output.narrated")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_missing_source_path(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    _scene(approved_manifest_data, 0)["source_paths"] = ["docs/missing.apseudo"]

    with pytest.raises(ManifestError, match=re.escape("scenes[0].source_paths[0]")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_directory_source_path(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / "docs" / "source-directory").mkdir(parents=True)
    _scene(approved_manifest_data, 0)["source_paths"] = ["docs/source-directory"]

    with pytest.raises(ManifestError, match=re.escape("scenes[0].source_paths[0]")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_rejects_ignored_untracked_source_path(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    source = repository_root / "docs" / "ignored.apseudo"
    source.write_text("ignored source\n", encoding="utf-8")
    (repository_root / ".gitignore").write_text("dist/\ndocs/ignored.apseudo\n", encoding="utf-8")
    _scene(approved_manifest_data, 0)["source_paths"] = ["docs/ignored.apseudo"]

    with pytest.raises(ManifestError, match=re.escape("scenes[0].source_paths[0]")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_accepts_existing_regular_git_tracked_sources(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    manifest = _load_manifest(
        write_manifest(repository_root, approved_manifest_data), repository_root
    )

    assert manifest.scenes[0].source_paths[0].is_file()


def test_rejects_explicitly_unignored_output_root(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / ".gitignore").write_text("dist/video\n!dist/video\n", encoding="utf-8")

    with pytest.raises(ManifestError, match=re.escape("output.root")):
        _load_manifest(write_manifest(repository_root, approved_manifest_data), repository_root)


def test_accepts_recursively_glob_ignored_output_root(
    repository_root: Path,
    approved_manifest_data: dict[str, object],
    write_manifest: Callable[[Path, Mapping[str, object]], Path],
) -> None:
    (repository_root / ".gitignore").write_text("dist/**/video/\n", encoding="utf-8")

    manifest = _load_manifest(
        write_manifest(repository_root, approved_manifest_data), repository_root
    )

    assert manifest.output.root == repository_root / "dist" / "video"
