"""Behavior contracts for truthful command and editor evidence capture."""

from __future__ import annotations

import hashlib
import os
import re
import struct
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from video_pipeline.capture import (
    CaptureError,
    capture_command,
    capture_teaching_defect,
    clean_revision_clone,
    promote_evidence,
    verify_evidence_manifest,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
CAPTURE_MANIFEST = REPOSITORY_ROOT / "media" / "repository-explainer" / "captures" / "manifest.json"
HERO_PATH = "docs/apseudo-docs/examples/review-loop.apseudo"
DEFECT_PATH = "tests/fixtures/invalid/unbounded_while.apseudo"
PINNED_CAPTURE_REVISION = "6fc73b94e5279928a4e37216592f3272ab2ae03b"
CAPTURED_AT = datetime(2026, 7, 23, 15, 30, tzinfo=UTC)


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@contextmanager
def _temporary_repository(tmp_path: Path) -> Generator[tuple[Path, str]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Capture Test")
    _git(
        repository,
        "config",
        "user.email",
        "168346341+chrisdpurcell@users.noreply.github.com",
    )
    _git(repository, "config", "commit.gpgsign", "false")
    (repository / ".gitignore").write_text("dist/\n", encoding="utf-8")
    fixture = repository / DEFECT_PATH
    fixture.parent.mkdir(parents=True)
    fixture.write_text(
        "process bad_loop():\n"
        "    while not approved:\n"
        "        review_document()\n"
        '    return Accepted(reason="done")\n',
        encoding="utf-8",
    )
    hero = repository / HERO_PATH
    hero.parent.mkdir(parents=True)
    hero.write_text('process review():\n    return Accepted(reason="done")\n', encoding="utf-8")
    _git(repository, "add", ".gitignore", DEFECT_PATH, HERO_PATH)
    _git(repository, "commit", "--quiet", "-m", "fixture")
    yield repository, _git(repository, "rev-parse", "HEAD")


def _write_executable(path: Path, body: str) -> Path:
    path.write_text(f"#!/usr/bin/python3\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", header[16:24])


def _source_range(source: bytes, first_line: int, last_line: int) -> bytes:
    return b"".join(source.splitlines(keepends=True)[first_line - 1 : last_line])


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    first, second = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (first + 0.05) / (second + 0.05)


def test_tc_t3_001__allowlisted_command__binds_revision_and_exact_process_evidence(
    tmp_path: Path,
) -> None:
    with _temporary_repository(tmp_path) as (repository, revision):
        _write_executable(
            repository / "capture-tool",
            'import sys\nsys.stdout.buffer.write(b"truthful stdout\\n")\n'
            'sys.stderr.buffer.write(b"truthful stderr\\n")\n',
        )
        _git(repository, "add", "capture-tool")
        _git(repository, "commit", "--quiet", "-m", "add capture tool")
        revision = _git(repository, "rev-parse", "HEAD")

        record = capture_command(
            repository,
            revision=revision,
            argv=("./capture-tool", "literal argument"),
            allowed_executables=frozenset({"./capture-tool"}),
            captured_at=CAPTURED_AT,
        )

        assert record.argv == ("./capture-tool", "literal argument")
        assert record.cwd == "."
        assert record.revision == revision
        assert record.exit_status == 0
        assert record.captured_at == "2026-07-23T15:30:00Z"
        assert record.stdout_sha256 == hashlib.sha256(record.stdout).hexdigest()
        assert record.stderr_sha256 == hashlib.sha256(record.stderr).hexdigest()
        assert record.stdout == b"truthful stdout\n"
        assert record.stderr == b"truthful stderr\n"

        clone_path: Path | None = None
        with clean_revision_clone(repository, revision=revision) as clone:
            clone_path = clone
            assert clone.is_relative_to(repository / "dist" / "video" / "work")
            assert _git(clone, "rev-parse", "HEAD") == revision
            assert _git(clone, "status", "--porcelain=v1", "--untracked-files=all") == ""
        assert clone_path is not None
        assert not clone_path.exists()


def test_tc_t3_002__unsafe_command_path_environment_or_output__fails_closed(
    tmp_path: Path,
) -> None:
    with _temporary_repository(tmp_path) as (repository, revision):
        safe = _write_executable(repository / "safe-tool", 'print("safe")\n')
        leaky = _write_executable(
            repository / "leaky-tool",
            'print("OPENAI_API_KEY=sk-prohibited123456789")\n',
        )
        _git(repository, "add", safe.name, leaky.name)
        _git(repository, "commit", "--quiet", "-m", "add tools")
        revision = _git(repository, "rev-parse", "HEAD")
        allowlist = frozenset({"./safe-tool", "./leaky-tool"})

        with pytest.raises(CaptureError, match="argument vector"):
            capture_command(
                repository,
                revision=revision,
                argv="./safe-tool",
                allowed_executables=allowlist,
            )
        with pytest.raises(CaptureError, match="allowlisted"):
            capture_command(repository, revision=revision, argv=("bash", "-c", "echo unsafe"))
        with pytest.raises(CaptureError, match="cwd"):
            capture_command(
                repository,
                revision=revision,
                argv=("./safe-tool",),
                cwd=tmp_path,
                allowed_executables=allowlist,
            )
        with pytest.raises(CaptureError, match="credential-like environment"):
            capture_command(
                repository,
                revision=revision,
                argv=("./safe-tool",),
                allowed_executables=allowlist,
                environment={"OPENAI_API_KEY": "sk-prohibited123456789"},
            )
        with pytest.raises(CaptureError, match="credential-like output"):
            capture_command(
                repository,
                revision=revision,
                argv=("./leaky-tool",),
                allowed_executables=allowlist,
            )

        (repository / "untracked-source.apseudo").write_text("ambiguous\n", encoding="utf-8")
        with pytest.raises(CaptureError, match="clean Git revision"):
            capture_command(
                repository,
                revision=revision,
                argv=("./safe-tool",),
                allowed_executables=allowlist,
            )


def test_tc_t3_003__named_reviewed_promotion__copies_exact_selected_bytes(
    tmp_path: Path,
) -> None:
    with _temporary_repository(tmp_path) as (repository, revision):
        executable = _write_executable(
            repository / "binary-tool",
            'import sys\nsys.stdout.buffer.write(b"reviewed\\x00bytes\\n")\n',
        )
        _git(repository, "add", executable.name)
        _git(repository, "commit", "--quiet", "-m", "add binary tool")
        revision = _git(repository, "rev-parse", "HEAD")
        record = capture_command(
            repository,
            revision=revision,
            argv=("./binary-tool",),
            allowed_executables=frozenset({"./binary-tool"}),
        )
        evidence_root = tmp_path / "promoted"

        promoted = promote_evidence(
            {"reviewed-command": record},
            capture_name="reviewed-command",
            stream="stdout",
            evidence_root=evidence_root,
            relative_path="commands/reviewed.bin",
        )

        assert promoted.capture_name == "reviewed-command"
        assert promoted.path == evidence_root / "commands" / "reviewed.bin"
        assert promoted.path.read_bytes() == record.stdout
        assert promoted.sha256 == record.stdout_sha256

        with pytest.raises(CaptureError, match="named capture"):
            promote_evidence(
                {"reviewed-command": record},
                capture_name="unreviewed-command",
                stream="stdout",
                evidence_root=evidence_root,
                relative_path="commands/unreviewed.bin",
            )
        with pytest.raises(CaptureError, match="relative_path"):
            promote_evidence(
                {"reviewed-command": record},
                capture_name="reviewed-command",
                stream="stdout",
                evidence_root=evidence_root,
                relative_path="../escape.bin",
            )


def test_tc_t3_004__committed_editor_evidence__has_real_pixel_and_range_provenance() -> None:
    manifest = verify_evidence_manifest(CAPTURE_MANIFEST, repository_root=REPOSITORY_ROOT)

    assert manifest.editor is not None
    assert manifest.revision == PINNED_CAPTURE_REVISION
    assert manifest.editor.operator_role == "capture operator"
    assert manifest.editor.application == "Visual Studio Code"
    assert manifest.editor.application_version == "1.130.0"
    assert manifest.editor.capture_tool == "Spectacle"
    assert manifest.editor.capture_tool_version == "6.7.3"
    assert manifest.editor.settings == {
        "breadcrumbs.enabled": False,
        "editor.fontFamily": "Noto Sans Mono",
        "editor.fontLigatures": False,
        "editor.fontSize": 32,
        "editor.guides.bracketPairs": False,
        "editor.guides.indentation": False,
        "editor.hover.enabled": False,
        "editor.lightbulb.enabled": "off",
        "editor.lineHeight": 40,
        "editor.lineNumbers": "on",
        "editor.matchBrackets": "never",
        "editor.minimap.enabled": False,
        "editor.padding.bottom": 0,
        "editor.padding.top": 120,
        "editor.renderWhitespace": "none",
        "editor.scrollBeyondLastLine": False,
        "editor.stickyScroll.enabled": False,
        "extensions.autoCheckUpdates": False,
        "extensions.autoUpdate": False,
        "git.enabled": False,
        "problems.decorations.enabled": False,
        "security.workspace.trust.enabled": False,
        "telemetry.telemetryLevel": "off",
        "update.mode": "none",
        "window.commandCenter": False,
        "window.menuBarVisibility": "hidden",
        "window.newWindowDimensions": "fullscreen",
        "window.zoomLevel": 0,
        "workbench.activityBar.location": "hidden",
        "workbench.colorTheme": "Default High Contrast",
        "workbench.editor.showTabs": "none",
        "workbench.layoutControl.enabled": False,
        "workbench.startupEditor": "none",
        "workbench.statusBar.visible": False,
        "workbench.tips.enabled": False,
        "zenMode.centerLayout": False,
        "zenMode.fullScreen": True,
        "zenMode.hideActivityBar": True,
        "zenMode.hideLineNumbers": False,
        "zenMode.hideStatusBar": True,
        "zenMode.showTabs": "none",
    }
    assert manifest.editor.viewport == (0, 0, 1920, 1080)
    assert manifest.editor.source_crop == (0, 120, 1728, 786)
    assert manifest.editor.destination_rectangle == (96, 54, 1728, 786)
    assert manifest.editor.evidence_rectangle == (96, 54, 1728, 786)
    assert manifest.editor.caption_rectangle == (96, 864, 1728, 162)
    assert manifest.editor.native_scale == 1.0
    assert manifest.editor.monitor_count == 1
    assert (
        _contrast_ratio(manifest.editor.palette_foreground, manifest.editor.palette_background)
        >= 4.5
    )

    source = subprocess.run(
        ["git", "show", f"{manifest.revision}:{manifest.editor.source_path}"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(source).hexdigest() == manifest.editor.source_sha256
    assert len(manifest.editor.frames) >= 2
    covered_lines: set[int] = set()
    for frame in manifest.editor.frames:
        assert frame.path.is_relative_to(
            REPOSITORY_ROOT / "media" / "repository-explainer" / "captures" / "evidence" / "editor"
        )
        assert _png_dimensions(frame.path) == (1920, 1080)
        assert hashlib.sha256(frame.path.read_bytes()).hexdigest() == frame.png_sha256
        assert frame.spectacle_argv[:4] == (
            "spectacle",
            "--current",
            "--background",
            "--nonotify",
        )
        assert frame.spectacle_argv[4] == "--output"
        assert frame.spectacle_argv[5] == frame.output_argument
        source_bytes = _source_range(source, frame.first_line, frame.last_line)
        assert hashlib.sha256(source_bytes).hexdigest() == frame.source_range_sha256
        covered_lines.update(range(frame.first_line, frame.last_line + 1))
    assert covered_lines == set(range(1, 28))


def test_tc_t3_005__teaching_defect__uses_tracked_stdin_and_requires_diagnostic(
    tmp_path: Path,
) -> None:
    with _temporary_repository(tmp_path) as (repository, revision):
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        _write_executable(
            fake_bin / "uv",
            "import sys\n"
            f"expected = {['run', 'apseudo-lint', '--stdin-filename', DEFECT_PATH]!r}\n"
            "if sys.argv[1:] != expected:\n"
            "    raise SystemExit(9)\n"
            "source = sys.stdin.buffer.read()\n"
            "if b'while not approved' not in source:\n"
            "    raise SystemExit(8)\n"
            "sys.stderr.write('stdin:2:5: error APSEUDO-WHILE-001 unbounded while loop\\n')\n"
            "raise SystemExit(1)\n",
        )

        teaching = capture_teaching_defect(
            repository,
            revision=revision,
            environment={"PATH": os.fspath(fake_bin)},
            captured_at=CAPTURED_AT,
        )

        assert teaching.command.argv == (
            "uv",
            "run",
            "apseudo-lint",
            "--stdin-filename",
            DEFECT_PATH,
        )
        assert teaching.command.exit_status == 1
        assert teaching.command.stdin_source == DEFECT_PATH
        assert teaching.source_path == DEFECT_PATH
        tracked_bytes = subprocess.run(
            ["git", "show", f"{revision}:{DEFECT_PATH}"],
            cwd=repository,
            check=True,
            capture_output=True,
        ).stdout
        assert teaching.source_sha256 == hashlib.sha256(tracked_bytes).hexdigest()
        assert teaching.command.stdin_sha256 == teaching.source_sha256
        assert b"APSEUDO-WHILE-001" in teaching.command.stderr
        assert not any(
            path.name != Path(DEFECT_PATH).name
            for path in (repository / "tests" / "fixtures" / "invalid").iterdir()
        )


def test_committed_command_evidence__hashes_and_paths_resolve_without_secrets() -> None:
    manifest = verify_evidence_manifest(
        CAPTURE_MANIFEST,
        repository_root=REPOSITORY_ROOT,
        allow_blocked_editor=True,
    )
    serialized = CAPTURE_MANIFEST.read_text(encoding="utf-8")

    assert not re.search(
        r"(?i)(authorization|api[_-]?key|access[_-]?token|secret[_-]?key|password)\\s*[:=]",
        serialized,
    )
    assert {record.id for record in manifest.commands} == {
        "hero-format-check",
        "hero-lint",
        "while-rule-explanation",
        "hero-mermaid",
        "teaching-defect",
    }
    for record in manifest.commands:
        assert record.revision == manifest.revision
        assert record.cwd == "."
        assert len(record.stdout_sha256) == 64
        assert len(record.stderr_sha256) == 64
        for output in record.promoted_outputs:
            assert output.path.is_file()
            assert hashlib.sha256(output.path.read_bytes()).hexdigest() == output.sha256

    teaching = next(record for record in manifest.commands if record.id == "teaching-defect")
    assert teaching.argv == (
        "uv",
        "run",
        "apseudo-lint",
        "--stdin-filename",
        DEFECT_PATH,
    )
    assert teaching.exit_status == 1
    assert teaching.stdin_source == DEFECT_PATH
    assert teaching.source_path == DEFECT_PATH
    assert teaching.source_sha256 == teaching.stdin_sha256
