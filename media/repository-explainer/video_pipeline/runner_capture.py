"""Capture guarded runner evidence from a disposable pinned-revision clone.

Runtime preparation synchronizes the locked operator environment and proves its
console entry point, imported package, Git object, and Codex login before any
clone exists. Capture then invokes only the tracked SessionStart command and the
four fixed runner vectors from the clone root. Every terminal path promotes the
same eight secret-free JSON records before clone cleanup; only complete hook,
runner, post-check, and no-diff proof can select ``accepted``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from .capture import RUNNER_EVIDENCE_NAMES, clean_revision_clone

type CaptureMode = Literal["accepted", "preflight-only"]

HOOK_COMMAND = '"$(git rev-parse --show-toplevel)/.agents/hooks/agent-handoff/session_start.py"'
HOOK_PATH = Path(".agents/hooks/agent-handoff/session_start.py")
HOOK_INPUT = '{"hook_event_name":"SessionStart","source":"startup","cwd":"."}'
RUNNER_SCRIPT = "docs/apseudo-docs/examples/runner/review-spec.apseudo"
SPEC_PATH = "docs/specs/repository-explainer-video.md"
RUN_ROOT = "dist/video/work/runner-runs"
MODULE_SOURCE = "src/apseudo_lint/__init__.py"
ENTRYPOINT_MODULE_SOURCE = "src/apseudo_lint/runner_cli.py"
REQUIRED_EVIDENCE_NAMES = RUNNER_EVIDENCE_NAMES
_CREDENTIAL_NAME = re.compile(
    r"(?i)(?:^|_)(?:api_?key|authorization|credential|password|private_?key|"
    r"secret|token)(?:$|_)"
)
_CREDENTIAL_BYTES = re.compile(
    rb"(?i)(?:authorization|api[_-]?key|access[_-]?token|secret[_-]?key|password)"
    rb"\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
_CREDENTIAL_RAW_KEY = re.compile(
    rb"""(?ix)
    (?:
        ["']
        (?:[a-z0-9]+[_-])*
        (?:api[_-]?key|authorization|credential|password|private[_-]?key|secret|token)
        (?:[_-][a-z0-9]+)*
        ["']
        |
        (?:^|[\s,{])
        (?:[a-z0-9]+[_-])*
        (?:api[_-]?key|authorization|credential|password|private[_-]?key|secret|token)
        (?:[_-][a-z0-9]+)*
    )
    \s*[:=]
    """
)
_FULL_REVISION = re.compile(r"[0-9a-f]{40}")
_VERSION_LINE = re.compile(rb'^__version__\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
_VERSION_NUMBER = re.compile(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?")


class RunnerCaptureError(ValueError):
    """Reject unsafe input or unverifiable runner capture evidence."""


class UnsafeRunnerCaptureError(RunnerCaptureError):
    """Reject credential-bearing input or output without promoting evidence."""


@dataclass(frozen=True, slots=True)
class RunnerRuntime:
    """Locked operator runtime proven against one capture revision."""

    revision: str
    operator_python: Path
    operator_python_sha256: str
    operator_apseudo_run: Path
    console_sha256: str
    console_expected_sha256: str
    console_entrypoint: str
    module_path: Path
    module_sha256: str
    entrypoint_module_path: Path
    entrypoint_module_sha256: str
    toolkit_version: str
    environment_sha256: str
    sync_argv: tuple[str, ...]
    sync_status: int
    provider_status_argv: tuple[str, ...]
    provider_status: int
    precondition_reason: str | None


@dataclass(frozen=True, slots=True)
class RunnerCaptureResult:
    """Promoted guarded-run evidence and the clone cleanup postcondition."""

    mode: CaptureMode
    reason: str
    revision: str
    clone_path: Path
    evidence_root: Path
    evidence_hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    """One subprocess result retained only as secret-screened capture data."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def prepare_runner_runtime(
    repository_root: Path,
    *,
    revision: str,
    operator_python: Path | None = None,
    operator_apseudo_run: Path | None = None,
    environment: Mapping[str, str] | None = None,
    sync_argv: Sequence[str] = ("uv", "sync", "--locked", "--all-groups"),
    provider_status_argv: Sequence[str] = ("codex", "login", "status"),
) -> RunnerRuntime:
    """Synchronize and prove the local operator runtime before cloning.

    The console script is required beside the selected process interpreter.
    Tests may provide a repository-local interpreter shim and fake console
    script, but the same adjacency, revision, module, version, sync, and login
    checks still apply.
    """
    root = _directory(repository_root, "repository_root")
    child_environment = _child_environment(environment)
    exact_revision = _resolve_revision(root, revision)
    _git_object_exists(root, exact_revision)

    selected_python = (
        Path(sys.executable).absolute()
        if operator_python is None
        else _existing_file(operator_python, "operator_python")
    )
    selected_runner = (
        selected_python.parent / "apseudo-run"
        if operator_apseudo_run is None
        else _existing_file(operator_apseudo_run, "operator_apseudo_run")
    )
    selected_python = _existing_file(selected_python, "operator_python")
    selected_runner = _existing_file(selected_runner, "operator_apseudo_run")
    if selected_runner.parent != selected_python.parent:
        raise RunnerCaptureError(
            "operator_apseudo_run: must be beside the selected operator interpreter"
        )
    if not os.access(selected_runner, os.X_OK):
        raise RunnerCaptureError("operator_apseudo_run: console script is not executable")
    console_interpreter = _verify_console_shebang(selected_runner, selected_python)
    console_entrypoint = _verify_console_entrypoint(
        selected_runner,
        _git_show(root, exact_revision, "pyproject.toml"),
        console_interpreter,
    )
    expected_console = expected_console_wrapper_bytes(
        console_interpreter,
        console_entrypoint,
    )

    sync_command = _argument_vector(sync_argv, "sync_argv")
    sync = _run(
        sync_command,
        cwd=root,
        environment=child_environment,
        timeout=300,
        operation="locked environment sync",
    )
    precondition_reason = (
        f"locked environment sync exited {sync.returncode}; expected 0"
        if sync.returncode != 0
        else None
    )

    provider_command = _argument_vector(provider_status_argv, "provider_status_argv")
    provider = _run(
        provider_command,
        cwd=root,
        environment=child_environment,
        timeout=30,
        operation="Codex login status",
    )
    if provider.returncode != 0 and precondition_reason is None:
        precondition_reason = (
            f"Codex login status exited {provider.returncode}; configured login is required"
        )
    if (
        provider.returncode == 0
        and "logged in" not in f"{provider.stdout}\n{provider.stderr}".casefold()
        and precondition_reason is None
    ):
        precondition_reason = "Codex login status did not confirm a configured login"

    (
        module_path,
        module_sha256,
        entrypoint_module_path,
        entrypoint_module_sha256,
        toolkit_version,
    ) = _operator_module_identity(
        selected_python,
        cwd=root,
        environment=child_environment,
    )

    pinned_module = _git_show(root, exact_revision, MODULE_SOURCE)
    if _digest(pinned_module) != module_sha256:
        raise RunnerCaptureError("operator module hash does not match the exact capture revision")
    pinned_entrypoint_module = _git_show(root, exact_revision, ENTRYPOINT_MODULE_SOURCE)
    if _digest(pinned_entrypoint_module) != entrypoint_module_sha256:
        raise RunnerCaptureError(
            "operator entrypoint module hash does not match the exact capture revision"
        )
    version_match = _VERSION_LINE.search(pinned_module)
    if version_match is None or version_match.group(1).decode("utf-8") != toolkit_version:
        raise RunnerCaptureError(
            "operator toolkit version does not match the exact capture revision"
        )

    return RunnerRuntime(
        revision=exact_revision,
        operator_python=selected_python,
        operator_python_sha256=_digest(selected_python.read_bytes()),
        operator_apseudo_run=selected_runner,
        console_sha256=_digest(selected_runner.read_bytes()),
        console_expected_sha256=_digest(expected_console),
        console_entrypoint=console_entrypoint,
        module_path=module_path,
        module_sha256=module_sha256,
        entrypoint_module_path=entrypoint_module_path,
        entrypoint_module_sha256=entrypoint_module_sha256,
        toolkit_version=toolkit_version,
        environment_sha256=_environment_digest(child_environment),
        sync_argv=sync_command,
        sync_status=sync.returncode,
        provider_status_argv=provider_command,
        provider_status=provider.returncode,
        precondition_reason=precondition_reason,
    )


def prepare_and_capture_guarded_runner(
    repository_root: Path,
    *,
    revision: str,
    evidence_root: Path,
    operator_python: Path | None = None,
    operator_apseudo_run: Path | None = None,
    environment: Mapping[str, str] | None = None,
    sync_argv: Sequence[str] = ("uv", "sync", "--locked", "--all-groups"),
    provider_status_argv: Sequence[str] = ("codex", "login", "status"),
) -> RunnerCaptureResult:
    """Prepare and capture, recording safe operational preparation failures."""
    try:
        runtime = prepare_runner_runtime(
            repository_root,
            revision=revision,
            operator_python=operator_python,
            operator_apseudo_run=operator_apseudo_run,
            environment=environment,
            sync_argv=sync_argv,
            provider_status_argv=provider_status_argv,
        )
    except UnsafeRunnerCaptureError:
        raise
    except RunnerCaptureError as exc:
        return _capture_preparation_failure(
            repository_root,
            revision=revision,
            evidence_root=evidence_root,
            operator_python=operator_python,
            operator_apseudo_run=operator_apseudo_run,
            sync_argv=sync_argv,
            provider_status_argv=provider_status_argv,
            reason=str(exc),
        )
    return capture_guarded_runner(
        repository_root,
        revision=revision,
        runtime=runtime,
        evidence_root=evidence_root,
        environment=environment,
    )


def _capture_preparation_failure(
    repository_root: Path,
    *,
    revision: str,
    evidence_root: Path,
    operator_python: Path | None,
    operator_apseudo_run: Path | None,
    sync_argv: Sequence[str],
    provider_status_argv: Sequence[str],
    reason: str,
) -> RunnerCaptureResult:
    root = _safe_path(repository_root, "repository_root")
    destination = _safe_path(evidence_root, "evidence_root")
    destination.mkdir(parents=True, exist_ok=True)
    if destination.is_relative_to(root / "dist" / "video" / "work"):
        raise RunnerCaptureError("evidence_root: promoted evidence must survive work-root cleanup")
    selected_python = (
        Path(sys.executable).absolute()
        if operator_python is None
        else operator_python.expanduser().absolute()
    )
    selected_runner = (
        selected_python.parent / "apseudo-run"
        if operator_apseudo_run is None
        else operator_apseudo_run.expanduser().absolute()
    )
    command_record = _preparation_failure_command_record(
        revision=revision,
        operator_python=selected_python,
        operator_apseudo_run=selected_runner,
        sync_argv=tuple(sync_argv),
        provider_status_argv=tuple(provider_status_argv),
        reason=reason,
    )
    bundle = _terminal_bundle(
        revision=revision,
        hook_record=_skipped_hook_record(reason),
        command_record=command_record,
        runner_artifacts=_skipped_runner_artifacts(reason),
        mode="preflight-only",
        reason=reason,
    )
    hashes = _promote_checked_bundle(destination, bundle)
    clone_path = Path(tempfile.mkdtemp(prefix="apseudo-runner-preparation-"))
    clone_path.rmdir()
    return RunnerCaptureResult(
        mode="preflight-only",
        reason=reason,
        revision=revision,
        clone_path=clone_path,
        evidence_root=destination,
        evidence_hashes=hashes,
    )


def _preparation_failure_command_record(
    *,
    revision: str,
    operator_python: Path,
    operator_apseudo_run: Path,
    sync_argv: tuple[str, ...],
    provider_status_argv: tuple[str, ...],
    reason: str,
) -> dict[str, object]:
    post_check = shlex.join((os.fspath(operator_python), "-m", "apseudo_lint.cli", RUNNER_SCRIPT))
    base_argv = (
        os.fspath(operator_apseudo_run),
        "--agent",
        "codex",
        "--workspace",
        ".",
        "--sandbox",
        "read-only",
        "--require-no-diff",
        "--post-check",
        post_check,
        "--run-dir",
        RUN_ROOT,
        "--set",
        f"spec_path={SPEC_PATH}",
        RUNNER_SCRIPT,
    )
    vectors = {
        "check": _insert_action(base_argv, "--check"),
        "render-prompt": _insert_action(base_argv, "--render-prompt"),
        "print-command": _insert_action(base_argv, "--print-command"),
        "execute": base_argv,
    }
    return {
        "revision": revision,
        "cwd": ".",
        "runtime": {
            "operator_python": os.fspath(operator_python),
            "operator_python_sha256": None,
            "operator_apseudo_run": os.fspath(operator_apseudo_run),
            "console_sha256": None,
            "console_expected_sha256": None,
            "console_entrypoint": None,
            "module_path": None,
            "module_sha256": None,
            "entrypoint_module_path": None,
            "entrypoint_module_sha256": None,
            "toolkit_version": None,
            "environment_sha256": None,
            "sync_argv": list(sync_argv),
            "sync_status": None,
            "provider_status_argv": list(provider_status_argv),
            "provider_status": None,
            "precondition_reason": reason,
        },
        "post_check": post_check,
        "base_argv": list(base_argv),
        "vectors": [
            {
                "action": action,
                "argv": list(vector),
                "status": "skipped",
                "reason": reason,
            }
            for action, vector in vectors.items()
        ],
        "prompt_assertions": {
            "no_hooks_requested: False": False,
            "hooks_required: False": False,
        },
        "rendered_prompt": None,
        "resolved_provider_vector": None,
        "display": {
            "aliases": {
                "apseudo-run": [os.fspath(operator_apseudo_run)],
                "apseudo-lint": [
                    os.fspath(operator_python),
                    "-m",
                    "apseudo_lint.cli",
                ],
            },
            "command": None,
        },
    }


def capture_guarded_runner(
    repository_root: Path,
    *,
    revision: str,
    runtime: RunnerRuntime,
    evidence_root: Path,
    environment: Mapping[str, str] | None = None,
) -> RunnerCaptureResult:
    """Capture hook and runner proof, promoting a truthful terminal record.

    Operational guard failures select ``preflight-only``. Unsafe input, output,
    or promoted bytes raise ``RunnerCaptureError`` and promote nothing.
    """
    root = _directory(repository_root, "repository_root")
    exact_revision = _resolve_revision(root, revision)
    child_environment = _child_environment(environment)
    destination = _safe_path(evidence_root, "evidence_root")
    destination.mkdir(parents=True, exist_ok=True)
    if destination.is_relative_to(root / "dist" / "video" / "work"):
        raise RunnerCaptureError("evidence_root: promoted evidence must survive work-root cleanup")

    post_check_argv = (
        os.fspath(runtime.operator_python),
        "-m",
        "apseudo_lint.cli",
        RUNNER_SCRIPT,
    )
    post_check = shlex.join(post_check_argv)
    base_argv = (
        os.fspath(runtime.operator_apseudo_run),
        "--agent",
        "codex",
        "--workspace",
        ".",
        "--sandbox",
        "read-only",
        "--require-no-diff",
        "--post-check",
        post_check,
        "--run-dir",
        RUN_ROOT,
        "--set",
        f"spec_path={SPEC_PATH}",
        RUNNER_SCRIPT,
    )
    vectors = {
        "check": _insert_action(base_argv, "--check"),
        "render-prompt": _insert_action(base_argv, "--render-prompt"),
        "print-command": _insert_action(base_argv, "--print-command"),
        "execute": base_argv,
    }
    command_record = _runner_command_record(runtime, base_argv, post_check, vectors)

    precondition_reason = _runtime_precondition_reason(runtime, exact_revision)
    if precondition_reason is not None:
        clone_path = Path(tempfile.mkdtemp(prefix="apseudo-runner-precondition-"))
        clone_path.rmdir()
        runner_artifacts = _skipped_runner_artifacts(precondition_reason)
        bundle = _terminal_bundle(
            revision=exact_revision,
            hook_record=_skipped_hook_record(precondition_reason),
            command_record=command_record,
            runner_artifacts=runner_artifacts,
            mode="preflight-only",
            reason=precondition_reason,
        )
        evidence_hashes = _promote_checked_bundle(destination, bundle)
        return RunnerCaptureResult(
            mode="preflight-only",
            reason=precondition_reason,
            revision=exact_revision,
            clone_path=clone_path,
            evidence_root=destination,
            evidence_hashes=evidence_hashes,
        )

    clone_path: Path
    with clean_revision_clone(root, revision=exact_revision) as clone:
        clone_path = clone
        hook_record, hook_reason = _capture_hook(clone, child_environment)
        runner_artifacts = _skipped_runner_artifacts("runner skipped because hook preflight failed")
        mode: CaptureMode = "preflight-only"
        reason = hook_reason or "guarded runner capture passed"

        if hook_reason is None:
            integrity_reason = _runtime_integrity_reason(
                root,
                exact_revision,
                runtime,
                child_environment,
            )
            if integrity_reason is not None:
                reason = integrity_reason
                runner_artifacts = _skipped_runner_artifacts(integrity_reason)
            else:
                runner_artifacts, runner_reason = _capture_runner(
                    clone,
                    child_environment,
                    command_record,
                    vectors,
                    post_check,
                    runtime,
                    exact_revision,
                )
                reason = runner_reason or "guarded runner capture passed"
                if runner_reason is None:
                    mode = "accepted"

        bundle = _terminal_bundle(
            revision=exact_revision,
            hook_record=hook_record,
            command_record=command_record,
            runner_artifacts=runner_artifacts,
            mode=mode,
            reason=reason,
        )
        evidence_hashes = _promote_checked_bundle(destination, bundle)

    if clone_path.exists():
        raise RunnerCaptureError("disposable clone still exists after capture")
    return RunnerCaptureResult(
        mode=mode,
        reason=reason,
        revision=exact_revision,
        clone_path=clone_path,
        evidence_root=destination,
        evidence_hashes=evidence_hashes,
    )


def _runtime_precondition_reason(
    runtime: RunnerRuntime,
    exact_revision: str,
) -> str | None:
    if runtime.revision != exact_revision:
        return "runtime revision does not match the requested capture revision"
    if runtime.precondition_reason is not None:
        return runtime.precondition_reason
    if runtime.sync_status != 0:
        return f"locked environment sync exited {runtime.sync_status}; expected 0"
    if runtime.provider_status != 0:
        return f"Codex login status exited {runtime.provider_status}; configured login is required"
    return None


def _runtime_integrity_reason(
    repository: Path,
    exact_revision: str,
    runtime: RunnerRuntime,
    environment: Mapping[str, str],
) -> str | None:
    """Revalidate every executable runtime byte immediately before runner calls."""
    if _environment_digest(environment) != runtime.environment_sha256:
        return "operator environment changed after runtime preparation"
    try:
        if _digest(runtime.operator_python.read_bytes()) != runtime.operator_python_sha256:
            return "operator interpreter changed after runtime preparation"
    except OSError:
        return "operator interpreter became unavailable after runtime preparation"

    try:
        console_interpreter = _verify_console_shebang(
            runtime.operator_apseudo_run,
            runtime.operator_python,
        )
        pinned_entrypoint = _pinned_console_entrypoint(
            _git_show(repository, exact_revision, "pyproject.toml")
        )
        expected_console = expected_console_wrapper_bytes(
            console_interpreter,
            pinned_entrypoint,
        )
        observed_console = runtime.operator_apseudo_run.read_bytes()
    except OSError, RunnerCaptureError:
        return "operator console wrapper became unverifiable after runtime preparation"
    if (
        runtime.console_entrypoint != pinned_entrypoint
        or _digest(expected_console) != runtime.console_expected_sha256
        or observed_console != expected_console
        or _digest(observed_console) != runtime.console_sha256
    ):
        return "operator console wrapper changed after runtime preparation"

    try:
        (
            module_path,
            module_sha256,
            entrypoint_module_path,
            entrypoint_module_sha256,
            toolkit_version,
        ) = _operator_module_identity(
            runtime.operator_python,
            cwd=repository,
            environment=environment,
        )
        pinned_module_sha256 = _digest(_git_show(repository, exact_revision, MODULE_SOURCE))
        pinned_entrypoint_module_sha256 = _digest(
            _git_show(repository, exact_revision, ENTRYPOINT_MODULE_SOURCE)
        )
    except UnsafeRunnerCaptureError:
        raise
    except RunnerCaptureError:
        return "operator module became unavailable after runtime preparation"
    if module_path != runtime.module_path or (
        runtime.module_sha256 != pinned_module_sha256
        or module_sha256 != runtime.module_sha256
        or toolkit_version != runtime.toolkit_version
    ):
        return "operator module changed after runtime preparation"
    if entrypoint_module_path != runtime.entrypoint_module_path or (
        runtime.entrypoint_module_sha256 != pinned_entrypoint_module_sha256
        or entrypoint_module_sha256 != runtime.entrypoint_module_sha256
    ):
        return "operator entrypoint module changed after runtime preparation"
    return None


def _operator_module_identity(
    operator_python: Path,
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> tuple[Path, str, Path, str, str]:
    identity_code = (
        "import hashlib,json,pathlib,apseudo_lint,apseudo_lint.runner_cli as runner_cli;"
        "p=pathlib.Path(apseudo_lint.__file__).resolve();"
        "r=pathlib.Path(runner_cli.__file__).resolve();"
        "print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),"
        "'entrypoint_path':str(r),"
        "'entrypoint_sha256':hashlib.sha256(r.read_bytes()).hexdigest(),"
        "'version':apseudo_lint.__version__},sort_keys=True))"
    )
    identity = _run(
        (os.fspath(operator_python), "-c", identity_code),
        cwd=cwd,
        environment=environment,
        timeout=30,
        operation="operator module identity",
    )
    if identity.returncode != 0:
        raise RunnerCaptureError("operator module identity could not be resolved")
    try:
        payload = cast(dict[str, object], json.loads(identity.stdout))
        module_path = _existing_file(
            Path(_string(payload.get("path"), "operator module path")),
            "operator module path",
        )
        module_sha256 = _hash_string(payload.get("sha256"), "operator module sha256")
        entrypoint_path = _existing_file(
            Path(_string(payload.get("entrypoint_path"), "operator entrypoint module path")),
            "operator entrypoint module path",
        )
        entrypoint_sha256 = _hash_string(
            payload.get("entrypoint_sha256"),
            "operator entrypoint module sha256",
        )
        toolkit_version = _string(payload.get("version"), "operator toolkit version")
    except (json.JSONDecodeError, TypeError) as exc:
        raise RunnerCaptureError("operator module identity returned invalid JSON") from exc
    return (
        module_path,
        module_sha256,
        entrypoint_path,
        entrypoint_sha256,
        toolkit_version,
    )


def _environment_digest(environment: Mapping[str, str]) -> str:
    encoded = json.dumps(
        sorted(environment.items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return _digest(encoded)


def _skipped_hook_record(reason: str) -> dict[str, object]:
    return {
        "config_path": ".codex/config.toml",
        "config_command": None,
        "configured_hook_path": HOOK_PATH.as_posix(),
        "configured_hook_mode": None,
        "cwd": ".",
        "input": HOOK_INPUT,
        "shell_argv": ["/bin/bash", "-lc", HOOK_COMMAND],
        "state_sha256": None,
        "status": "skipped",
        "reason": f"hook skipped because runtime precondition failed: {reason}",
    }


def _terminal_bundle(
    *,
    revision: str,
    hook_record: dict[str, object],
    command_record: dict[str, object],
    runner_artifacts: dict[str, object],
    mode: CaptureMode,
    reason: str,
) -> dict[str, object]:
    outcome_value = _object_copy(runner_artifacts["outcome.json"])
    outcome_value.update(
        {
            "accepted": mode == "accepted",
            "mode": mode,
            "reason": reason,
            "revision": revision,
        }
    )
    runner_artifacts["outcome.json"] = outcome_value
    return {
        "hook-preflight.json": hook_record,
        "runner-commands.json": command_record,
        **runner_artifacts,
    }


def _promote_checked_bundle(
    evidence_root: Path,
    bundle: Mapping[str, object],
) -> dict[str, str]:
    _require_exact_bundle(bundle)
    _scan_bundle(bundle)
    evidence_hashes = _promote_bundle(evidence_root, bundle)
    _verify_promoted_bundle(evidence_root, evidence_hashes)
    return evidence_hashes


def expand_display_command(display_command: str, aliases: Mapping[str, object]) -> tuple[str, ...]:
    """Expand only the two approved display aliases to their recorded paths."""
    try:
        argv = shlex.split(display_command)
    except ValueError as exc:
        raise RunnerCaptureError("display command is not valid shell-token text") from exc
    if not argv or argv[0] != "apseudo-run":
        raise RunnerCaptureError("display command must begin with the apseudo-run alias")
    runner_exact = _alias_tokens(aliases, "apseudo-run")
    linter_exact = _alias_tokens(aliases, "apseudo-lint")
    if len(runner_exact) != 1 or len(linter_exact) != 3:
        raise RunnerCaptureError("display aliases have unexpected expansion widths")
    argv[:1] = runner_exact
    try:
        post_index = argv.index("--post-check") + 1
        post_argv = shlex.split(argv[post_index])
    except (ValueError, IndexError) as exc:
        raise RunnerCaptureError("display command is missing a valid --post-check") from exc
    if not post_argv or post_argv[0] != "apseudo-lint":
        raise RunnerCaptureError("display post-check must begin with the apseudo-lint alias")
    argv[post_index] = shlex.join([*linter_exact, *post_argv[1:]])
    return tuple(argv)


def expected_console_wrapper_bytes(interpreter: Path, entrypoint: str) -> bytes:
    """Render the exact uv console wrapper for one pinned Python entry point."""
    try:
        module_name, function_name = entrypoint.split(":", maxsplit=1)
    except ValueError as exc:
        raise RunnerCaptureError("operator console entry point is invalid") from exc
    if (
        not interpreter.is_absolute()
        or not all(part.isidentifier() for part in module_name.split("."))
        or not function_name.isidentifier()
    ):
        raise RunnerCaptureError("operator console entry point is invalid")
    return (
        f"#!{interpreter}\n"
        "# -*- coding: utf-8 -*-\n"
        "import sys\n"
        f"from {module_name} import {function_name}\n"
        'if __name__ == "__main__":\n'
        '    if sys.argv[0].endswith("-script.pyw"):\n'
        "        sys.argv[0] = sys.argv[0][:-11]\n"
        '    elif sys.argv[0].endswith(".exe"):\n'
        "        sys.argv[0] = sys.argv[0][:-4]\n"
        f"    sys.exit({function_name}())\n"
    ).encode()


def _capture_hook(
    clone: Path, environment: Mapping[str, str]
) -> tuple[dict[str, object], str | None]:
    config_path = clone / ".codex/config.toml"
    state_path = clone / "docs/handoff/state.md"
    base: dict[str, object] = {
        "config_path": ".codex/config.toml",
        "config_command": None,
        "configured_hook_path": HOOK_PATH.as_posix(),
        "configured_hook_mode": None,
        "cwd": ".",
        "input": HOOK_INPUT,
        "shell_argv": ["/bin/bash", "-lc", HOOK_COMMAND],
        "state_sha256": _digest(state_path.read_bytes()) if state_path.is_file() else None,
        "status": "failed",
    }
    try:
        command = _session_start_command(config_path)
    except (OSError, tomllib.TOMLDecodeError, RunnerCaptureError) as exc:
        reason = f"configured SessionStart hook unavailable: {exc}"
        base["reason"] = reason
        return base, reason
    base["config_command"] = command
    if command != HOOK_COMMAND:
        reason = "configured SessionStart command changed"
        base["reason"] = reason
        return base, reason

    hook = clone / HOOK_PATH
    try:
        metadata = hook.lstat()
    except OSError:
        reason = "configured SessionStart hook executable is missing"
        base["reason"] = reason
        return base, reason
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        reason = "configured SessionStart hook must be a regular non-symlink file"
        base["reason"] = reason
        return base, reason
    base["configured_hook_mode"] = oct(stat.S_IMODE(metadata.st_mode))
    if not os.access(hook, os.X_OK):
        reason = "configured SessionStart hook is not executable"
        base["reason"] = reason
        return base, reason

    try:
        interpreter = _hook_interpreter(hook, clone, environment)
    except UnsafeRunnerCaptureError:
        raise
    except RunnerCaptureError as exc:
        reason = str(exc)
        base["reason"] = reason
        return base, reason
    base["interpreter"] = interpreter

    hook_environment = dict(environment)
    hook_environment.pop("CLAUDE_PROJECT_DIR", None)
    result = _run(
        ("/bin/bash", "-lc", command),
        cwd=clone,
        environment=hook_environment,
        input_text=HOOK_INPUT,
        timeout=15,
        operation="SessionStart hook preflight",
    )
    base.update(
        {
            "exit_status": result.returncode,
            "stdout_sha256": _digest(result.stdout.encode("utf-8")),
            "stderr_sha256": _digest(result.stderr.encode("utf-8")),
            "output_sha256": _digest((result.stdout + result.stderr).encode("utf-8")),
        }
    )
    if result.returncode != 0:
        reason = f"configured hook exited {result.returncode}; expected 0"
        base["reason"] = reason
        return base, reason

    output = result.stdout
    if "session_start.py failed:" in output:
        reason = "configured hook emitted a degraded diagnostic"
        base["reason"] = reason
        return base, reason
    if re.search(r"(?i)\b(?:placeholder|unavailable)\b", output):
        reason = "configured hook emitted placeholder or unavailable content"
        base["reason"] = reason
        return base, reason
    branch = _git(clone, "rev-parse", "--abbrev-ref", "HEAD")
    short_commit = _git(clone, "rev-parse", "--short", "HEAD")
    focus_bullet = _first_current_focus_bullet(state_path)
    assertions = {
        "session_context": output.count("<session_context>") == 1
        and output.count("</session_context>") == 1,
        "branch": output.count(f"Branch: {branch}") == 1,
        "current_focus_bullet": output.count(focus_bullet) == 1,
        "short_commit": len(re.findall(rf"(?m)^{re.escape(short_commit)}(?:\s|$)", output)) == 1,
    }
    base["assertions"] = assertions
    base["branch"] = branch
    base["current_focus_bullet"] = focus_bullet
    base["short_commit"] = short_commit
    if not all(assertions.values()):
        reason = "configured hook output failed substantive assertions"
        base["reason"] = reason
        return base, reason
    base["status"] = "passed"
    base["reason"] = "configured SessionStart hook passed"
    return base, None


def _runner_command_record(
    runtime: RunnerRuntime,
    base_argv: tuple[str, ...],
    post_check: str,
    vectors: Mapping[str, tuple[str, ...]],
) -> dict[str, object]:
    aliases: dict[str, object] = {
        "apseudo-run": [os.fspath(runtime.operator_apseudo_run)],
        "apseudo-lint": [
            os.fspath(runtime.operator_python),
            "-m",
            "apseudo_lint.cli",
        ],
    }
    display_argv = list(base_argv)
    display_argv[0] = "apseudo-run"
    post_index = display_argv.index("--post-check") + 1
    parsed_post = shlex.split(display_argv[post_index])
    expected_prefix = [
        os.fspath(runtime.operator_python),
        "-m",
        "apseudo_lint.cli",
    ]
    if parsed_post[:3] != expected_prefix:
        raise RunnerCaptureError("recorded post-check prefix changed")
    display_argv[post_index] = shlex.join(["apseudo-lint", *parsed_post[3:]])
    display_command = shlex.join(display_argv)
    if any(
        absolute in display_command
        for absolute in (
            os.fspath(runtime.operator_python),
            os.fspath(runtime.operator_apseudo_run),
        )
    ):
        raise RunnerCaptureError("display command contains an absolute operator path")
    if expand_display_command(display_command, aliases) != base_argv:
        raise RunnerCaptureError("display alias expansion does not equal the recorded argv")
    return {
        "revision": runtime.revision,
        "cwd": ".",
        "runtime": {
            "operator_python": os.fspath(runtime.operator_python),
            "operator_python_sha256": runtime.operator_python_sha256,
            "operator_apseudo_run": os.fspath(runtime.operator_apseudo_run),
            "console_sha256": runtime.console_sha256,
            "console_expected_sha256": runtime.console_expected_sha256,
            "console_entrypoint": runtime.console_entrypoint,
            "module_path": os.fspath(runtime.module_path),
            "module_sha256": runtime.module_sha256,
            "entrypoint_module_path": os.fspath(runtime.entrypoint_module_path),
            "entrypoint_module_sha256": runtime.entrypoint_module_sha256,
            "toolkit_version": runtime.toolkit_version,
            "environment_sha256": runtime.environment_sha256,
            "sync_argv": list(runtime.sync_argv),
            "sync_status": runtime.sync_status,
            "provider_status_argv": list(runtime.provider_status_argv),
            "provider_status": runtime.provider_status,
            "precondition_reason": runtime.precondition_reason,
        },
        "post_check": post_check,
        "base_argv": list(base_argv),
        "vectors": [
            {"action": action, "argv": list(vector), "status": "planned"}
            for action, vector in vectors.items()
        ],
        "prompt_assertions": {
            "no_hooks_requested: False": False,
            "hooks_required: False": False,
        },
        "rendered_prompt": None,
        "resolved_provider_vector": None,
        "display": {"aliases": aliases, "command": display_command},
    }


def _capture_runner(
    clone: Path,
    environment: Mapping[str, str],
    command_record: dict[str, object],
    vectors: Mapping[str, tuple[str, ...]],
    post_check: str,
    runtime: RunnerRuntime,
    exact_revision: str,
) -> tuple[dict[str, object], str | None]:
    vector_records = cast(list[dict[str, object]], command_record["vectors"])
    results: dict[str, _ProcessResult] = {}
    preflight_reason: str | None = None
    for index, action in enumerate(("check", "render-prompt", "print-command")):
        integrity_reason = _runtime_integrity_reason(
            clone,
            exact_revision,
            runtime,
            environment,
        )
        if integrity_reason is not None:
            for skipped in vector_records[index:]:
                skipped["status"] = "skipped"
                skipped["reason"] = integrity_reason
            return _skipped_runner_artifacts(integrity_reason), integrity_reason
        result = _run(
            vectors[action],
            cwd=clone,
            environment=environment,
            timeout=120,
            operation=f"runner {action}",
        )
        results[action] = result
        vector_records[index].update(_process_record(result))
        if result.returncode != 0 and preflight_reason is None:
            preflight_reason = f"runner {action} exited {result.returncode}; expected 0"

    prompt = results["render-prompt"].stdout
    command_record["rendered_prompt"] = prompt
    prompt_assertions = cast(dict[str, object], command_record["prompt_assertions"])
    for substring in tuple(prompt_assertions):
        prompt_assertions[substring] = prompt.count(substring) == 1
    if not all(cast(bool, value) for value in prompt_assertions.values()):
        preflight_reason = preflight_reason or "rendered prompt hook flags changed"

    try:
        printed_lines = [
            line for line in results["print-command"].stdout.splitlines() if line.strip()
        ]
        provider_vector = shlex.split(printed_lines[0])
    except IndexError, ValueError:
        provider_vector = []
    command_record["resolved_provider_vector"] = provider_vector
    if not provider_vector or provider_vector[0] != "codex":
        preflight_reason = preflight_reason or "resolved Codex provider vector is absent"

    if preflight_reason is not None:
        vector_records[3]["status"] = "skipped"
        vector_records[3]["reason"] = preflight_reason
        return _skipped_runner_artifacts(preflight_reason), preflight_reason

    integrity_reason = _runtime_integrity_reason(
        clone,
        exact_revision,
        runtime,
        environment,
    )
    if integrity_reason is not None:
        vector_records[3]["status"] = "skipped"
        vector_records[3]["reason"] = integrity_reason
        return _skipped_runner_artifacts(integrity_reason), integrity_reason

    execution = _run(
        vectors["execute"],
        cwd=clone,
        environment=environment,
        timeout=600,
        operation="runner execution",
    )
    vector_records[3].update(_process_record(execution))
    if execution.returncode != 0:
        diagnostic = _process_diagnostic(execution)
        reason = f"runner execution exited {execution.returncode}; expected 0"
        if diagnostic:
            reason = f"{reason}: {diagnostic}"
    else:
        reason = None

    run_records = sorted(path for path in (clone / RUN_ROOT).glob("*") if path.is_dir())
    if len(run_records) != 1:
        record_reason = f"runner produced {len(run_records)} run records; expected 1"
        return _skipped_runner_artifacts(record_reason), reason or record_reason
    run_record = run_records[0]
    _scan_record_directory(run_record)
    artifacts, artifact_reason = _load_runner_artifacts(run_record)
    reason = reason or artifact_reason

    run_manifest = _object_copy(artifacts["run-manifest.json"])
    run_manifest["capture_revision"] = _git(clone, "rev-parse", "HEAD")
    artifacts["run-manifest.json"] = run_manifest
    agent_command = _object_copy(artifacts["agent-command.json"])
    resolved_execution_vector = agent_command.get("argv")
    if not isinstance(resolved_execution_vector, list) or not resolved_execution_vector:
        reason = reason or "runner agent command did not record a provider vector"
    else:
        command_record["resolved_execution_provider_vector"] = resolved_execution_vector

    try:
        post_checks = _array(artifacts["post-checks.json"], "post-checks.json")
    except RunnerCaptureError:
        post_checks = []
    if len(post_checks) != 1:
        reason = reason or "runner post-check record is missing or ambiguous"
    else:
        post_record = _object_copy(post_checks[0])
        if (
            post_record.get("command") != post_check
            or post_record.get("returncode") != 0
            or post_record.get("passed") is not True
        ):
            # A semantic Blocked exit caused by this record is less specific
            # than the deterministic post-check failure that produced it.
            reason = "runner post-check failed"

    validation = artifacts["validation-before.json"]
    if not validation_record_passed(validation):
        reason = reason or "runner validation-before record failed"
    outcome = artifacts["outcome.json"]
    try:
        outcome_record = _object_copy(outcome)
    except RunnerCaptureError:
        outcome_record = {}
    if outcome_record.get("outcome") != "Accepted":
        reason = reason or "runner outcome was not Accepted"

    changed_files = _git_changed_files(clone)
    clean = not changed_files
    artifacts["changed-files.json"] = {
        "clean": clean,
        "files": changed_files,
        "no_diff": clean,
    }
    if not clean:
        reason = reason or "runner workspace changed despite --require-no-diff"
    return artifacts, reason


def _load_runner_artifacts(run_record: Path) -> tuple[dict[str, object], str | None]:
    source_names = {
        "run-manifest.json": "manifest.json",
        "agent-command.json": "agent-command.json",
        "validation-before.json": "validation-before.json",
        "post-checks.json": "post-checks.json",
        "outcome.json": "outcome.json",
    }
    artifacts = _skipped_runner_artifacts("runner record is incomplete")
    unavailable: list[str] = []
    for promoted_name, source_name in source_names.items():
        source = run_record / source_name
        try:
            artifacts[promoted_name] = cast(object, json.loads(source.read_text(encoding="utf-8")))
        except OSError, UnicodeDecodeError, json.JSONDecodeError:
            unavailable.append(source_name)
    artifacts["changed-files.json"] = {
        "clean": False,
        "files": [],
        "no_diff": False,
    }
    if unavailable:
        return artifacts, f"runner record missing or invalid: {', '.join(unavailable)}"
    return artifacts, None


def _skipped_runner_artifacts(reason: str) -> dict[str, object]:
    skipped = {"status": "skipped", "reason": reason}
    return {
        "run-manifest.json": dict(skipped),
        "agent-command.json": dict(skipped),
        "validation-before.json": dict(skipped),
        "post-checks.json": [],
        "changed-files.json": {
            "clean": False,
            "files": [],
            "no_diff": False,
            "reason": reason,
        },
        "outcome.json": {
            "outcome": "Blocked",
            "summary": "Guarded runner capture did not reach accepted execution.",
            "checks_run": [],
            "artifacts": [],
        },
    }


def _session_start_command(config_path: Path) -> str:
    payload = _object_copy(cast(object, tomllib.loads(config_path.read_text(encoding="utf-8"))))
    hooks = payload.get("hooks")
    hooks_record = _object_copy(hooks)
    session_entries = _array(hooks_record.get("SessionStart"), "hooks.SessionStart")
    if len(session_entries) != 1:
        raise RunnerCaptureError("exactly one hooks.SessionStart entry is required")
    session = _object_copy(session_entries[0])
    commands = _array(session.get("hooks"), "hooks.SessionStart.hooks")
    if len(commands) != 1:
        raise RunnerCaptureError("exactly one SessionStart hook command is required")
    command_entry = _object_copy(commands[0])
    if command_entry.get("type") != "command" or not isinstance(command_entry.get("command"), str):
        raise RunnerCaptureError("SessionStart hook is not a command entry")
    return cast(str, command_entry["command"])


def _hook_interpreter(hook: Path, cwd: Path, environment: Mapping[str, str]) -> dict[str, object]:
    try:
        first_line = hook.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError) as exc:
        raise RunnerCaptureError("configured hook shebang is unreadable") from exc
    if not first_line.startswith("#!"):
        raise RunnerCaptureError("configured hook has no shebang")
    try:
        tokens = shlex.split(first_line[2:])
    except ValueError as exc:
        raise RunnerCaptureError("configured hook shebang is invalid") from exc
    if not tokens:
        raise RunnerCaptureError("configured hook shebang is empty")
    if tokens[0] == "/usr/bin/env":
        if len(tokens) != 2:
            raise RunnerCaptureError("configured hook env shebang must name only python3")
        resolved = shutil.which(tokens[1], path=environment.get("PATH"))
        if resolved is None:
            raise RunnerCaptureError("configured hook python3 interpreter is unavailable")
        interpreter = Path(resolved)
    else:
        if len(tokens) != 1:
            raise RunnerCaptureError("configured hook shebang contains unsupported arguments")
        interpreter = Path(tokens[0])
    version_result = _run(
        (os.fspath(interpreter), "--version"),
        cwd=cwd,
        environment=environment,
        timeout=10,
        operation="hook interpreter version",
    )
    if version_result.returncode != 0:
        raise RunnerCaptureError("configured hook interpreter version probe failed")
    rendered_version = (version_result.stdout or version_result.stderr).strip()
    match = _VERSION_NUMBER.fullmatch(rendered_version)
    if match is None:
        raise RunnerCaptureError("configured hook interpreter version is unrecognized")
    version_info = [int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)]
    if tuple(version_info[:2]) < (3, 14):
        raise RunnerCaptureError("configured hook requires Python 3.14 or newer")
    return {
        "shebang": first_line[2:],
        "resolved_path": os.fspath(interpreter.resolve()),
        "version": rendered_version,
        "version_info": version_info,
    }


def _first_current_focus_bullet(state_path: Path) -> str:
    try:
        lines = state_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RunnerCaptureError("docs/handoff/state.md is unavailable") from exc
    in_focus = False
    for line in lines:
        if line == "## Current focus":
            in_focus = True
            continue
        if in_focus and line.startswith("## "):
            break
        if in_focus and line.startswith("- "):
            return line
    raise RunnerCaptureError("docs/handoff/state.md has no current-focus bullet")


def validation_record_passed(value: object) -> bool:
    """Return whether a record exactly matches a zero-error runner validation."""
    try:
        record = _object_copy(value)
        if set(record) != {"summary", "diagnostics"}:
            return False
        summary = _object_copy(record.get("summary"))
        if set(summary) != {"diagnostics", "errors", "warnings"}:
            return False
        diagnostics = _array(record.get("diagnostics"), "validation diagnostics")
    except RunnerCaptureError:
        return False
    counts = {
        "diagnostics": len(diagnostics),
        "errors": 0,
        "warnings": 0,
    }
    for diagnostic in diagnostics:
        try:
            item = _object_copy(diagnostic)
        except RunnerCaptureError:
            return False
        required = {"path", "line", "column", "code", "severity", "message"}
        optional = {"hint", "snippet"}
        if not required <= set(item) or not set(item) <= required | optional:
            return False
        if (
            not all(
                isinstance(item[field], str) and bool(item[field])
                for field in ("path", "code", "severity", "message")
            )
            or not _is_nonnegative_integer(item["line"])
            or not _is_nonnegative_integer(item["column"])
            or any(
                field in item and (not isinstance(item[field], str) or not bool(item[field]))
                for field in ("hint", "snippet")
            )
        ):
            return False
        severity = item["severity"]
        if severity not in {"error", "warning", "info"}:
            return False
        if severity in {"error", "warning"}:
            counts[cast(str, severity) + "s"] += 1
    return (
        all(_is_nonnegative_integer(summary.get(field)) for field in counts)
        and all(summary[field] == count for field, count in counts.items())
        and counts["errors"] == 0
    )


def _git_changed_files(repository: Path) -> list[str]:
    result = _run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=repository,
        environment=os.environ,
        timeout=30,
        operation="Git changed-file report",
    )
    if result.returncode != 0:
        raise RunnerCaptureError("Git changed-file report failed")
    return [line[3:] for line in result.stdout.splitlines() if len(line) >= 4]


def _scan_record_directory(run_record: Path) -> None:
    for path in run_record.rglob("*"):
        if path.is_symlink():
            raise RunnerCaptureError("runner record contains a symlink")
        if path.is_file():
            try:
                content = path.read_bytes()
            except OSError as exc:
                raise RunnerCaptureError("runner record file could not be read") from exc
            try:
                value = cast(object, json.loads(content))
            except UnicodeDecodeError, json.JSONDecodeError:
                value = None
            reject_credential_evidence(value, raw=content, context="runner record")


def _scan_bundle(bundle: Mapping[str, object]) -> None:
    reject_credential_evidence(
        bundle,
        raw=_canonical_json(bundle),
        context="runner evidence",
    )


def reject_credential_evidence(
    value: object,
    *,
    raw: bytes | None,
    context: str,
) -> None:
    """Reject secret-shaped JSON names, values, or undecodable raw evidence."""
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            record = cast(dict[object, object], current)
            for key, item in record.items():
                if not isinstance(key, str) or _CREDENTIAL_NAME.search(key):
                    raise UnsafeRunnerCaptureError(f"{context} contains credential-like output")
                pending.append(item)
        elif isinstance(current, list):
            pending.extend(cast(list[object], current))
        elif isinstance(current, str) and _CREDENTIAL_BYTES.search(current.encode("utf-8")):
            raise UnsafeRunnerCaptureError(f"{context} contains credential-like output")
    if raw is not None and (_CREDENTIAL_BYTES.search(raw) or _CREDENTIAL_RAW_KEY.search(raw)):
        raise UnsafeRunnerCaptureError(f"{context} contains credential-like output")


def _promote_bundle(evidence_root: Path, bundle: Mapping[str, object]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in REQUIRED_EVIDENCE_NAMES:
        content = _canonical_json(bundle[name])
        destination = evidence_root / name
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=evidence_root, prefix=f".{name}.", delete=False
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            temporary.replace(destination)
        except OSError as exc:
            raise RunnerCaptureError(f"evidence promotion failed for {name!r}") from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        hashes[name] = _digest(content)
    return hashes


def _verify_promoted_bundle(evidence_root: Path, hashes: Mapping[str, str]) -> None:
    if set(hashes) != set(REQUIRED_EVIDENCE_NAMES):
        raise RunnerCaptureError("promoted runner evidence name set changed")
    for name, expected in hashes.items():
        path = evidence_root / name
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise RunnerCaptureError(f"promoted runner evidence {name!r} is unavailable") from exc
        if _digest(content) != expected:
            raise RunnerCaptureError(f"promoted runner evidence {name!r} hash changed")
        reject_credential_evidence(
            None,
            raw=content,
            context=f"promoted runner evidence {name!r}",
        )


def _process_record(result: _ProcessResult) -> dict[str, object]:
    record: dict[str, object] = {
        "status": "completed",
        "exit_status": result.returncode,
        "stdout_sha256": _digest(result.stdout.encode("utf-8")),
        "stderr_sha256": _digest(result.stderr.encode("utf-8")),
    }
    diagnostic = _process_diagnostic(result)
    if result.returncode != 0 and diagnostic:
        record["diagnostic"] = diagnostic
        record["output_excerpt"] = _process_output_excerpt(result)
    return record


def _process_diagnostic(result: _ProcessResult) -> str:
    combined = _process_output_excerpt(result)
    if not combined:
        return ""
    if "invalid_json_schema" in combined and "additionalProperties" in combined:
        return (
            "Codex invalid_json_schema: response schema requires additionalProperties to be false"
        )
    return combined


def _process_output_excerpt(result: _ProcessResult) -> str:
    combined = result.stderr.strip() or result.stdout.strip()
    return combined[:2048]


def _insert_action(base: tuple[str, ...], action: str) -> tuple[str, ...]:
    return (base[0], action, *base[1:])


def _run(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
    operation: str,
    input_text: str | None = None,
) -> _ProcessResult:
    arguments = tuple(argv)
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            env=dict(environment),
            input=input_text,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RunnerCaptureError(f"{operation}: executable was not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise RunnerCaptureError(f"{operation}: timed out") from exc
    except OSError as exc:
        raise RunnerCaptureError(f"{operation}: process could not start") from exc
    encoded = (completed.stdout + completed.stderr).encode("utf-8")
    reject_credential_evidence(None, raw=encoded, context=f"{operation} output")
    return _ProcessResult(
        argv=arguments,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _child_environment(environment: Mapping[str, str] | None) -> dict[str, str]:
    selected = os.environ.copy()
    if environment is None:
        return selected
    for key, value in environment.items():
        if _CREDENTIAL_NAME.search(key) or _CREDENTIAL_BYTES.search(f"{key}={value}".encode()):
            raise UnsafeRunnerCaptureError("credential-like environment input is prohibited")
        selected[key] = value
    return selected


def _verify_console_shebang(console: Path, operator_python: Path) -> Path:
    try:
        first_line = console.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError) as exc:
        raise RunnerCaptureError("operator console script shebang is unreadable") from exc
    if not first_line.startswith("#!"):
        raise RunnerCaptureError("operator console script has no shebang")
    shebang_path = Path(first_line[2:])
    if not shebang_path.is_absolute() or shebang_path.resolve() != operator_python.resolve():
        raise RunnerCaptureError(
            "operator console script shebang does not resolve to the selected interpreter"
        )
    return shebang_path


def _verify_console_entrypoint(
    console: Path,
    pinned_pyproject: bytes,
    console_interpreter: Path,
) -> str:
    entrypoint = _pinned_console_entrypoint(pinned_pyproject)
    try:
        console_bytes = console.read_bytes()
    except OSError as exc:
        raise RunnerCaptureError("operator console entry point could not be verified") from exc
    expected = expected_console_wrapper_bytes(console_interpreter, entrypoint)
    if console_bytes != expected:
        raise RunnerCaptureError(
            "operator console wrapper does not match the exact capture revision"
        )
    return entrypoint


def _pinned_console_entrypoint(pinned_pyproject: bytes) -> str:
    try:
        payload = _object_copy(cast(object, tomllib.loads(pinned_pyproject.decode("utf-8"))))
        project = _object_copy(payload.get("project"))
        scripts = _object_copy(project.get("scripts"))
        return _string(scripts.get("apseudo-run"), "project.scripts.apseudo-run")
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise RunnerCaptureError("capture revision pyproject.toml is invalid") from exc


def _git_object_exists(repository: Path, revision: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=repository,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RunnerCaptureError("capture revision is unavailable from local Git objects")


def _git_show(repository: Path, revision: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=repository,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RunnerCaptureError(
            f"capture revision does not contain required path {relative_path!r}"
        )
    return result.stdout


def _resolve_revision(repository: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    exact = result.stdout.strip()
    if result.returncode != 0 or _FULL_REVISION.fullmatch(exact) is None:
        raise RunnerCaptureError("revision: expected a resolvable Git commit")
    return exact


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RunnerCaptureError(f"Git {' '.join(arguments)} failed")
    return result.stdout.strip()


def _argument_vector(values: Sequence[str], field: str) -> tuple[str, ...]:
    vector = tuple(values)
    if not vector or any("\x00" in value for value in vector):
        raise RunnerCaptureError(f"{field}: expected a non-empty string argument vector")
    return vector


def _directory(path: Path, field: str) -> Path:
    resolved = _safe_path(path, field)
    if not resolved.is_dir():
        raise RunnerCaptureError(f"{field}: expected an existing directory")
    return resolved


def _existing_file(path: Path, field: str) -> Path:
    selected = path.expanduser().absolute()
    if not selected.is_file():
        raise RunnerCaptureError(f"{field}: expected an existing file")
    return selected


def _safe_path(path: Path, field: str) -> Path:
    try:
        return path.expanduser().resolve()
    except OSError as exc:
        raise RunnerCaptureError(f"{field}: path resolution failed") from exc


def _canonical_json(value: object) -> bytes:
    try:
        return (json.dumps(value, indent="\t", sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise RunnerCaptureError("runner evidence is not JSON serializable") from exc


def _require_exact_bundle(bundle: Mapping[str, object]) -> None:
    if set(bundle) != set(REQUIRED_EVIDENCE_NAMES):
        raise RunnerCaptureError("runner evidence bundle has an unexpected name set")


def _object_copy(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RunnerCaptureError("runner evidence record must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise RunnerCaptureError("runner evidence object keys must be strings")
    return {cast(str, key): item for key, item in raw.items()}


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise RunnerCaptureError(f"{field}: expected an array")
    return cast(list[object], value)


def _alias_tokens(aliases: Mapping[str, object], name: str) -> list[str]:
    value = aliases.get(name)
    tokens = _array(value, f"display alias {name!r}")
    if any(not isinstance(token, str) for token in tokens):
        raise RunnerCaptureError(f"display alias {name!r} is invalid")
    return [cast(str, token) for token in tokens]


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RunnerCaptureError(f"{field}: expected a non-empty string")
    return value


def _hash_string(value: object, field: str) -> str:
    selected = _string(value, field)
    if re.fullmatch(r"[0-9a-f]{64}", selected) is None:
        raise RunnerCaptureError(f"{field}: expected a SHA-256 digest")
    return selected


def _is_nonnegative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
