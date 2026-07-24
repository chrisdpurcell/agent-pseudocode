"""Pinned operator-runtime preparation and complete package-closure checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .runner_security import (
    RunnerCaptureError,
    UnsafeRunnerCaptureError,
    build_child_environment,
    run_capture_process,
)

MODULE_SOURCE = "src/apseudo_lint/__init__.py"
ENTRYPOINT_MODULE_SOURCE = "src/apseudo_lint/runner_cli.py"
_VERSION_LINE = re.compile(rb'^__version__\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
_LOGIN_CONFIRMATION = re.compile(r"(?im)^Logged in(?: using .+)?$")


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
    package_files: tuple[tuple[str, str], ...]
    toolkit_version: str
    environment_sha256: str
    sync_argv: tuple[str, ...]
    sync_status: int
    provider_status_argv: tuple[str, ...]
    provider_status: int
    precondition_reason: str | None


def prepare_runner_runtime(
    repository_root: Path,
    *,
    revision: str,
    operator_python: Path | None = None,
    operator_apseudo_run: Path | None = None,
    environment: Mapping[str, str] | None = None,
    auth_environment: Mapping[str, str] | None = None,
    sync_argv: Sequence[str] = ("uv", "sync", "--locked", "--all-groups"),
    provider_status_argv: Sequence[str] = ("codex", "login", "status"),
) -> RunnerRuntime:
    """Synchronize and prove the local operator runtime before cloning."""
    root = _directory(repository_root, "repository_root")
    child_environment = build_child_environment(environment)
    provider_environment = build_child_environment(
        environment,
        auth_environment=auth_environment,
    )
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
    sync = run_capture_process(
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
    provider = run_capture_process(
        provider_command,
        cwd=root,
        environment=provider_environment,
        timeout=30,
        operation="Codex login status",
    )
    if provider.returncode != 0 and precondition_reason is None:
        precondition_reason = (
            f"Codex login status exited {provider.returncode}; configured login is required"
        )
    if (
        provider.returncode == 0
        and _LOGIN_CONFIRMATION.search(f"{provider.stdout}\n{provider.stderr}") is None
        and precondition_reason is None
    ):
        precondition_reason = "Codex login status did not confirm a configured login"

    (
        module_path,
        module_sha256,
        entrypoint_module_path,
        entrypoint_module_sha256,
        package_files,
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
    if package_files != _pinned_package_closure(root, exact_revision):
        raise RunnerCaptureError(
            "operator package closure does not match the exact capture revision"
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
        package_files=package_files,
        toolkit_version=toolkit_version,
        environment_sha256=environment_digest(child_environment),
        sync_argv=sync_command,
        sync_status=sync.returncode,
        provider_status_argv=provider_command,
        provider_status=provider.returncode,
        precondition_reason=precondition_reason,
    )


def runtime_precondition_reason(
    runtime: RunnerRuntime,
    exact_revision: str,
) -> str | None:
    """Return a stable reason when a prepared runtime cannot run."""
    if runtime.revision != exact_revision:
        return "runtime revision does not match the requested capture revision"
    if runtime.precondition_reason is not None:
        return runtime.precondition_reason
    if runtime.sync_status != 0:
        return f"locked environment sync exited {runtime.sync_status}; expected 0"
    if runtime.provider_status != 0:
        return f"Codex login status exited {runtime.provider_status}; configured login is required"
    return None


def runtime_integrity_reason(
    repository: Path,
    exact_revision: str,
    runtime: RunnerRuntime,
    environment: Mapping[str, str],
) -> str | None:
    """Revalidate every executable package byte immediately before each vector."""
    if environment_digest(environment) != runtime.environment_sha256:
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
            package_files,
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
        pinned_package_files = _pinned_package_closure(repository, exact_revision)
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
    if package_files != runtime.package_files or package_files != pinned_package_files:
        return "operator package closure changed after runtime preparation"
    return None


def environment_digest(environment: Mapping[str, str]) -> str:
    """Hash the selected child environment without recording its values."""
    encoded = json.dumps(
        sorted(environment.items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return _digest(encoded)


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


def _operator_module_identity(
    operator_python: Path,
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> tuple[Path, str, Path, str, tuple[tuple[str, str], ...], str]:
    identity_code = (
        "import hashlib,json,pathlib,apseudo_lint,apseudo_lint.runner_cli as runner_cli;"
        "p=pathlib.Path(apseudo_lint.__file__).resolve();"
        "r=pathlib.Path(runner_cli.__file__).resolve();"
        "root=p.parent;"
        "files={str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() "
        "for q in root.rglob('*.py') if '__pycache__' not in q.parts};"
        "print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),"
        "'entrypoint_path':str(r),"
        "'entrypoint_sha256':hashlib.sha256(r.read_bytes()).hexdigest(),"
        "'package_files':files,"
        "'version':apseudo_lint.__version__},sort_keys=True))"
    )
    identity = run_capture_process(
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
        package_record = _object_copy(payload.get("package_files"))
        package_files = tuple(
            sorted(
                (
                    _string(relative_path, "operator package relative path"),
                    _hash_string(value, "operator package file sha256"),
                )
                for relative_path, value in package_record.items()
            )
        )
        toolkit_version = _string(payload.get("version"), "operator toolkit version")
    except (json.JSONDecodeError, TypeError) as exc:
        raise RunnerCaptureError("operator module identity returned invalid JSON") from exc
    return (
        module_path,
        module_sha256,
        entrypoint_path,
        entrypoint_sha256,
        package_files,
        toolkit_version,
    )


def _pinned_package_closure(
    repository: Path,
    exact_revision: str,
) -> tuple[tuple[str, str], ...]:
    listing = _git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        exact_revision,
        "--",
        "src/apseudo_lint",
    )
    prefix = "src/apseudo_lint/"
    paths = tuple(
        line for line in listing.splitlines() if line.startswith(prefix) and line.endswith(".py")
    )
    if not paths:
        raise RunnerCaptureError("capture revision has no Python package closure")
    return tuple(
        (
            path.removeprefix(prefix),
            _digest(_git_show(repository, exact_revision, path)),
        )
        for path in paths
    )


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
    result = _git_process(
        repository,
        ("git", "cat-file", "-e", f"{revision}^{{commit}}"),
        "Git object probe",
    )
    if result.returncode != 0:
        raise RunnerCaptureError("capture revision is unavailable from local Git objects")


def _git_show(repository: Path, revision: str, relative_path: str) -> bytes:
    result = _git_process(
        repository,
        ("git", "show", f"{revision}:{relative_path}"),
        f"Git read {relative_path}",
    )
    if result.returncode != 0:
        raise RunnerCaptureError(
            f"capture revision does not contain required path {relative_path!r}"
        )
    return result.stdout.encode("utf-8")


def _resolve_revision(repository: Path, revision: str) -> str:
    result = _git_process(
        repository,
        ("git", "rev-parse", "--verify", f"{revision}^{{commit}}"),
        "Git revision resolution",
    )
    exact = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", exact) is None:
        raise RunnerCaptureError("revision: expected a resolvable Git commit")
    return exact


def _git(repository: Path, *arguments: str) -> str:
    result = _git_process(
        repository,
        ("git", *arguments),
        f"Git {' '.join(arguments)}",
    )
    if result.returncode != 0:
        raise RunnerCaptureError(f"Git {' '.join(arguments)} failed")
    return result.stdout.strip()


def _git_process(repository: Path, argv: tuple[str, ...], operation: str):
    return run_capture_process(
        argv,
        cwd=repository,
        environment=build_child_environment(None),
        timeout=30,
        operation=operation,
        screen_output=False,
    )


def _argument_vector(values: Sequence[str], field: str) -> tuple[str, ...]:
    raw_vector = cast(Sequence[object], values)
    if any(not isinstance(value, str) for value in raw_vector):
        raise RunnerCaptureError(f"{field}: expected a non-empty string argument vector")
    vector = tuple(cast(str, value) for value in raw_vector)
    if not vector or any("\x00" in value for value in vector):
        raise RunnerCaptureError(f"{field}: expected a non-empty string argument vector")
    return vector


def _directory(path: Path, field: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise RunnerCaptureError(f"{field}: expected an existing directory")
    return resolved


def _existing_file(path: Path, field: str) -> Path:
    selected = path.expanduser().absolute()
    if not selected.is_file():
        raise RunnerCaptureError(f"{field}: expected an existing file")
    return selected


def _object_copy(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RunnerCaptureError("runner evidence record must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise RunnerCaptureError("runner evidence object keys must be strings")
    return {cast(str, key): item for key, item in raw.items()}


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RunnerCaptureError(f"{field}: expected a non-empty string")
    return value


def _hash_string(value: object, field: str) -> str:
    selected = _string(value, field)
    if re.fullmatch(r"[0-9a-f]{64}", selected) is None:
        raise RunnerCaptureError(f"{field}: expected a SHA-256 digest")
    return selected


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
