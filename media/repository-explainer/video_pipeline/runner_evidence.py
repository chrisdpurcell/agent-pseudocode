"""Typed runner-record validation and transactional evidence promotion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .capture import RUNNER_EVIDENCE_NAMES
from .runner_security import (
    EvidencePromotionError,
    RunnerCaptureError,
    RunnerOperationalError,
    read_bytes_limited,
    reject_credential_evidence,
)

_FULL_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MANIFEST_FIELDS = frozenset(
    {
        "agent",
        "args",
        "ended_at",
        "exit_code",
        "git_head",
        "mode",
        "outcome",
        "passthrough",
        "prompt_sha256",
        "reason",
        "run_id",
        "script_name",
        "script_path",
        "started_at",
        "toolkit_version",
        "workspace",
    }
)
_AGENT_COMMAND_FIELDS = frozenset(
    {
        "argv",
        "cwd",
        "env_overrides",
        "output_last_message_path",
        "schema_path",
        "stdin",
    }
)
_OUTCOME_FIELDS = frozenset({"artifacts", "checks_run", "evidence", "outcome", "reason", "summary"})
_POST_CHECK_FIELDS = frozenset({"command", "passed", "returncode", "stderr", "stdout"})
_OUTCOME_EXIT_CODES = {"Accepted": 0, "NeedsUserDecision": 10, "Blocked": 20}


@dataclass(frozen=True, slots=True)
class RunnerArtifactContext:
    """Expected values that bind one runner record to its capture."""

    revision: str
    workspace: Path
    script_path: Path
    script_name: str
    spec_path: str
    prompt: str
    preview_argv: tuple[str, ...]
    post_check: str
    execution_exit_code: int
    toolkit_version: str


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Strictly parsed accepted-run manifest fields used by capture."""

    run_id: str
    agent: str
    mode: str
    workspace: str
    git_head: str
    exit_code: int
    outcome: str
    reason: str
    prompt_sha256: str


@dataclass(frozen=True, slots=True)
class AgentCommand:
    """Strictly parsed provider invocation."""

    argv: tuple[str, ...]
    stdin: str
    cwd: str
    schema_path: str
    output_last_message_path: str


@dataclass(frozen=True, slots=True)
class PostCheck:
    """Strictly parsed deterministic post-check."""

    command: str
    returncode: int
    passed: bool


@dataclass(frozen=True, slots=True)
class RunnerOutcome:
    """Strictly parsed provider outcome."""

    outcome: str
    reason: str
    checks_run: tuple[str, ...]


def validate_runner_artifact_contract(
    artifacts: Mapping[str, object],
    context: RunnerArtifactContext,
) -> str | None:
    """Return a precise reason when cross-bound runner artifacts are invalid."""
    try:
        manifest = _parse_manifest(artifacts.get("run-manifest.json"), context)
        command = _parse_agent_command(artifacts.get("agent-command.json"), context)
        _parse_validation(artifacts.get("validation-before.json"))
        post_check = _parse_post_check(artifacts.get("post-checks.json"), context)
        outcome = _parse_outcome(artifacts.get("outcome.json"), context)
        _cross_bind(manifest, command, post_check, outcome, context)
    except RunnerCaptureError as exc:
        return f"runner artifact contract failed: {exc}"
    return None


def validation_record_passed(value: object) -> bool:
    """Return whether a record exactly matches a zero-error runner validation."""
    try:
        _parse_validation(value)
    except RunnerCaptureError:
        return False
    return True


def promote_evidence_bundle(
    evidence_root: Path,
    bundle: Mapping[str, object],
    *,
    allow_recapture: bool = False,
) -> dict[str, str]:
    """Stage, validate, and atomically commit one exact evidence directory."""
    if set(bundle) != set(RUNNER_EVIDENCE_NAMES):
        raise EvidencePromotionError("runner evidence bundle has an unexpected name set")
    parent = evidence_root.expanduser().absolute().parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise EvidencePromotionError("evidence parent directory is unavailable") from exc
    destination = evidence_root.expanduser().absolute()
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=parent))
    backup: Path | None = None
    try:
        hashes = _write_stage(stage, bundle)
        if destination.exists() or destination.is_symlink():
            if _directory_matches(destination, hashes):
                shutil.rmtree(stage)
                return hashes
            if not allow_recapture:
                raise EvidencePromotionError(
                    "existing evidence differs; explicit recapture authority is required"
                )
            backup = Path(tempfile.mkdtemp(prefix=f".{destination.name}.backup-", dir=parent))
            backup.rmdir()
            replace_evidence_path(destination, backup)
        try:
            replace_evidence_path(stage, destination)
        except OSError as exc:
            if backup is not None and backup.exists() and not destination.exists():
                replace_evidence_path(backup, destination)
                backup = None
            raise EvidencePromotionError("evidence directory commit failed") from exc
        if backup is not None:
            _remove_path(backup)
            backup = None
        _validate_directory(destination, hashes)
        return hashes
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists() and not destination.exists():
            replace_evidence_path(backup, destination)


def _write_stage(stage: Path, bundle: Mapping[str, object]) -> dict[str, str]:
    reject_credential_evidence(
        bundle,
        raw=_canonical_json(bundle),
        context="runner evidence",
    )
    hashes: dict[str, str] = {}
    for name in RUNNER_EVIDENCE_NAMES:
        content = _canonical_json(bundle[name])
        reject_credential_evidence(
            bundle[name],
            raw=content,
            context=f"runner evidence {name!r}",
        )
        path = stage / name
        try:
            with path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise EvidencePromotionError(f"evidence staging failed for {name!r}") from exc
        hashes[name] = _digest(content)
    _fsync_directory(stage)
    _validate_directory(stage, hashes)
    return hashes


def _validate_directory(directory: Path, hashes: Mapping[str, str]) -> None:
    if set(hashes) != set(RUNNER_EVIDENCE_NAMES):
        raise EvidencePromotionError("promoted runner evidence name set changed")
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        raise EvidencePromotionError("promoted evidence directory is unavailable") from exc
    if {entry.name for entry in entries} != set(RUNNER_EVIDENCE_NAMES):
        raise EvidencePromotionError("promoted evidence directory inventory changed")
    for entry in entries:
        try:
            metadata = entry.lstat()
        except OSError as exc:
            raise EvidencePromotionError(
                f"promoted runner evidence {entry.name!r} is unavailable"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise EvidencePromotionError(
                f"promoted runner evidence {entry.name!r} is not a regular file"
            )
        try:
            content = read_bytes_limited(
                entry,
                operation=f"promoted runner evidence {entry.name!r}",
            )
        except RunnerOperationalError as exc:
            raise EvidencePromotionError(str(exc)) from exc
        if _digest(content) != hashes[entry.name]:
            raise EvidencePromotionError(f"promoted runner evidence {entry.name!r} hash changed")
        reject_credential_evidence(
            None,
            raw=content,
            context=f"promoted runner evidence {entry.name!r}",
        )


def _directory_matches(directory: Path, hashes: Mapping[str, str]) -> bool:
    try:
        _validate_directory(directory, hashes)
    except EvidencePromotionError:
        return False
    return True


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def replace_evidence_path(source: Path, destination: Path) -> None:
    """Replace one promotion path; exposed as the commit fault-injection seam."""
    source.replace(destination)


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise EvidencePromotionError("evidence staging directory could not be synced") from exc


def _parse_manifest(value: object, context: RunnerArtifactContext) -> RunManifest:
    record = _object(value, "run-manifest.json")
    if set(record) != set(_MANIFEST_FIELDS):
        raise RunnerCaptureError("run-manifest.json fields changed")
    run_id = _string(record["run_id"], "manifest run_id")
    _string(record["started_at"], "manifest started_at")
    _string(record["ended_at"], "manifest ended_at")
    if _string(record["toolkit_version"], "manifest toolkit_version") != context.toolkit_version:
        raise RunnerCaptureError("manifest toolkit version changed")
    if Path(_string(record["script_path"], "manifest script_path")) != context.script_path:
        raise RunnerCaptureError("manifest script path changed")
    if _string(record["script_name"], "manifest script_name") != context.script_name:
        raise RunnerCaptureError("manifest script name changed")
    agent = _string(record["agent"], "manifest agent")
    mode = _string(record["mode"], "manifest mode")
    workspace = _string(record["workspace"], "manifest workspace")
    args = _object(record["args"], "manifest args")
    if args != {"spec_path": context.spec_path}:
        raise RunnerCaptureError("manifest script arguments changed")
    if _string_array(record["passthrough"], "manifest passthrough"):
        raise RunnerCaptureError("manifest passthrough arguments changed")
    prompt_sha256 = _hash(record["prompt_sha256"], "manifest prompt_sha256")
    git_head = _revision(record["git_head"], "manifest git_head")
    exit_code = _integer(record["exit_code"], "manifest exit_code")
    outcome = _string(record["outcome"], "manifest outcome")
    reason = _string(record["reason"], "manifest reason")
    return RunManifest(
        run_id=run_id,
        agent=agent,
        mode=mode,
        workspace=workspace,
        git_head=git_head,
        exit_code=exit_code,
        outcome=outcome,
        reason=reason,
        prompt_sha256=prompt_sha256,
    )


def _parse_agent_command(
    value: object,
    context: RunnerArtifactContext,
) -> AgentCommand:
    record = _object(value, "agent-command.json")
    if set(record) != set(_AGENT_COMMAND_FIELDS):
        raise RunnerCaptureError("agent-command.json fields changed")
    argv = _string_array(record["argv"], "agent command argv")
    if len(argv) < 3 or argv[:2] != ("codex", "exec") or argv[-1] != "-":
        raise RunnerCaptureError("agent command provider vector changed")
    cwd = _string(record["cwd"], "agent command cwd")
    environment = _object(record["env_overrides"], "agent command env_overrides")
    if environment:
        raise RunnerCaptureError("agent command environment overrides changed")
    stdin = _string(record["stdin"], "agent command stdin")
    schema_path = _string(record["schema_path"], "agent command schema_path")
    last_message_path = _string(
        record["output_last_message_path"],
        "agent command output_last_message_path",
    )
    if _option(argv, "--cd") != os.fspath(context.workspace):
        raise RunnerCaptureError("agent command workspace changed")
    if _option(argv, "--sandbox") != "read-only":
        raise RunnerCaptureError("agent command sandbox changed")
    if "--json" not in argv:
        raise RunnerCaptureError("agent command JSON mode is absent")
    if _option(argv, "--output-schema") != schema_path:
        raise RunnerCaptureError("agent command schema path is not bound to argv")
    if _option(argv, "--output-last-message") != last_message_path:
        raise RunnerCaptureError("agent command output path is not bound to argv")
    if _normalized_provider_argv(argv) != _normalized_provider_argv(context.preview_argv):
        raise RunnerCaptureError("provider preview and execution vectors differ")
    return AgentCommand(
        argv=argv,
        stdin=stdin,
        cwd=cwd,
        schema_path=schema_path,
        output_last_message_path=last_message_path,
    )


def _parse_validation(value: object) -> None:
    record = _object(value, "validation-before.json")
    if set(record) != {"summary", "diagnostics"}:
        raise RunnerCaptureError("validation-before.json fields changed")
    summary = _object(record["summary"], "validation summary")
    if set(summary) != {"diagnostics", "errors", "warnings"}:
        raise RunnerCaptureError("validation summary fields changed")
    diagnostics = _array(record["diagnostics"], "validation diagnostics")
    counts = {"diagnostics": len(diagnostics), "errors": 0, "warnings": 0}
    for value_item in diagnostics:
        item = _object(value_item, "validation diagnostic")
        required = {"path", "line", "column", "code", "severity", "message"}
        optional = {"hint", "snippet"}
        if not required <= set(item) or not set(item) <= required | optional:
            raise RunnerCaptureError("validation diagnostic fields changed")
        for field in ("path", "code", "severity", "message"):
            _string(item[field], f"validation diagnostic {field}")
        _nonnegative_integer(item["line"], "validation diagnostic line")
        _nonnegative_integer(item["column"], "validation diagnostic column")
        for field in ("hint", "snippet"):
            if field in item:
                _string(item[field], f"validation diagnostic {field}")
        severity = item["severity"]
        if severity not in {"error", "warning", "info"}:
            raise RunnerCaptureError("validation diagnostic severity changed")
        if severity in {"error", "warning"}:
            counts[cast(str, severity) + "s"] += 1
    for field, expected in counts.items():
        if _nonnegative_integer(summary[field], f"validation {field}") != expected:
            raise RunnerCaptureError("validation summary contradicts diagnostics")
    if counts["errors"] != 0:
        raise RunnerCaptureError("validation-before.json contains errors")


def _parse_post_check(value: object, context: RunnerArtifactContext) -> PostCheck:
    records = _array(value, "post-checks.json")
    if len(records) != 1:
        raise RunnerCaptureError("post-checks.json must contain exactly one record")
    record = _object(records[0], "post-check record")
    if set(record) != set(_POST_CHECK_FIELDS):
        raise RunnerCaptureError("post-check record fields changed")
    command = _string(record["command"], "post-check command")
    returncode = _integer(record["returncode"], "post-check returncode")
    passed = _boolean(record["passed"], "post-check passed")
    _string_or_empty(record["stdout"], "post-check stdout")
    _string_or_empty(record["stderr"], "post-check stderr")
    if command != context.post_check:
        raise RunnerCaptureError("post-check command changed")
    if passed != (returncode == 0):
        raise RunnerCaptureError("post-check status contradicts return code")
    return PostCheck(command=command, returncode=returncode, passed=passed)


def _parse_outcome(value: object, context: RunnerArtifactContext) -> RunnerOutcome:
    record = _object(value, "outcome.json")
    if not set(record) <= _OUTCOME_FIELDS or not {
        "artifacts",
        "checks_run",
        "outcome",
        "reason",
        "summary",
    } <= set(record):
        raise RunnerCaptureError("outcome.json fields changed")
    outcome = _string(record["outcome"], "outcome")
    if outcome not in _OUTCOME_EXIT_CODES:
        raise RunnerCaptureError("outcome value changed")
    reason = _string(record["reason"], "outcome reason")
    _string(record["summary"], "outcome summary")
    checks_run = _string_array(record["checks_run"], "outcome checks_run")
    _string_array(record["artifacts"], "outcome artifacts")
    if "evidence" in record:
        _string(record["evidence"], "outcome evidence")
    if checks_run != (context.post_check,):
        raise RunnerCaptureError("outcome checks are not bound to the post-check")
    return RunnerOutcome(outcome=outcome, reason=reason, checks_run=checks_run)


def _cross_bind(
    manifest: RunManifest,
    command: AgentCommand,
    post_check: PostCheck,
    outcome: RunnerOutcome,
    context: RunnerArtifactContext,
) -> None:
    expected_prompt_hash = _digest(context.prompt.encode("utf-8"))
    if manifest.agent != "codex" or manifest.mode != "review":
        raise RunnerCaptureError("manifest agent or mode changed")
    if manifest.workspace != os.fspath(context.workspace) or command.cwd != manifest.workspace:
        raise RunnerCaptureError("runner record workspace binding changed")
    if manifest.git_head != context.revision:
        raise RunnerCaptureError("manifest Git head does not match capture revision")
    if manifest.exit_code != context.execution_exit_code:
        raise RunnerCaptureError("manifest exit code does not match runner execution")
    if manifest.prompt_sha256 != expected_prompt_hash or command.stdin != context.prompt:
        raise RunnerCaptureError("runner prompt hash or stdin binding changed")
    if manifest.outcome != outcome.outcome or manifest.reason != outcome.reason:
        raise RunnerCaptureError("manifest and outcome records disagree")
    if _OUTCOME_EXIT_CODES[outcome.outcome] != manifest.exit_code:
        raise RunnerCaptureError("runner outcome contradicts its exit code")
    if post_check.passed != (outcome.outcome == "Accepted"):
        raise RunnerCaptureError("post-check and outcome records disagree")


def _normalized_provider_argv(argv: Sequence[str]) -> tuple[str, ...]:
    normalized = list(argv)
    for option in ("--output-last-message", "--output-schema"):
        try:
            index = normalized.index(option) + 1
            normalized[index] = f"<{option[2:]}>"
        except (ValueError, IndexError) as exc:
            raise RunnerCaptureError(f"provider vector is missing {option}") from exc
    return tuple(normalized)


def _option(argv: Sequence[str], option: str) -> str:
    try:
        return argv[argv.index(option) + 1]
    except (ValueError, IndexError) as exc:
        raise RunnerCaptureError(f"provider vector is missing {option}") from exc


def _canonical_json(value: object) -> bytes:
    try:
        return (json.dumps(value, indent="\t", sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise EvidencePromotionError("runner evidence is not JSON serializable") from exc


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RunnerCaptureError(f"{field}: expected an object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise RunnerCaptureError(f"{field}: object keys must be strings")
    return {cast(str, key): item for key, item in raw.items()}


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise RunnerCaptureError(f"{field}: expected an array")
    return cast(list[object], value)


def _string_array(value: object, field: str) -> tuple[str, ...]:
    items = _array(value, field)
    if any(not isinstance(item, str) for item in items):
        raise RunnerCaptureError(f"{field}: expected only strings")
    return tuple(cast(str, item) for item in items)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RunnerCaptureError(f"{field}: expected a non-empty string")
    return value


def _string_or_empty(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise RunnerCaptureError(f"{field}: expected a string")
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RunnerCaptureError(f"{field}: expected an integer")
    return value


def _nonnegative_integer(value: object, field: str) -> int:
    selected = _integer(value, field)
    if selected < 0:
        raise RunnerCaptureError(f"{field}: expected a nonnegative integer")
    return selected


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise RunnerCaptureError(f"{field}: expected a boolean")
    return value


def _hash(value: object, field: str) -> str:
    selected = _string(value, field)
    if _SHA256.fullmatch(selected) is None:
        raise RunnerCaptureError(f"{field}: expected a SHA-256 digest")
    return selected


def _revision(value: object, field: str) -> str:
    selected = _string(value, field)
    if _FULL_REVISION.fullmatch(selected) is None:
        raise RunnerCaptureError(f"{field}: expected a full Git revision")
    return selected


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
