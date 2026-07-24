"""Security and bounded-I/O primitives for guarded runner capture."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast

MAX_PROCESS_OUTPUT_BYTES = 1_048_576
MAX_EVIDENCE_FILE_BYTES = 1_048_576
_PROCESS_POLL_SECONDS = 0.05
_PROCESS_TERM_SECONDS = 0.5
_PROCESS_KILL_SECONDS = 0.5
_READER_JOIN_SECONDS = 0.5

_CHILD_ENVIRONMENT_KEYS = frozenset(
    {
        "APSEUDO_TEST_FILE_LIMIT",
        "APSEUDO_TEST_HOOK_MODE",
        "APSEUDO_TEST_LOGIN_MESSAGE",
        "APSEUDO_TEST_LOGIN_STATUS",
        "APSEUDO_TEST_OUTPUT_LIMIT",
        "APSEUDO_TEST_REQUIRE_AUTH",
        "APSEUDO_TEST_RUNNER_MODE",
        "APSEUDO_TEST_SYNC_STATUS",
        "CODEX_HOME",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PATH",
        "TMPDIR",
        "XDG_CONFIG_HOME",
    }
)
_AUTH_ENVIRONMENT_KEYS = frozenset({"OPENAI_API_KEY"})
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


class RunnerCaptureError(ValueError):
    """Reject invalid or unverifiable runner capture inputs."""


class RunnerOperationalError(RunnerCaptureError):
    """Report an expected operational failure that permits safe evidence."""


class UnsafeRunnerCaptureError(RunnerCaptureError):
    """Reject credential-bearing input or output without promoting evidence."""


class EvidencePromotionError(RunnerCaptureError):
    """Reject a promotion that cannot preserve the prior evidence directory."""


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """One subprocess result retained only after secret screening."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def build_child_environment(
    environment: Mapping[str, str] | None,
    *,
    auth_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a minimal child environment with explicit, non-recorded auth."""
    selected = {key: value for key, value in os.environ.items() if key in _CHILD_ENVIRONMENT_KEYS}
    if environment is not None:
        untyped_environment = cast(Mapping[object, object], environment)
        for key, value in untyped_environment.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise RunnerCaptureError("child environment keys and values must be strings")
            if _CREDENTIAL_NAME.search(key) or _CREDENTIAL_BYTES.search(f"{key}={value}".encode()):
                raise UnsafeRunnerCaptureError("credential-like environment input is prohibited")
            if key not in _CHILD_ENVIRONMENT_KEYS:
                raise RunnerCaptureError(f"child environment key {key!r} is not allowlisted")
            selected[key] = value
    if auth_environment is not None:
        untyped_auth = cast(Mapping[object, object], auth_environment)
        for key, value in untyped_auth.items():
            if not isinstance(key, str):
                raise RunnerCaptureError("Codex auth environment keys must be strings")
            if key not in _AUTH_ENVIRONMENT_KEYS:
                raise RunnerCaptureError(f"Codex auth environment key {key!r} is not supported")
            if not isinstance(value, str) or not value:
                raise RunnerCaptureError(
                    f"Codex auth environment key {key!r} requires a non-empty value"
                )
            selected[key] = value
    return selected


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


def read_bytes_limited(
    path: Path,
    *,
    operation: str,
    limit: int = MAX_EVIDENCE_FILE_BYTES,
) -> bytes:
    """Read no more than ``limit`` bytes from a regular non-symlink file."""
    try:
        if path.is_symlink() or not path.is_file():
            raise RunnerOperationalError(f"{operation}: expected a regular non-symlink file")
        with path.open("rb") as handle:
            content = handle.read(limit + 1)
    except RunnerOperationalError:
        raise
    except OSError as exc:
        raise RunnerOperationalError(f"{operation}: file could not be read") from exc
    if len(content) > limit:
        raise RunnerOperationalError(f"{operation}: file exceeds the read limit")
    return content


def run_capture_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
    operation: str,
    input_text: str | None = None,
    screen_output: bool = True,
) -> ProcessResult:
    """Run a process while draining and capping each output stream."""
    arguments = tuple(argv)
    try:
        process = subprocess.Popen(
            arguments,
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise RunnerOperationalError(f"{operation}: executable was not found") from exc
    except OSError as exc:
        raise RunnerOperationalError(f"{operation}: process could not start") from exc

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    exceeded = threading.Event()
    threads = [
        threading.Thread(
            target=_drain_stream,
            args=(process.stdout, stdout_buffer, exceeded),
            daemon=True,
        ),
        threading.Thread(
            target=_drain_stream,
            args=(process.stderr, stderr_buffer, exceeded),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    if input_text is not None:
        assert process.stdin is not None
        try:
            process.stdin.write(input_text.encode("utf-8"))
            process.stdin.close()
        except BrokenPipeError:
            pass
    deadline = time.monotonic() + timeout
    failure: RunnerOperationalError | None = None
    while True:
        if exceeded.is_set():
            failure = RunnerOperationalError(
                f"{operation}: output exceeded {MAX_PROCESS_OUTPUT_BYTES} bytes"
            )
            break
        observed_returncode = process.poll()
        if observed_returncode is not None:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            failure = RunnerOperationalError(f"{operation}: timed out")
            break
        exceeded.wait(min(_PROCESS_POLL_SECONDS, remaining))
    if failure is not None:
        _terminate_process_group(process)
        _finish_reader_threads(process, threads)
        raise failure
    returncode = process.poll()
    if returncode is None:
        _terminate_process_group(process)
        _finish_reader_threads(process, threads)
        raise RunnerOperationalError(f"{operation}: process state became unavailable")
    if not _join_reader_threads(threads, _READER_JOIN_SECONDS):
        _terminate_process_group(process)
        _finish_reader_threads(process, threads)
        if exceeded.is_set():
            raise RunnerOperationalError(
                f"{operation}: output exceeded {MAX_PROCESS_OUTPUT_BYTES} bytes"
            )
        raise RunnerOperationalError(f"{operation}: descendant process retained output pipes")
    if exceeded.is_set():
        raise RunnerOperationalError(
            f"{operation}: output exceeded {MAX_PROCESS_OUTPUT_BYTES} bytes"
        )
    try:
        stdout = bytes(stdout_buffer).decode("utf-8")
        stderr = bytes(stderr_buffer).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RunnerOperationalError(f"{operation}: output was not UTF-8") from exc
    if screen_output:
        reject_credential_evidence(
            None,
            raw=bytes(stdout_buffer) + bytes(stderr_buffer),
            context=f"{operation} output",
        )
    return ProcessResult(
        argv=arguments,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _drain_stream(
    stream: BinaryIO | None,
    buffer: bytearray,
    exceeded: threading.Event,
) -> None:
    if stream is None:
        return
    try:
        with stream:
            while chunk := os.read(stream.fileno(), 65_536):
                remaining = MAX_PROCESS_OUTPUT_BYTES + 1 - len(buffer)
                if remaining > 0:
                    buffer.extend(chunk[:remaining])
                if len(buffer) > MAX_PROCESS_OUTPUT_BYTES or len(chunk) > remaining:
                    exceeded.set()
    except OSError:
        return


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    process_group = process.pid
    _signal_process_group(process_group, signal.SIGTERM)
    if not _wait_process_group(process_group, _PROCESS_TERM_SECONDS):
        _signal_process_group(process_group, signal.SIGKILL)
        _wait_process_group(process_group, _PROCESS_KILL_SECONDS)
    try:
        process.wait(timeout=_PROCESS_KILL_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=_PROCESS_KILL_SECONDS)
        except subprocess.TimeoutExpired:
            return


def _signal_process_group(process_group: int, selected_signal: signal.Signals) -> None:
    try:
        os.killpg(process_group, selected_signal)
    except ProcessLookupError:
        return


def _wait_process_group(process_group: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return True
        time.sleep(_PROCESS_POLL_SECONDS)
    return False


def _join_reader_threads(
    threads: Sequence[threading.Thread],
    timeout: float,
) -> bool:
    deadline = time.monotonic() + timeout
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    return all(not thread.is_alive() for thread in threads)


def _finish_reader_threads(
    process: subprocess.Popen[bytes],
    threads: Sequence[threading.Thread],
) -> None:
    if _join_reader_threads(threads, _READER_JOIN_SECONDS):
        return
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    _join_reader_threads(threads, _READER_JOIN_SECONDS)
