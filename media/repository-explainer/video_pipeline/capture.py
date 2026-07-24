"""Capture and verify byte-exact repository evidence at a clean Git revision.

Every subprocess crosses one policy boundary here: callers supply an argument
vector, the executable must be allowlisted, and the working tree must match the
recorded commit before and after execution. Promoted evidence is selected by
capture name and copied byte-for-byte; no shell command or environment snapshot
is accepted or persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

DEFAULT_ALLOWED_EXECUTABLES = frozenset({"spectacle", "uv"})
TEACHING_DEFECT_PATH = "tests/fixtures/invalid/unbounded_while.apseudo"
TEACHING_DEFECT_ARGV = (
    "uv",
    "run",
    "apseudo-lint",
    "--stdin-filename",
    TEACHING_DEFECT_PATH,
)
HERO_SOURCE_PATH = "docs/apseudo-docs/examples/review-loop.apseudo"
CAPTURE_ROOT = Path("media/repository-explainer/captures")
EVIDENCE_ROOT = CAPTURE_ROOT / "evidence"
EDITOR_EVIDENCE_ROOT = EVIDENCE_ROOT / "editor"
RUNNER_EVIDENCE_ROOT = EVIDENCE_ROOT / "runner"
RUNNER_EVIDENCE_NAMES = (
    "hook-preflight.json",
    "runner-commands.json",
    "run-manifest.json",
    "agent-command.json",
    "validation-before.json",
    "post-checks.json",
    "changed-files.json",
    "outcome.json",
)
SOURCE_CROP = (0, 120, 1728, 786)
DESTINATION_RECTANGLE = (96, 54, 1728, 786)
CAPTION_RECTANGLE = (96, 864, 1728, 162)
EDITOR_SETTINGS: dict[str, object] = {
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
_SAFE_INHERITED_ENVIRONMENT = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "TZ",
    "UV_CACHE_DIR",
    "XDG_CACHE_HOME",
)
_CREDENTIAL_NAME = re.compile(
    r"(?i)(?:^|_)(?:api_?key|authorization|credential|password|private_?key|"
    r"secret|token)(?:$|_)"
)
_CREDENTIAL_OUTPUT = re.compile(
    rb"(?i)(?:authorization|api[_-]?key|access[_-]?token|secret[_-]?key|password)"
    rb"\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40}")


class CaptureError(ValueError):
    """Reject unsafe, ambiguous, or unverifiable capture input."""


@dataclass(frozen=True, slots=True)
class CommandCapture:
    """One completed process plus the bytes needed for reviewed promotion."""

    argv: tuple[str, ...]
    cwd: str
    revision: str
    exit_status: int
    captured_at: str
    stdout: bytes
    stderr: bytes
    stdout_sha256: str
    stderr_sha256: str
    stdin_sha256: str | None
    stdin_source: str | None


@dataclass(frozen=True, slots=True)
class PromotedEvidence:
    """A named command stream promoted without semantic transformation."""

    capture_name: str
    stream: Literal["stdout", "stderr"]
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class TeachingDefectCapture:
    """The tracked unbounded-loop fixture and its required diagnostic."""

    source_path: str
    source_sha256: str
    command: CommandCapture


@dataclass(frozen=True, slots=True)
class EvidenceOutput:
    """A promoted command output whose bytes still match its ledger hash."""

    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class CommandEvidence:
    """A manifest command record bound to one revision and reviewed outputs."""

    id: str
    argv: tuple[str, ...]
    cwd: str
    revision: str
    captured_at: str
    exit_status: int
    stdout_sha256: str
    stderr_sha256: str
    stdin_source: str | None
    stdin_sha256: str | None
    source_path: str | None
    source_sha256: str | None
    promoted_outputs: tuple[EvidenceOutput, ...]


@dataclass(frozen=True, slots=True)
class EditorFrame:
    """One unscaled workstation screenshot and the source lines visible in it."""

    id: str
    path: Path
    png_sha256: str
    first_line: int
    last_line: int
    source_range_sha256: str
    spectacle_argv: tuple[str, ...]
    output_argument: str


@dataclass(frozen=True, slots=True)
class EditorEvidence:
    """The exact editor substrate whose pixels may be cropped by later scenes."""

    operator_role: str
    application: str
    application_version: str
    capture_tool: str
    capture_tool_version: str
    captured_at: str
    settings: dict[str, object]
    viewport: tuple[int, int, int, int]
    source_crop: tuple[int, int, int, int]
    destination_rectangle: tuple[int, int, int, int]
    evidence_rectangle: tuple[int, int, int, int]
    caption_rectangle: tuple[int, int, int, int]
    native_scale: float
    monitor_count: int
    palette_foreground: str
    palette_background: str
    source_path: str
    source_sha256: str
    frames: tuple[EditorFrame, ...]


@dataclass(frozen=True, slots=True)
class RunnerEvidenceFile:
    """One promoted runner record that survives disposable-clone deletion."""

    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class RunnerEvidenceLedger:
    """Typed hash ledger for an accepted or truthful preflight-only runner capture."""

    mode: Literal["accepted", "preflight-only"]
    reason: str
    revision: str
    evidence: tuple[RunnerEvidenceFile, ...]


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    """Verified command and real-editor evidence for one pinned commit."""

    revision: str
    commands: tuple[CommandEvidence, ...]
    editor: EditorEvidence | None
    editor_blocker: str | None
    runner: RunnerEvidenceLedger | None


def capture_command(
    repository_root: Path,
    *,
    revision: str,
    argv: Sequence[object],
    cwd: Path | None = None,
    stdin_bytes: bytes | None = None,
    stdin_source: str | None = None,
    expected_exit_codes: frozenset[int] = frozenset({0}),
    allowed_executables: frozenset[str] | None = None,
    environment: Mapping[object, object] | None = None,
    captured_at: datetime | None = None,
) -> CommandCapture:
    """Run one allowlisted argument vector and return its exact bounded evidence.

    Environment values are neither recorded nor exposed. Only a small inherited
    operational set reaches the child, and explicit additions fail closed when
    their names or values look credential-bearing.
    """
    root = _resolved_directory(repository_root, "repository_root")
    command_cwd = _resolved_directory(cwd if cwd is not None else root, "cwd")
    _require_below(command_cwd, root, "cwd")
    arguments = _argument_vector(argv)
    executable_allowlist = (
        allowed_executables if allowed_executables is not None else DEFAULT_ALLOWED_EXECUTABLES
    )
    if arguments[0] not in executable_allowlist:
        raise CaptureError(f"argv[0]: executable {arguments[0]!r} is not allowlisted")
    if not expected_exit_codes:
        raise CaptureError("expected_exit_codes: must not be empty")
    child_environment = _safe_environment(environment)
    exact_revision = _require_clean_revision(root, revision)
    timestamp = _timestamp(captured_at)

    try:
        completed = subprocess.run(
            list(arguments),
            cwd=command_cwd,
            input=stdin_bytes,
            check=False,
            capture_output=True,
            env=child_environment,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise CaptureError(
            f"argv[0]: allowlisted executable {arguments[0]!r} was not found"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CaptureError("capture command timed out") from exc
    except OSError as exc:
        raise CaptureError("capture command could not start") from exc

    stdout = completed.stdout
    stderr = completed.stderr
    if _contains_credential(stdout) or _contains_credential(stderr):
        raise CaptureError("capture command produced credential-like output")
    _require_clean_revision(root, exact_revision)
    if completed.returncode not in expected_exit_codes:
        raise CaptureError(
            f"capture command exited {completed.returncode}; expected {sorted(expected_exit_codes)}"
        )
    return CommandCapture(
        argv=arguments,
        cwd=command_cwd.relative_to(root).as_posix() or ".",
        revision=exact_revision,
        exit_status=completed.returncode,
        captured_at=timestamp,
        stdout=stdout,
        stderr=stderr,
        stdout_sha256=_digest(stdout),
        stderr_sha256=_digest(stderr),
        stdin_sha256=_digest(stdin_bytes) if stdin_bytes is not None else None,
        stdin_source=stdin_source,
    )


@contextmanager
def clean_revision_clone(
    repository_root: Path, *, revision: str, work_root: Path | None = None
) -> Generator[Path]:
    """Yield a disposable clean clone at ``revision`` below ``dist/video/work``.

    The source checkout may contain unrelated work because the clone reads only
    the named commit object. The yielded clone itself must be clean, which keeps
    later T3/T4 commands from confusing operator edits with captured behavior.
    """
    root = _resolved_directory(repository_root, "repository_root")
    exact_revision = _resolve_revision(root, revision)
    authorized_work_root = (root / "dist" / "video" / "work").resolve()
    selected_work_root = (
        _safe_resolve(work_root, "work_root") if work_root is not None else authorized_work_root
    )
    _require_below(selected_work_root, authorized_work_root, "work_root")
    selected_work_root.mkdir(parents=True, exist_ok=True)
    clone = Path(tempfile.mkdtemp(prefix="capture-clone-", dir=selected_work_root))
    clone.rmdir()
    try:
        _run_checked(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                "--shared",
                "--",
                os.fspath(root),
                os.fspath(clone),
            ],
            cwd=root,
            operation="Git clone",
        )
        _run_checked(
            ["git", "checkout", "--quiet", "--detach", exact_revision],
            cwd=clone,
            operation="Git checkout",
        )
        if _resolve_revision(clone, "HEAD") != exact_revision:
            raise CaptureError("clean clone did not reach the pinned revision")
        _require_clean_revision(clone, exact_revision)
        yield clone
    finally:
        if clone.exists():
            shutil.rmtree(clone)


def promote_evidence(
    captures: Mapping[str, CommandCapture],
    *,
    capture_name: str,
    stream: Literal["stdout", "stderr"] | str,
    evidence_root: Path,
    relative_path: str,
) -> PromotedEvidence:
    """Promote one explicitly named stream, preserving its bytes exactly."""
    try:
        capture = captures[capture_name]
    except KeyError as exc:
        raise CaptureError(f"capture_name: no named capture {capture_name!r}") from exc
    if stream not in {"stdout", "stderr"}:
        raise CaptureError("stream: expected 'stdout' or 'stderr'")
    root = _safe_resolve(evidence_root, "evidence_root")
    destination = _owned_relative_path(root, relative_path, "relative_path")
    content = capture.stdout if stream == "stdout" else capture.stderr
    expected_digest = capture.stdout_sha256 if stream == "stdout" else capture.stderr_sha256
    if destination.exists():
        try:
            existing = destination.read_bytes()
        except OSError as exc:
            raise CaptureError("relative_path: existing evidence could not be read") from exc
        if existing != content:
            raise CaptureError("relative_path: existing evidence has different bytes")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            temporary.replace(destination)
        except OSError as exc:
            raise CaptureError("relative_path: evidence promotion failed") from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    if _digest(destination.read_bytes()) != expected_digest:
        raise CaptureError("relative_path: promoted bytes do not match the capture hash")
    return PromotedEvidence(
        capture_name=capture_name,
        stream=cast(Literal["stdout", "stderr"], stream),
        path=destination,
        sha256=expected_digest,
    )


def capture_teaching_defect(
    repository_root: Path,
    *,
    revision: str,
    environment: Mapping[object, object] | None = None,
    captured_at: datetime | None = None,
) -> TeachingDefectCapture:
    """Capture the tracked teaching defect through its exact stdin command."""
    root = _resolved_directory(repository_root, "repository_root")
    exact_revision = _resolve_revision(root, revision)
    tracked_source = _git_object(root, exact_revision, TEACHING_DEFECT_PATH)
    source_path = _owned_relative_path(root, TEACHING_DEFECT_PATH, "teaching source")
    try:
        working_source = source_path.read_bytes()
    except OSError as exc:
        raise CaptureError("teaching source: tracked fixture could not be read") from exc
    if working_source != tracked_source:
        raise CaptureError("teaching source: working bytes differ from the pinned revision")
    command = capture_command(
        root,
        revision=exact_revision,
        argv=TEACHING_DEFECT_ARGV,
        stdin_bytes=tracked_source,
        stdin_source=TEACHING_DEFECT_PATH,
        expected_exit_codes=frozenset({1}),
        environment=environment,
        captured_at=captured_at,
    )
    if b"APSEUDO-WHILE-001" not in command.stdout + command.stderr:
        raise CaptureError("teaching defect: APSEUDO-WHILE-001 diagnostic is missing")
    return TeachingDefectCapture(
        source_path=TEACHING_DEFECT_PATH,
        source_sha256=_digest(tracked_source),
        command=command,
    )


def verify_evidence_manifest(
    path: Path, *, repository_root: Path, allow_blocked_editor: bool = False
) -> EvidenceManifest:
    """Load the committed ledger and reverify every referenced byte and source range."""
    root = _resolved_directory(repository_root, "repository_root")
    manifest_path = _safe_resolve(path, "manifest")
    _require_below(manifest_path, root, "manifest")
    try:
        raw = manifest_path.read_bytes()
    except FileNotFoundError as exc:
        raise CaptureError("manifest: file not found") from exc
    except OSError as exc:
        raise CaptureError("manifest: could not be read") from exc
    if _contains_credential(raw):
        raise CaptureError("manifest: credential-like content is prohibited")
    try:
        decoded: object = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureError("manifest: invalid JSON") from exc
    payload = _object(decoded, "manifest")
    manifest_fields = {"schema_version", "revision", "commands", "editor"}
    if "runner" in payload:
        manifest_fields.add("runner")
    _exact_fields(payload, manifest_fields, "manifest")
    if _integer(payload.get("schema_version"), "schema_version") != 1:
        raise CaptureError("schema_version: expected 1")
    revision = _string(payload.get("revision"), "revision")
    if not _REVISION.fullmatch(revision):
        raise CaptureError("revision: expected a full lowercase Git commit")
    if _resolve_revision(root, revision) != revision:
        raise CaptureError("revision: Git object does not match the ledger")
    command_values = _array(payload.get("commands"), "commands")
    commands = tuple(
        _parse_command_evidence(_object(value, f"commands[{index}]"), index, root, revision)
        for index, value in enumerate(command_values)
    )
    if len({record.id for record in commands}) != len(commands):
        raise CaptureError("commands: ids must be unique")
    editor_payload = _object(payload.get("editor"), "editor")
    if editor_payload.get("status") == "blocked":
        _exact_fields(
            editor_payload,
            {"status", "blocker", "observed_at", "rejected_capture"},
            "editor",
        )
        blocker = _string(editor_payload.get("blocker"), "editor.blocker")
        _timestamp_string(editor_payload.get("observed_at"), "editor.observed_at")
        _string(editor_payload.get("rejected_capture"), "editor.rejected_capture")
        if not allow_blocked_editor:
            raise CaptureError(f"editor: blocked: {blocker}")
        editor = None
        editor_blocker = blocker
    else:
        editor = _parse_editor(editor_payload, root, revision)
        editor_blocker = None
    runner_payload = payload.get("runner")
    runner = (
        _parse_runner(_object(runner_payload, "runner"), root, revision)
        if runner_payload is not None
        else None
    )
    return EvidenceManifest(
        revision=revision,
        commands=commands,
        editor=editor,
        editor_blocker=editor_blocker,
        runner=runner,
    )


def _parse_runner(payload: dict[str, object], root: Path, revision: str) -> RunnerEvidenceLedger:
    _exact_fields(payload, {"mode", "reason", "revision", "evidence"}, "runner")
    mode_value = _string(payload.get("mode"), "runner.mode")
    if mode_value not in {"accepted", "preflight-only"}:
        raise CaptureError("runner.mode: expected 'accepted' or 'preflight-only'")
    mode = cast(Literal["accepted", "preflight-only"], mode_value)
    reason = _string(payload.get("reason"), "runner.reason")
    runner_revision = _string(payload.get("revision"), "runner.revision")
    if runner_revision != revision:
        raise CaptureError("runner.revision: must match manifest revision")
    evidence_values = _array(payload.get("evidence"), "runner.evidence")
    evidence = tuple(
        _parse_runner_evidence_file(
            _object(value, f"runner.evidence[{index}]"),
            f"runner.evidence[{index}]",
            root,
        )
        for index, value in enumerate(evidence_values)
    )
    names = tuple(record.path.name for record in evidence)
    if len(names) != len(set(names)) or set(names) != set(RUNNER_EVIDENCE_NAMES):
        raise CaptureError("runner.evidence: expected each required runner record exactly once")
    outcome_path = next(record.path for record in evidence if record.path.name == "outcome.json")
    try:
        outcome_raw = outcome_path.read_bytes()
        outcome_value: object = json.loads(outcome_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureError("runner.evidence: outcome.json is unavailable or invalid") from exc
    outcome = _object(outcome_value, "runner.evidence.outcome")
    if (
        outcome.get("mode") != mode
        or outcome.get("accepted") is not (mode == "accepted")
        or outcome.get("revision") != revision
        or outcome.get("reason") != reason
    ):
        raise CaptureError("runner: ledger does not match promoted outcome.json")
    return RunnerEvidenceLedger(
        mode=mode,
        reason=reason,
        revision=runner_revision,
        evidence=evidence,
    )


def _parse_runner_evidence_file(
    payload: dict[str, object], field: str, root: Path
) -> RunnerEvidenceFile:
    _exact_fields(payload, {"path", "sha256"}, field)
    relative_path = _string(payload.get("path"), f"{field}.path")
    path = _owned_relative_path(root, relative_path, f"{field}.path")
    _require_below(path, (root / RUNNER_EVIDENCE_ROOT).resolve(), f"{field}.path")
    expected_hash = _hash(payload.get("sha256"), f"{field}.sha256")
    try:
        actual_hash = _digest(path.read_bytes())
    except OSError as exc:
        raise CaptureError(f"{field}.path: evidence could not be read") from exc
    if actual_hash != expected_hash:
        raise CaptureError(f"{field}.sha256: promoted runner evidence bytes changed")
    return RunnerEvidenceFile(path=path, sha256=expected_hash)


def _parse_command_evidence(
    payload: dict[str, object], index: int, root: Path, revision: str
) -> CommandEvidence:
    field = f"commands[{index}]"
    _exact_fields(
        payload,
        {
            "id",
            "argv",
            "cwd",
            "revision",
            "captured_at",
            "exit_status",
            "stdout_sha256",
            "stderr_sha256",
            "stdin_source",
            "stdin_sha256",
            "source_path",
            "source_sha256",
            "promoted_outputs",
        },
        field,
    )
    record_revision = _string(payload.get("revision"), f"{field}.revision")
    if record_revision != revision:
        raise CaptureError(f"{field}.revision: must match manifest revision")
    cwd = _string(payload.get("cwd"), f"{field}.cwd")
    if cwd != ".":
        raise CaptureError(f"{field}.cwd: expected repository root")
    argv = tuple(
        _string(value, f"{field}.argv[{argument_index}]")
        for argument_index, value in enumerate(_array(payload.get("argv"), f"{field}.argv"))
    )
    if not argv:
        raise CaptureError(f"{field}.argv: must not be empty")
    stdout_sha256 = _hash(payload.get("stdout_sha256"), f"{field}.stdout_sha256")
    stderr_sha256 = _hash(payload.get("stderr_sha256"), f"{field}.stderr_sha256")
    stdin_source = _optional_string(payload.get("stdin_source"), f"{field}.stdin_source")
    stdin_sha256 = _optional_hash(payload.get("stdin_sha256"), f"{field}.stdin_sha256")
    source_path = _optional_string(payload.get("source_path"), f"{field}.source_path")
    source_sha256 = _optional_hash(payload.get("source_sha256"), f"{field}.source_sha256")
    if (stdin_source is None) != (stdin_sha256 is None):
        raise CaptureError(f"{field}: stdin source and hash must be present together")
    if (source_path is None) != (source_sha256 is None):
        raise CaptureError(f"{field}: source path and hash must be present together")
    if (
        source_path is not None
        and source_sha256 is not None
        and _digest(_git_object(root, revision, source_path)) != source_sha256
    ):
        raise CaptureError(f"{field}.source_sha256: pinned source bytes changed")
    promoted_outputs = tuple(
        _parse_promoted_output(
            _object(value, f"{field}.promoted_outputs[{output_index}]"),
            f"{field}.promoted_outputs[{output_index}]",
            root,
        )
        for output_index, value in enumerate(
            _array(payload.get("promoted_outputs"), f"{field}.promoted_outputs")
        )
    )
    return CommandEvidence(
        id=_string(payload.get("id"), f"{field}.id"),
        argv=argv,
        cwd=cwd,
        revision=record_revision,
        captured_at=_timestamp_string(payload.get("captured_at"), f"{field}.captured_at"),
        exit_status=_integer(payload.get("exit_status"), f"{field}.exit_status"),
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
        stdin_source=stdin_source,
        stdin_sha256=stdin_sha256,
        source_path=source_path,
        source_sha256=source_sha256,
        promoted_outputs=promoted_outputs,
    )


def _parse_promoted_output(payload: dict[str, object], field: str, root: Path) -> EvidenceOutput:
    _exact_fields(payload, {"path", "sha256"}, field)
    relative_path = _string(payload.get("path"), f"{field}.path")
    path = _owned_relative_path(root, relative_path, f"{field}.path")
    expected_root = (root / EVIDENCE_ROOT).resolve()
    _require_below(path, expected_root, f"{field}.path")
    expected_hash = _hash(payload.get("sha256"), f"{field}.sha256")
    try:
        actual_hash = _digest(path.read_bytes())
    except OSError as exc:
        raise CaptureError(f"{field}.path: evidence could not be read") from exc
    if actual_hash != expected_hash:
        raise CaptureError(f"{field}.sha256: promoted evidence bytes changed")
    return EvidenceOutput(path=path, sha256=expected_hash)


def _parse_editor(payload: dict[str, object], root: Path, revision: str) -> EditorEvidence:
    _exact_fields(
        payload,
        {
            "operator_role",
            "application",
            "application_version",
            "capture_tool",
            "capture_tool_version",
            "captured_at",
            "settings",
            "viewport",
            "monitor_count",
            "native_scale",
            "source_path",
            "source_revision",
            "source_sha256",
            "source_crop",
            "destination_rectangle",
            "evidence_rectangle",
            "caption_rectangle",
            "palette",
            "frames",
            "overlay_copy",
        },
        "editor",
    )
    source_path = _string(payload.get("source_path"), "editor.source_path")
    if source_path != HERO_SOURCE_PATH:
        raise CaptureError(f"editor.source_path: expected {HERO_SOURCE_PATH!r}")
    source_revision = _string(payload.get("source_revision"), "editor.source_revision")
    if source_revision != revision:
        raise CaptureError("editor.source_revision: must match manifest revision")
    source = _git_object(root, revision, source_path)
    source_sha256 = _hash(payload.get("source_sha256"), "editor.source_sha256")
    if _digest(source) != source_sha256:
        raise CaptureError("editor.source_sha256: pinned source bytes changed")
    settings = _object(payload.get("settings"), "editor.settings")
    if settings != EDITOR_SETTINGS:
        raise CaptureError("editor.settings: exact capture settings changed")
    if payload.get("overlay_copy") is not False:
        raise CaptureError("editor.overlay_copy: source substrate must not contain overlay copy")
    operator_role = _string(payload.get("operator_role"), "editor.operator_role")
    application = _string(payload.get("application"), "editor.application")
    application_version = _string(payload.get("application_version"), "editor.application_version")
    capture_tool = _string(payload.get("capture_tool"), "editor.capture_tool")
    capture_tool_version = _string(
        payload.get("capture_tool_version"), "editor.capture_tool_version"
    )
    if operator_role != "capture operator":
        raise CaptureError("editor.operator_role: expected 'capture operator'")
    if (application, application_version) != ("Visual Studio Code", "1.130.0"):
        raise CaptureError("editor.application: exact Visual Studio Code version is unavailable")
    if (capture_tool, capture_tool_version) != ("Spectacle", "6.7.3"):
        raise CaptureError("editor.capture_tool: exact Spectacle version is unavailable")
    captured_at = _timestamp_string(payload.get("captured_at"), "editor.captured_at")
    viewport = _integer_tuple(payload.get("viewport"), "editor.viewport")
    source_crop = _integer_tuple(payload.get("source_crop"), "editor.source_crop")
    destination = _integer_tuple(
        payload.get("destination_rectangle"), "editor.destination_rectangle"
    )
    evidence = _integer_tuple(payload.get("evidence_rectangle"), "editor.evidence_rectangle")
    caption = _integer_tuple(payload.get("caption_rectangle"), "editor.caption_rectangle")
    if viewport != (0, 0, 1920, 1080):
        raise CaptureError("editor.viewport: expected one 1920x1080 monitor")
    if source_crop != SOURCE_CROP:
        raise CaptureError("editor.source_crop: exact native crop changed")
    if destination != DESTINATION_RECTANGLE or evidence != DESTINATION_RECTANGLE:
        raise CaptureError("editor destination/evidence rectangle changed")
    if caption != CAPTION_RECTANGLE:
        raise CaptureError("editor.caption_rectangle: exact caption band changed")
    if _rectangles_overlap(destination, caption):
        raise CaptureError("editor rectangles: evidence overlaps the caption band")
    native_scale = _number(payload.get("native_scale"), "editor.native_scale")
    if native_scale != 1.0:
        raise CaptureError("editor.native_scale: expected 1.0")
    monitor_count = _integer(payload.get("monitor_count"), "editor.monitor_count")
    if monitor_count != 1:
        raise CaptureError("editor.monitor_count: expected 1")
    palette = _object(payload.get("palette"), "editor.palette")
    _exact_fields(palette, {"foreground", "background", "contrast_ratio"}, "editor.palette")
    foreground = _hex_color(palette.get("foreground"), "editor.palette.foreground")
    background = _hex_color(palette.get("background"), "editor.palette.background")
    computed_contrast = _contrast_ratio(foreground, background)
    recorded_contrast = _number(palette.get("contrast_ratio"), "editor.palette.contrast_ratio")
    if abs(computed_contrast - recorded_contrast) > 0.01 or computed_contrast < 4.5:
        raise CaptureError("editor.palette: contrast ratio is invalid")
    frames = tuple(
        _parse_editor_frame(
            _object(value, f"editor.frames[{index}]"),
            index,
            root,
            source,
        )
        for index, value in enumerate(_array(payload.get("frames"), "editor.frames"))
    )
    if len(frames) < 2:
        raise CaptureError("editor.frames: at least two real scroll states are required")
    covered = {line for frame in frames for line in range(frame.first_line, frame.last_line + 1)}
    if covered != set(range(1, len(source.splitlines()) + 1)):
        raise CaptureError("editor.frames: displayed ranges must cover every hero source line")
    return EditorEvidence(
        operator_role=operator_role,
        application=application,
        application_version=application_version,
        capture_tool=capture_tool,
        capture_tool_version=capture_tool_version,
        captured_at=captured_at,
        settings=settings,
        viewport=viewport,
        source_crop=source_crop,
        destination_rectangle=destination,
        evidence_rectangle=evidence,
        caption_rectangle=caption,
        native_scale=native_scale,
        monitor_count=monitor_count,
        palette_foreground=foreground,
        palette_background=background,
        source_path=source_path,
        source_sha256=source_sha256,
        frames=frames,
    )


def _parse_editor_frame(
    payload: dict[str, object], index: int, root: Path, source: bytes
) -> EditorFrame:
    field = f"editor.frames[{index}]"
    _exact_fields(
        payload,
        {
            "id",
            "path",
            "png_sha256",
            "png_dimensions",
            "displayed_line_range",
            "source_range_sha256",
            "spectacle_argv",
            "output_argument",
        },
        field,
    )
    path = _owned_relative_path(
        root, _string(payload.get("path"), f"{field}.path"), f"{field}.path"
    )
    _require_below(path, (root / EDITOR_EVIDENCE_ROOT).resolve(), f"{field}.path")
    png_sha256 = _hash(payload.get("png_sha256"), f"{field}.png_sha256")
    try:
        png = path.read_bytes()
    except OSError as exc:
        raise CaptureError(f"{field}.path: PNG could not be read") from exc
    if _digest(png) != png_sha256:
        raise CaptureError(f"{field}.png_sha256: screenshot bytes changed")
    dimensions = _png_dimensions(png, f"{field}.png_dimensions")
    if dimensions != _integer_pair(payload.get("png_dimensions"), f"{field}.png_dimensions"):
        raise CaptureError(f"{field}.png_dimensions: PNG header does not match")
    if dimensions != (1920, 1080):
        raise CaptureError(f"{field}.png_dimensions: expected 1920x1080")
    first_line, last_line = _integer_pair(
        payload.get("displayed_line_range"), f"{field}.displayed_line_range"
    )
    source_lines = source.splitlines(keepends=True)
    if first_line < 1 or last_line < first_line or last_line > len(source_lines):
        raise CaptureError(f"{field}.displayed_line_range: outside source")
    source_range_sha256 = _hash(payload.get("source_range_sha256"), f"{field}.source_range_sha256")
    if _digest(b"".join(source_lines[first_line - 1 : last_line])) != source_range_sha256:
        raise CaptureError(f"{field}.source_range_sha256: displayed source range changed")
    argv = tuple(
        _string(value, f"{field}.spectacle_argv[{argument_index}]")
        for argument_index, value in enumerate(
            _array(payload.get("spectacle_argv"), f"{field}.spectacle_argv")
        )
    )
    output_argument = _string(payload.get("output_argument"), f"{field}.output_argument")
    expected_argv = (
        "spectacle",
        "--current",
        "--background",
        "--nonotify",
        "--output",
        output_argument,
    )
    if argv != expected_argv:
        raise CaptureError(f"{field}.spectacle_argv: exact capture command changed")
    if Path(output_argument).resolve() != path:
        raise CaptureError(f"{field}.output_argument: must resolve to the tracked PNG")
    return EditorFrame(
        id=_string(payload.get("id"), f"{field}.id"),
        path=path,
        png_sha256=png_sha256,
        first_line=first_line,
        last_line=last_line,
        source_range_sha256=source_range_sha256,
        spectacle_argv=argv,
        output_argument=output_argument,
    )


def _argument_vector(argv: Sequence[object]) -> tuple[str, ...]:
    if isinstance(argv, (str, bytes)):
        raise CaptureError("argv: expected an argument vector, not a shell string")
    raw_arguments = tuple(argv)
    if not raw_arguments:
        raise CaptureError("argv: argument vector must not be empty")
    if any(
        not isinstance(argument, str) or not argument or "\x00" in argument
        for argument in raw_arguments
    ):
        raise CaptureError("argv: every argument must be a non-empty NUL-free string")
    return cast(tuple[str, ...], raw_arguments)


def _safe_environment(additions: Mapping[object, object] | None) -> dict[str, str]:
    environment = {
        name: value for name in _SAFE_INHERITED_ENVIRONMENT if (value := os.environ.get(name))
    }
    if additions is None:
        return environment
    for name, value in additions.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(value, str)
            or "\x00" in name
            or "\x00" in value
            or _CREDENTIAL_NAME.search(name)
            or _contains_credential(value.encode("utf-8"))
        ):
            raise CaptureError("credential-like environment content is prohibited")
        environment[name] = value
    return environment


def _require_clean_revision(root: Path, revision: str) -> str:
    exact_revision = _resolve_revision(root, revision)
    if _resolve_revision(root, "HEAD") != exact_revision:
        raise CaptureError("repository does not have the requested clean Git revision checked out")
    status = _run_checked(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        operation="Git status",
    ).stdout
    if status:
        raise CaptureError(
            "repository must match a clean Git revision without tracked or untracked changes"
        )
    return exact_revision


def _resolve_revision(root: Path, revision: str) -> str:
    if not revision or revision.startswith("-") or "\x00" in revision:
        raise CaptureError("revision: invalid Git revision")
    completed = _run_checked(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=root,
        operation="Git revision lookup",
    )
    resolved = completed.stdout.decode("ascii", errors="strict").strip()
    if not _REVISION.fullmatch(resolved):
        raise CaptureError("revision: Git did not return a full commit hash")
    return resolved


def _git_object(root: Path, revision: str, relative_path: str) -> bytes:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != relative_path:
        raise CaptureError("source path: expected a normalized repository-relative path")
    return _run_checked(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=root,
        operation="Git source lookup",
    ).stdout


def _run_checked(
    args: list[str], *, cwd: Path, operation: str
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError(f"{operation} could not complete") from exc
    if completed.returncode != 0:
        raise CaptureError(f"{operation} failed with exit status {completed.returncode}")
    return completed


def _resolved_directory(path: Path, field: str) -> Path:
    resolved = _safe_resolve(path, field)
    if not resolved.is_dir():
        raise CaptureError(f"{field}: expected an existing directory")
    return resolved


def _safe_resolve(path: Path | None, field: str) -> Path:
    if path is None:
        raise CaptureError(f"{field}: path is required")
    try:
        return path.resolve()
    except OSError as exc:
        raise CaptureError(f"{field}: path resolution failed") from exc


def _require_below(path: Path, root: Path, field: str) -> None:
    if path != root and not path.is_relative_to(root):
        raise CaptureError(f"{field}: path escapes its owned root")


def _owned_relative_path(root: Path, value: str, field: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != value:
        raise CaptureError(f"{field}: expected a normalized relative path")
    resolved = (root / relative).resolve()
    _require_below(resolved, root, field)
    return resolved


def _timestamp(value: datetime | None) -> str:
    timestamp = value if value is not None else datetime.now(tz=UTC)
    if timestamp.tzinfo is None:
        raise CaptureError("captured_at: timezone information is required")
    return timestamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _timestamp_string(value: object, field: str) -> str:
    text = _string(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureError(f"{field}: invalid timestamp") from exc
    if parsed.tzinfo is None or _timestamp(parsed) != text:
        raise CaptureError(f"{field}: expected canonical UTC seconds")
    return text


def _digest(content: bytes | None) -> str:
    if content is None:
        raise CaptureError("hash input is missing")
    return hashlib.sha256(content).hexdigest()


def _contains_credential(content: bytes) -> bool:
    return _CREDENTIAL_OUTPUT.search(content) is not None


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CaptureError(f"{field}: expected an object")
    mapping = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in mapping):
        raise CaptureError(f"{field}: expected an object")
    return cast(dict[str, object], mapping)


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise CaptureError(f"{field}: expected an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CaptureError(f"{field}: expected a non-empty string")
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CaptureError(f"{field}: expected an integer")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CaptureError(f"{field}: expected a number")
    return float(value)


def _hash(value: object, field: str) -> str:
    text = _string(value, field)
    if not _SHA256.fullmatch(text):
        raise CaptureError(f"{field}: expected a lowercase SHA-256")
    return text


def _optional_hash(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _hash(value, field)


def _integer_pair(value: object, field: str) -> tuple[int, int]:
    values = _array(value, field)
    if len(values) != 2:
        raise CaptureError(f"{field}: expected two integers")
    return (_integer(values[0], f"{field}[0]"), _integer(values[1], f"{field}[1]"))


def _integer_tuple(value: object, field: str) -> tuple[int, int, int, int]:
    values = _array(value, field)
    if len(values) != 4:
        raise CaptureError(f"{field}: expected four integers")
    return cast(
        tuple[int, int, int, int],
        tuple(_integer(item, f"{field}[{index}]") for index, item in enumerate(values)),
    )


def _exact_fields(payload: dict[str, object], expected: set[str], field: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise CaptureError(f"{field}: fields differ (missing={missing}, unknown={unknown})")


def _png_dimensions(content: bytes, field: str) -> tuple[int, int]:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise CaptureError(f"{field}: evidence is not a PNG")
    return cast(tuple[int, int], struct.unpack(">II", content[16:24]))


def _hex_color(value: object, field: str) -> str:
    color = _string(value, field)
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise CaptureError(f"{field}: expected #RRGGBB")
    return color.upper()


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _rectangles_overlap(
    first: tuple[int, int, int, int], second: tuple[int, int, int, int]
) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return not (
        first_x + first_width <= second_x
        or second_x + second_width <= first_x
        or first_y + first_height <= second_y
        or second_y + second_height <= first_y
    )
