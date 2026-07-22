"""Agent-backed runner for executable Agent Pseudocode scripts."""

from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

from . import __version__
from .config import load_config
from .executable import (
    AgentName,
    ExecutableScript,
    JsonValue,
    RunMode,
    parse_executable_file,
    parse_simple_frontmatter,
)
from .lint import lint_snippet
from .model import Diagnostic, LintConfig, Severity, Snippet
from .runner_logging import get_runner_logger

type RunnerAction = Literal[
    "run",
    "check",
    "render-prompt",
    "print-command",
    "replay",
    "rerun",
    "resume-run",
]
type OutcomeFormat = Literal["json", "markdown", "text"]
type ApprovalPolicy = Literal["untrusted", "on-request", "never", "auto-approved-tools"]

OUTCOMES: Final[tuple[str, ...]] = ("Accepted", "Blocked", "NeedsUserDecision")
EXIT_ACCEPTED: Final[int] = 0
EXIT_NEEDS_USER_DECISION: Final[int] = 10
EXIT_BLOCKED: Final[int] = 20
EXIT_VALIDATION_FAILED: Final[int] = 30
EXIT_CONFIG_INVALID: Final[int] = 31
EXIT_AGENT_FAILED: Final[int] = 40
EXIT_OUTPUT_INVALID: Final[int] = 41
EXIT_SAFETY_BLOCKED: Final[int] = 50


def _empty_str_dict() -> dict[str, str]:
    return {}


def _empty_object_dict() -> dict[str, object]:
    return {}


def _empty_str_tuple() -> tuple[str, ...]:
    return ()


LOGGER = get_runner_logger()

OUTCOME_SCHEMA: Final[dict[str, object]] = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": list(OUTCOMES)},
        "reason": {"type": "string"},
        "summary": {"type": "string"},
        "artifacts": {"type": "array", "items": {"type": "string"}},
        "checks_run": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "string"},
    },
    "required": ["outcome", "reason", "summary", "checks_run"],
    "additionalProperties": True,
}


@dataclass(frozen=True, slots=True)
class RunnerOptions:
    """Resolved command-line options for an executable pseudocode run."""

    action: RunnerAction = "run"
    agent: AgentName | None = None
    mode: RunMode | None = None
    workspace: Path | None = None
    allow_dirty: bool = False
    require_clean_git: bool | None = None
    danger_accepted: bool = False
    agent_command: str | None = None
    model: str | None = None
    profile: str | None = None
    sandbox: str | None = None
    claude_bare: bool | None = None
    allowed_tools: tuple[str, ...] = field(default_factory=_empty_str_tuple)
    max_turns: int | None = None
    max_budget_usd: float | None = None
    timeout_seconds: int | None = None
    timeout_idle_seconds: int | None = None
    max_output_bytes: int | None = None
    output_schema: Path | None = None
    run_dir: Path | None = None
    output: Path | None = None
    output_last_message: Path | None = None
    events_path: Path | None = None
    prompt_out: Path | None = None
    schema_out: Path | None = None
    changed_files_out: Path | None = None
    diff_out: Path | None = None
    print_json: bool = False
    outcome_format: OutcomeFormat = "json"
    stream: bool = False
    env: dict[str, str] = field(default_factory=_empty_str_dict)
    approval_policy: ApprovalPolicy | None = None
    add_dirs: tuple[Path, ...] = ()
    ephemeral: bool = False
    hermetic: bool = False
    project_context: bool = False
    require_no_diff: bool = False
    expect_diff: bool = False
    post_checks: tuple[str, ...] = ()
    fail_on_warning: bool = False
    no_hooks: bool = False
    require_hooks: bool = False
    require_mcp: bool = False
    resume: str | None = None
    resume_last: bool = False
    resume_all: bool = False
    lock_name: str | None = None
    retry: int = 0
    quiet: bool = False
    verbose: bool = False
    log_dir: Path | None = None  # Backward-compatible alias for run_dir.


@dataclass(frozen=True, slots=True)
class RunnerInvocation:
    """Concrete invocation after script metadata and CLI overrides are resolved."""

    script: ExecutableScript
    agent: AgentName
    mode: RunMode
    workspace: Path
    args: dict[str, JsonValue]
    passthrough: tuple[str, ...]
    options: RunnerOptions


@dataclass(frozen=True, slots=True)
class AgentCommand:
    """Rendered external command and stdin payload."""

    argv: list[str]
    stdin: str | None
    cwd: Path
    env: dict[str, str]
    schema_path: Path | None = None
    output_last_message_path: Path | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly preview."""

        return {
            "argv": self.argv,
            "stdin": self.stdin,
            "cwd": str(self.cwd),
            "env_overrides": self.env,
            "schema_path": str(self.schema_path) if self.schema_path else None,
            "output_last_message_path": str(self.output_last_message_path)
            if self.output_last_message_path
            else None,
        }


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Raw external agent process result."""

    command: AgentCommand
    returncode: int
    stdout: str
    stderr: str
    final_message: str
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class RunnerOutcome:
    """Parsed normalized outcome."""

    outcome: str
    reason: str
    summary: str
    checks_run: list[str]
    artifacts: list[str]
    evidence: str | None = None
    raw: dict[str, object] = field(default_factory=_empty_object_dict)

    @property
    def exit_code(self) -> int:
        """Map semantic outcome to shell exit status."""

        if self.outcome == "Accepted":
            return EXIT_ACCEPTED
        if self.outcome == "NeedsUserDecision":
            return EXIT_NEEDS_USER_DECISION
        return EXIT_BLOCKED

    def as_dict(self) -> dict[str, object]:
        """Return normalized JSON."""

        payload: dict[str, object] = {
            "outcome": self.outcome,
            "reason": self.reason,
            "summary": self.summary,
            "checks_run": self.checks_run,
            "artifacts": self.artifacts,
        }
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Local validation result for an executable script."""

    diagnostics: list[Diagnostic]

    @property
    def failed(self) -> bool:
        """Return true if validation contains an error."""

        return any(diagnostic.severity == Severity.ERROR for diagnostic in self.diagnostics)

    def failed_with_options(self, options: RunnerOptions) -> bool:
        """Return true when validation fails under runner options."""

        if self.failed:
            return True
        return options.fail_on_warning and any(
            diagnostic.severity == Severity.WARNING for diagnostic in self.diagnostics
        )

    def as_dict(self) -> dict[str, object]:
        """Return JSON-friendly validation payload."""

        errors = sum(1 for diag in self.diagnostics if diag.severity == Severity.ERROR)
        warnings = sum(1 for diag in self.diagnostics if diag.severity == Severity.WARNING)
        return {
            "summary": {
                "diagnostics": len(self.diagnostics),
                "errors": errors,
                "warnings": warnings,
            },
            "diagnostics": [diag.as_dict() for diag in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class PostCheckResult:
    """Result from a runner-enforced post-check command."""

    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "passed": self.passed,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(slots=True)
class RunRecord:
    """Persistent record directory for an agent-backed run."""

    run_id: str
    directory: Path
    events_path: Path
    started_at: str
    manifest: dict[str, object]

    def write_json(self, name: str, payload: object) -> Path:
        path = self.directory / name
        _write_json(path, payload)
        return path

    def write_text(self, name: str, text: str) -> Path:
        path = self.directory / name
        _write_text(path, text)
        return path

    def event(self, event: str, **payload: object) -> None:
        record: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "event": event,
        }
        record.update(payload)
        _append_jsonl(self.events_path, record)

    def close(self, *, exit_code: int, outcome: RunnerOutcome | None) -> None:
        self.manifest["ended_at"] = datetime.now(UTC).isoformat()
        self.manifest["exit_code"] = exit_code
        if outcome is not None:
            self.manifest["outcome"] = outcome.outcome
            self.manifest["reason"] = outcome.reason
        self.write_json("manifest.json", self.manifest)


def load_invocation(
    script_path: Path,
    *,
    options: RunnerOptions,
    raw_script_args: list[str],
    arg_overrides: Mapping[str, JsonValue] | None = None,
) -> RunnerInvocation:
    """Load and resolve a runner invocation."""

    script = parse_executable_file(script_path.expanduser().resolve())
    agent = _resolve_agent(script, options)
    mode = options.mode or script.metadata.mode
    workspace = _resolve_workspace(script, options.workspace)
    args, passthrough = parse_script_args(raw_script_args)
    if arg_overrides:
        args.update(dict(arg_overrides))
    args = resolve_script_arg_schema(script, args)
    return RunnerInvocation(
        script=script,
        agent=agent,
        mode=mode,
        workspace=workspace,
        args=args,
        passthrough=passthrough,
        options=options,
    )


def validate_script(script: ExecutableScript, config: LintConfig | None = None) -> ValidationResult:
    """Validate an executable script's pseudocode body."""

    effective = config or _load_config_safely(script.path)
    snippet = Snippet(
        path=script.path,
        text=script.body,
        start_line=script.body_start_line,
        name=script.path.name,
        language=script.path.suffix.lstrip("."),
    )
    return ValidationResult(lint_snippet(snippet, effective))


def render_prompt(invocation: RunnerInvocation) -> str:
    """Render the provider-neutral task prompt fed to Claude Code or Codex CLI."""

    metadata = invocation.script.metadata.as_prompt_dict()
    args_payload: dict[str, JsonValue] = dict(invocation.args)
    schema = json.dumps(OUTCOME_SCHEMA, indent=2, sort_keys=True)
    options = invocation.options
    prompt_parts = [
        "You are executing an Agent Pseudocode script.",
        "",
        "Execution contract:",
        "- Treat the pseudocode as the control-flow source of truth.",
        "- Follow all guards, branches, bounded loops, stop conditions, and terminal outcomes.",
        "- Do not convert bounded loops into unbounded loops.",
        "- Do not bypass repository hooks, validation, CI, or safety checks.",
        "- If the pseudocode conflicts with repository instructions or reality, stop and return NeedsUserDecision or Blocked.",
        "- Before returning Accepted, run the verification actions required by the pseudocode.",
        "- Return exactly one JSON object matching the outcome schema; do not wrap it in Markdown.",
        "",
        "Runner policy:",
        f"- project_context: {not options.hermetic or options.project_context}",
        f"- hermetic: {options.hermetic}",
        f"- no_hooks_requested: {options.no_hooks}",
        f"- hooks_required: {options.require_hooks}",
        f"- mcp_required: {options.require_mcp}",
        f"- require_no_diff: {options.require_no_diff}",
        f"- expect_diff: {options.expect_diff}",
        f"- post_checks: {json.dumps(list(options.post_checks), sort_keys=True)}",
        f"- additional_write_dirs: {json.dumps([str(path) for path in options.add_dirs], sort_keys=True)}",
        "",
        "Invocation:",
        f"- toolkit_version: {__version__}",
        f"- script_path: {invocation.script.path}",
        f"- selected_agent: {invocation.agent}",
        f"- execution_mode: {invocation.mode}",
        f"- workspace: {invocation.workspace}",
        f"- metadata: {json.dumps(metadata, sort_keys=True)}",
        f"- script_args: {json.dumps(args_payload, sort_keys=True)}",
        f"- passthrough_args: {json.dumps(list(invocation.passthrough), sort_keys=True)}",
        "",
        "Allowed terminal outcomes:",
        "- Accepted: the requested process completed and verification passed.",
        "- Blocked: the process cannot continue without violating the contract or because verification failed.",
        "- NeedsUserDecision: user input or approval is required before continuing.",
        "",
        "Outcome JSON schema:",
        "```json",
        schema,
        "```",
        "",
        "Pseudocode:",
        "```apseudo",
        invocation.script.body.rstrip(),
        "```",
        "",
        "Return only the final JSON outcome object.",
    ]
    return "\n".join(prompt_parts).rstrip() + "\n"


def build_agent_command(invocation: RunnerInvocation, prompt: str, temp_dir: Path) -> AgentCommand:
    """Build the external command for the selected agent without executing it."""

    if invocation.agent == "claude":
        return _build_claude_command(invocation, prompt)
    return _build_codex_command(invocation, prompt, temp_dir)


def execute_invocation(invocation: RunnerInvocation) -> tuple[RunnerOutcome | None, int, str]:
    """Validate, execute, parse, and map a runner invocation."""

    LOGGER.info(
        "execute_start",
        script=str(invocation.script.path),
        agent=invocation.agent,
        mode=invocation.mode,
    )
    validation = validate_script(invocation.script)
    if validation.failed_with_options(invocation.options):
        return (
            None,
            EXIT_VALIDATION_FAILED,
            json.dumps(validation.as_dict(), indent=2, sort_keys=True),
        )

    safety_error = check_safety(invocation)
    if safety_error is not None:
        return None, EXIT_SAFETY_BLOCKED, safety_error

    prompt = render_prompt(invocation)
    if invocation.options.prompt_out:
        _write_text(invocation.options.prompt_out, prompt)
    if invocation.options.schema_out:
        _write_text(invocation.options.schema_out, outcome_schema_json())

    run_record: RunRecord | None = None
    outcome: RunnerOutcome | None = None
    exit_code = EXIT_AGENT_FAILED
    with _workspace_lock(invocation), tempfile.TemporaryDirectory(prefix="apseudo-run-") as raw_tmp:
        temp_dir = Path(raw_tmp)
        command = build_agent_command(invocation, prompt, temp_dir)
        run_record = create_run_record(invocation, prompt, validation, command)
        if run_record is not None:
            command.env["APSEUDO_RUN_ID"] = run_record.run_id
            command.env["APSEUDO_RUN_DIR"] = str(run_record.directory)
            run_record.event("agent_start", argv=command.argv)
        attempts = max(1, invocation.options.retry + 1)
        agent_result: AgentResult | None = None
        for attempt in range(1, attempts + 1):
            if run_record is not None:
                run_record.event("agent_attempt", attempt=attempt, max_attempts=attempts)
            agent_result = run_agent_command(
                command,
                timeout=invocation.options.timeout_seconds,
                stream=invocation.options.stream,
                events_path=_events_path(invocation, run_record),
                max_output_bytes=invocation.options.max_output_bytes,
            )
            if agent_result.returncode == 0:
                break
            if attempt < attempts and run_record is not None:
                run_record.event("agent_retry", returncode=agent_result.returncode)
        assert agent_result is not None
        _write_agent_artifacts(invocation, run_record, agent_result)
        if agent_result.returncode != 0:
            exit_code = EXIT_AGENT_FAILED
            output = _agent_failure_message(invocation.agent, agent_result)
            if run_record is not None:
                run_record.event("agent_failed", returncode=agent_result.returncode)
                run_record.close(exit_code=exit_code, outcome=None)
            LOGGER.error("agent_failed", agent=invocation.agent, returncode=agent_result.returncode)
            return None, exit_code, output

        outcome = parse_runner_outcome(_combined_final_output(agent_result))
        if outcome is None:
            exit_code = EXIT_OUTPUT_INVALID
            output = _invalid_output_message(agent_result)
            if run_record is not None:
                run_record.event("output_invalid")
                run_record.close(exit_code=exit_code, outcome=None)
            return None, exit_code, output

        post_results = run_post_checks(invocation)
        if run_record is not None:
            run_record.write_json("post-checks.json", [item.as_dict() for item in post_results])
        if any(not item.passed for item in post_results):
            failed = [item.command for item in post_results if not item.passed]
            outcome = RunnerOutcome(
                outcome="Blocked",
                reason="runner post-check failed",
                summary="Runner-enforced post-checks failed after agent completion.",
                checks_run=[*outcome.checks_run, *[item.command for item in post_results]],
                artifacts=outcome.artifacts,
                evidence="; ".join(failed),
                raw=outcome.raw,
            )

        diff_error = enforce_diff_policy(invocation)
        if diff_error is not None:
            outcome = RunnerOutcome(
                outcome="Blocked",
                reason=diff_error,
                summary="Runner diff policy failed after agent completion.",
                checks_run=outcome.checks_run,
                artifacts=outcome.artifacts,
                evidence=_git_diff(invocation.workspace),
                raw=outcome.raw,
            )
        _write_post_run_files(invocation, run_record, outcome)
        exit_code = outcome.exit_code
        if run_record is not None:
            run_record.event("completed", outcome=outcome.outcome, exit_code=exit_code)
            run_record.close(exit_code=exit_code, outcome=outcome)
        LOGGER.info("execute_complete", outcome=outcome.outcome, exit_code=exit_code)
        return outcome, exit_code, format_outcome(outcome, invocation.options.outcome_format)


def run_agent_command(
    command: AgentCommand,
    *,
    timeout: int | None = None,
    stream: bool = False,
    events_path: Path | None = None,
    max_output_bytes: int | None = None,
) -> AgentResult:
    """Run the external agent command."""

    executable = command.argv[0]
    if shutil.which(executable) is None:
        return AgentResult(command, 127, "", f"agent executable not found: {executable}", "")
    env = os.environ.copy()
    env.update(command.env)
    start = time.monotonic()
    if stream:
        return _run_agent_command_streaming(
            command,
            env=env,
            timeout=timeout,
            events_path=events_path,
            max_output_bytes=max_output_bytes,
            start=start,
        )
    completed = subprocess.run(
        command.argv,
        cwd=command.cwd,
        env=env,
        input=command.stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    stdout = _limit_text(completed.stdout, max_output_bytes)
    stderr = _limit_text(completed.stderr, max_output_bytes)
    if events_path is not None:
        if stdout:
            _append_jsonl(events_path, {"timestamp": _now(), "event": "stdout", "text": stdout})
        if stderr:
            _append_jsonl(events_path, {"timestamp": _now(), "event": "stderr", "text": stderr})
        _append_jsonl(
            events_path,
            {"timestamp": _now(), "event": "process_exit", "returncode": completed.returncode},
        )
    final_message = ""
    if command.output_last_message_path and command.output_last_message_path.exists():
        final_message = command.output_last_message_path.read_text(encoding="utf-8")
    return AgentResult(
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        final_message=final_message,
        duration_seconds=time.monotonic() - start,
    )


def check_safety(invocation: RunnerInvocation) -> str | None:
    """Return a safety/configuration error string, or None when safe to proceed."""

    if invocation.mode == "danger" and not invocation.options.danger_accepted:
        return "danger mode requires --i-understand-danger"
    if invocation.options.no_hooks and invocation.options.require_hooks:
        return "--no-hooks conflicts with --require-hooks"
    if invocation.options.require_hooks and not _hooks_configured(invocation):
        return f"{invocation.agent} hooks were required but no project hook config was found"
    if invocation.options.require_mcp and not (invocation.workspace / ".mcp.json").exists():
        return "MCP was required but .mcp.json was not found in the workspace"
    requires_clean = (
        invocation.options.require_clean_git
        if invocation.options.require_clean_git is not None
        else invocation.script.metadata.requires_clean_git
    )
    allow_dirty = invocation.options.allow_dirty or invocation.script.metadata.allow_dirty_git
    if requires_clean and not allow_dirty and _git_dirty(invocation.workspace):
        return "workspace has uncommitted changes; use --allow-dirty only when intentional"
    if invocation.agent == "codex":
        sandbox = _codex_sandbox(invocation)
        if sandbox == "danger-full-access" and invocation.mode != "danger":
            return "Codex danger-full-access sandbox requires --mode danger"
    if invocation.options.lock_name and not _safe_lock_name(invocation.options.lock_name):
        return "--lock may contain only letters, digits, dash, underscore, and dot"
    return None


def parse_script_args(raw_args: list[str]) -> tuple[dict[str, JsonValue], tuple[str, ...]]:
    """Parse ``key=value`` script arguments and preserve non key/value passthrough args."""

    values: dict[str, JsonValue] = {}
    passthrough: list[str] = []
    for raw in raw_args:
        if "=" in raw and not raw.startswith("-"):
            key, value = raw.split("=", 1)
            values[key] = _parse_arg_scalar(value)
        else:
            passthrough.append(raw)
    return values, tuple(passthrough)


def resolve_script_arg_schema(
    script: ExecutableScript,
    values: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    """Apply frontmatter ``args`` defaults and validate required arguments."""

    resolved: dict[str, JsonValue] = dict(values)
    schema = script.metadata.args
    for name, raw_spec in schema.items():
        spec: Mapping[str, JsonValue] = raw_spec if isinstance(raw_spec, dict) else {}
        if name not in resolved:
            default = spec.get("default")
            if default is not None:
                resolved[name] = default
        required = bool(spec.get("required"))
        if required and name not in resolved:
            raise ValueError(f"missing required script argument: {name}")
        if name in resolved:
            resolved[name] = _coerce_arg_value(name, resolved[name], spec)
    return resolved


def load_arg_values(paths: Sequence[Path]) -> dict[str, JsonValue]:
    """Load script argument values from JSON or simple YAML-like files."""

    merged: dict[str, JsonValue] = {}
    for path in paths:
        text = path.expanduser().read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError(f"argument file must contain an object: {path}")
            merged.update(cast(dict[str, JsonValue], parsed))
        else:
            merged.update(parse_simple_frontmatter(text))
    return merged


def parse_runner_outcome(text: str) -> RunnerOutcome | None:
    """Parse and minimally validate a final structured outcome."""

    payload = _extract_json_object(text)
    if payload is None:
        return None
    structured = payload.get("structured_output")
    if isinstance(structured, dict):
        payload = cast(dict[str, object], structured)
    elif isinstance(payload.get("result"), str):
        nested = _extract_json_object(cast(str, payload["result"]))
        if nested is not None:
            payload = nested

    outcome = payload.get("outcome")
    reason = payload.get("reason")
    summary = payload.get("summary")
    checks = payload.get("checks_run")
    artifacts = payload.get("artifacts", [])
    evidence = payload.get("evidence")
    if outcome not in OUTCOMES:
        return None
    if not isinstance(reason, str) or not isinstance(summary, str):
        return None
    if not isinstance(checks, list):
        return None
    check_items = cast(list[object], checks)
    if not all(isinstance(item, str) for item in check_items):
        return None
    if not isinstance(artifacts, list):
        return None
    artifact_items = cast(list[object], artifacts)
    if not all(isinstance(item, str) for item in artifact_items):
        return None
    return RunnerOutcome(
        outcome=cast(str, outcome),
        reason=reason,
        summary=summary,
        checks_run=cast(list[str], check_items),
        artifacts=cast(list[str], artifact_items),
        evidence=evidence if isinstance(evidence, str) else None,
        raw=payload,
    )


def outcome_schema_json() -> str:
    """Return the runner outcome JSON Schema."""

    return json.dumps(OUTCOME_SCHEMA, indent=2, sort_keys=True) + "\n"


def shell_join(argv: list[str]) -> str:
    """Return a shell-escaped command preview."""

    return shlex.join(argv)


def format_outcome(outcome: RunnerOutcome, output_format: OutcomeFormat) -> str:
    """Format a normalized outcome for stdout or files."""

    if output_format == "json":
        return json.dumps(outcome.as_dict(), indent=2, sort_keys=True)
    if output_format == "markdown":
        lines = [
            f"# {outcome.outcome}",
            "",
            f"**Reason:** {outcome.reason}",
            "",
            outcome.summary,
            "",
            "## Checks run",
        ]
        lines.extend(f"- `{check}`" for check in outcome.checks_run)
        if outcome.artifacts:
            lines.append("")
            lines.append("## Artifacts")
            lines.extend(f"- `{artifact}`" for artifact in outcome.artifacts)
        if outcome.evidence:
            lines.extend(["", "## Evidence", "", outcome.evidence])
        return "\n".join(lines).rstrip() + "\n"
    return f"{outcome.outcome}: {outcome.reason}\n{outcome.summary}\n"


def create_run_record(
    invocation: RunnerInvocation,
    prompt: str,
    validation: ValidationResult,
    command: AgentCommand,
) -> RunRecord | None:
    """Create and initialize a persistent run record directory when requested."""

    root = invocation.options.run_dir or invocation.options.log_dir
    if root is None:
        return None
    started = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    script_name = invocation.script.metadata.name or invocation.script.path.stem
    run_id = f"{started}-{_slug(script_name)}-{invocation.agent}-{uuid.uuid4().hex[:8]}"
    directory = root.expanduser().resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    events_path = invocation.options.events_path or (directory / "events.jsonl")
    manifest: dict[str, object] = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "toolkit_version": __version__,
        "script_path": str(invocation.script.path),
        "script_name": script_name,
        "agent": invocation.agent,
        "mode": invocation.mode,
        "workspace": str(invocation.workspace),
        "args": invocation.args,
        "passthrough": list(invocation.passthrough),
        "prompt_sha256": _sha256(prompt),
        "git_head": _git_head(invocation.workspace),
    }
    record = RunRecord(
        run_id=run_id,
        directory=directory,
        events_path=events_path,
        started_at=cast(str, manifest["started_at"]),
        manifest=manifest,
    )
    record.write_json("manifest.json", manifest)
    record.write_text("script.apseudo", invocation.script.path.read_text(encoding="utf-8"))
    record.write_text("rendered-prompt.md", prompt)
    record.write_json("agent-command.json", command.as_dict())
    record.write_json("validation-before.json", validation.as_dict())
    record.event("created")
    return record


def run_post_checks(invocation: RunnerInvocation) -> list[PostCheckResult]:
    """Run deterministic post-checks after agent execution."""

    results: list[PostCheckResult] = []
    for command in invocation.options.post_checks:
        completed = subprocess.run(
            command,
            cwd=invocation.workspace,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
            timeout=invocation.options.timeout_seconds,
        )
        results.append(
            PostCheckResult(
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
    return results


def enforce_diff_policy(invocation: RunnerInvocation) -> str | None:
    """Return a diff policy error, or None when policy passes."""

    changed = _git_changed_files(invocation.workspace)
    if invocation.options.require_no_diff and changed:
        return "--require-no-diff was set but the workspace has Git changes"
    if invocation.options.expect_diff and not changed:
        return "--expect-diff was set but the workspace has no Git changes"
    return None


def script_help(script: ExecutableScript, *, prog: str | None = None) -> str:
    """Return script-specific help generated from executable frontmatter."""

    command = prog or script.path.name
    name = script.metadata.name or script.path.stem
    description = script.metadata.description or "Executable Agent Pseudocode script."
    lines = [
        f"{name} — {description}",
        "",
        "Usage:",
        f"  {command} [RUNNER OPTIONS] -- [ARG=VALUE]...",
        "",
        "Runner shortcuts:",
        "  --claude              Run through Claude Code headless mode.",
        "  --codex               Run through Codex CLI exec mode.",
        "  --plan | --review     Read-only intent.",
        "  --apply               Permit workspace edits according to provider sandboxing.",
        "  --check               Validate this script without launching an agent.",
        "  --render-prompt       Print the exact prompt that would be sent.",
        "",
    ]
    if script.metadata.args:
        lines.append("Arguments:")
        for arg_name, raw in script.metadata.args.items():
            if not isinstance(raw, dict):
                lines.append(f"  {arg_name}")
                continue
            required = "required" if raw.get("required") else "optional"
            arg_type = raw.get("type", "string")
            default = raw.get("default")
            description = raw.get("description", "")
            suffix = f" Default: {default!r}." if default is not None else ""
            lines.append(f"  {arg_name} ({arg_type}, {required})  {description}{suffix}")
    else:
        lines.append("Arguments:")
        lines.append("  No script-specific arguments are declared.")
    return "\n".join(lines).rstrip() + "\n"


# --- Agent command builders -------------------------------------------------


def _build_claude_command(invocation: RunnerInvocation, prompt: str) -> AgentCommand:
    options = invocation.options
    provider = invocation.script.metadata.agent_options("claude")
    command = options.agent_command or _string_option(provider, "command", default="claude")
    argv = [command]
    bare = _bool_option(provider, "bare", default=False)
    if options.claude_bare is not None:
        bare = options.claude_bare
    if options.hermetic:
        bare = True
    if options.project_context:
        bare = False
    if bare:
        argv.append("--bare")
    argv.extend(["-p", prompt])
    if options.resume_last:
        argv.append("--continue")
    if options.resume:
        argv.extend(["--resume", options.resume])
    output_format = (
        "stream-json"
        if options.stream
        else _string_option(provider, "output_format", default="json")
    )
    argv.extend(["--output-format", output_format])
    if options.stream:
        argv.extend(["--verbose", "--include-partial-messages"])
    argv.extend(["--json-schema", outcome_schema_json().strip()])
    model = options.model or _string_option(provider, "model", default="")
    if model:
        argv.extend(["--model", model])
    allowed_tools = _allowed_tools(invocation, provider)
    if allowed_tools:
        argv.extend(["--allowedTools", ",".join(allowed_tools)])
    permission_mode = _string_option(
        provider, "permission_mode", default=""
    ) or _claude_permission_mode(
        invocation.mode,
        options.approval_policy,
    )
    if permission_mode:
        argv.extend(["--permission-mode", permission_mode])
    max_turns = options.max_turns or _int_option(provider, "max_turns")
    if max_turns is not None:
        argv.extend(["--max-turns", str(max_turns)])
    max_budget = options.max_budget_usd or _float_option(provider, "max_budget_usd")
    if max_budget is not None:
        argv.extend(["--max-budget-usd", str(max_budget)])
    return AgentCommand(argv=argv, stdin=None, cwd=invocation.workspace, env=dict(options.env))


def _build_codex_command(invocation: RunnerInvocation, prompt: str, temp_dir: Path) -> AgentCommand:
    options = invocation.options
    provider = invocation.script.metadata.agent_options("codex")
    command = options.agent_command or _string_option(provider, "command", default="codex")
    schema_path = options.output_schema or (temp_dir / "outcome.schema.json")
    if options.output_schema is None:
        schema_path.write_text(outcome_schema_json(), encoding="utf-8")
    final_message_path = options.output_last_message or (temp_dir / "final-message.json")
    argv = [command, "exec"]
    if options.resume or options.resume_last:
        argv.append("resume")
        if options.resume_last:
            argv.append("--last")
        if options.resume_all:
            argv.append("--all")
        if options.resume:
            argv.append(options.resume)
    argv.extend(["--cd", str(invocation.workspace)])
    argv.append("--json")
    argv.extend(["--output-last-message", str(final_message_path)])
    argv.extend(["--output-schema", str(schema_path)])
    sandbox = _codex_sandbox(invocation)
    if sandbox:
        argv.extend(["--sandbox", sandbox])
    model = options.model or _string_option(provider, "model", default="")
    if model:
        argv.extend(["--model", model])
    profile = options.profile or _string_option(provider, "profile", default="")
    if profile:
        argv.extend(["--profile", profile])
    approval = options.approval_policy or _string_option(provider, "approval_policy", default="")
    if approval and approval in {"untrusted", "on-request", "never"}:
        argv.extend(["--ask-for-approval", approval])
    if options.ephemeral:
        argv.append("--ephemeral")
    if options.hermetic:
        argv.append("--ignore-user-config")
    if options.no_hooks:
        argv.append("--ignore-rules")
    if _bool_option(provider, "skip_git_repo_check", default=False):
        argv.append("--skip-git-repo-check")
    for item in [*_list_option(provider, "add_dir"), *[str(path) for path in options.add_dirs]]:
        argv.extend(["--add-dir", item])
    argv.append("-")
    return AgentCommand(
        argv=argv,
        stdin=prompt,
        cwd=invocation.workspace,
        env=dict(options.env),
        schema_path=schema_path,
        output_last_message_path=final_message_path,
    )


# --- Private helpers --------------------------------------------------------


def _run_agent_command_streaming(
    command: AgentCommand,
    *,
    env: Mapping[str, str],
    timeout: int | None,
    events_path: Path | None,
    max_output_bytes: int | None,
    start: float,
) -> AgentResult:
    process = subprocess.Popen(
        command.argv,
        cwd=command.cwd,
        env=dict(env),
        stdin=subprocess.PIPE if command.stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if command.stdin is not None and process.stdin is not None:
        process.stdin.write(command.stdin)
        process.stdin.close()
    output_parts: list[str] = []
    assert process.stdout is not None
    deadline = time.monotonic() + timeout if timeout is not None else None
    for line in process.stdout:
        output_parts.append(line)
        if events_path is not None:
            _append_jsonl(
                events_path, {"timestamp": _now(), "event": "stream", "text": line.rstrip("\n")}
            )
        print(line, end="")
        if deadline is not None and time.monotonic() > deadline:
            process.kill()
            break
    returncode = process.wait(timeout=5)
    stdout = _limit_text("".join(output_parts), max_output_bytes)
    if events_path is not None:
        _append_jsonl(
            events_path, {"timestamp": _now(), "event": "process_exit", "returncode": returncode}
        )
    final_message = ""
    if command.output_last_message_path and command.output_last_message_path.exists():
        final_message = command.output_last_message_path.read_text(encoding="utf-8")
    return AgentResult(command, returncode, stdout, "", final_message, time.monotonic() - start)


def _write_agent_artifacts(
    invocation: RunnerInvocation,
    record: RunRecord | None,
    result: AgentResult,
) -> None:
    if record is not None:
        record.write_text("stdout.log", result.stdout)
        record.write_text("stderr.log", result.stderr)
        if result.final_message:
            record.write_text("final-message.txt", result.final_message)
    if invocation.options.output_last_message and result.final_message:
        _write_text(invocation.options.output_last_message, result.final_message)


def _write_post_run_files(
    invocation: RunnerInvocation,
    record: RunRecord | None,
    outcome: RunnerOutcome,
) -> None:
    output_text = format_outcome(outcome, invocation.options.outcome_format)
    if invocation.options.output:
        _write_text(invocation.options.output, output_text)
    if record is not None:
        record.write_text(
            "outcome.json" if invocation.options.outcome_format == "json" else "outcome.txt",
            output_text,
        )
    changed_files = "\n".join(_git_changed_files(invocation.workspace)) + "\n"
    diff = _git_diff(invocation.workspace)
    if invocation.options.changed_files_out:
        _write_text(invocation.options.changed_files_out, changed_files)
    if invocation.options.diff_out:
        _write_text(invocation.options.diff_out, diff)
    if record is not None:
        record.write_text("changed-files.txt", changed_files)
        record.write_text("git-diff.patch", diff)
        after = validate_script(invocation.script)
        record.write_json("validation-after.json", after.as_dict())


def _events_path(invocation: RunnerInvocation, record: RunRecord | None) -> Path | None:
    if invocation.options.events_path:
        return invocation.options.events_path
    if record is not None:
        return record.events_path
    return None


def _combined_final_output(result: AgentResult) -> str:
    if result.final_message.strip():
        return result.final_message
    if result.stdout.strip():
        return result.stdout
    return result.stderr


def _extract_json_object(text: str) -> dict[str, object] | None:
    candidates = [text.strip()]
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        candidates.insert(0, fence_match.group(1).strip())
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            candidates.insert(0, stripped)
    object_match = re.search(r"\{.*\}", text, re.DOTALL)
    if object_match:
        candidates.append(object_match.group(0))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return cast(dict[str, object], parsed)
    return None


def _git_root(start: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _git_head(root: Path) -> str | None:
    if _git_root(root) is None:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _git_dirty(root: Path) -> bool:
    return bool(_git_changed_files(root))


def _git_changed_files(root: Path) -> list[str]:
    if _git_root(root) is None:
        return []
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    files: list[str] = []
    for line in result.stdout.splitlines():
        text = line[3:] if len(line) > 3 else line
        if text:
            files.append(text)
    return files


def _git_diff(root: Path) -> str:
    if _git_root(root) is None:
        return ""
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--binary"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout


def _load_config_safely(path: Path) -> LintConfig:
    try:
        return load_config(start=path)
    except Exception:
        return LintConfig()


def _agent_failure_message(agent: AgentName, result: AgentResult) -> str:
    return (
        f"{agent} command failed with exit status {result.returncode}\n\n"
        f"Command: {shell_join(result.command.argv)}\n\n"
        f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    ).rstrip()


def _invalid_output_message(result: AgentResult) -> str:
    final_output = _combined_final_output(result)
    return "agent final output did not match the runner outcome schema\n\n" + final_output


def _codex_sandbox(invocation: RunnerInvocation) -> str:
    if invocation.options.sandbox:
        return invocation.options.sandbox
    provider = invocation.script.metadata.agent_options("codex")
    configured = _string_option(provider, "sandbox", default="")
    if configured:
        return configured
    if invocation.mode in {"plan", "review"}:
        return "read-only"
    if invocation.mode == "apply":
        return "workspace-write"
    return "danger-full-access"


def _claude_permission_mode(mode: RunMode, approval_policy: ApprovalPolicy | None) -> str:
    if approval_policy == "auto-approved-tools":
        return "acceptEdits"
    if mode in {"plan", "review"}:
        return "plan"
    if mode == "apply":
        return "acceptEdits"
    return ""


def _allowed_tools(invocation: RunnerInvocation, provider: dict[str, JsonValue]) -> list[str]:
    if invocation.options.allowed_tools:
        return list(invocation.options.allowed_tools)
    configured = _list_option(provider, "allowed_tools")
    if configured:
        return configured
    if invocation.mode in {"plan", "review"}:
        return ["Read", "Bash(git status *)", "Bash(git diff *)"]
    if invocation.mode == "apply":
        return ["Read", "Edit", "Write", "Bash"]
    return []


def _resolve_agent(script: ExecutableScript, options: RunnerOptions) -> AgentName:
    if options.agent is not None:
        return options.agent
    env_agent = os.environ.get("APSEUDO_AGENT")
    if env_agent in {"claude", "codex"}:
        return cast(AgentName, env_agent)
    if script.metadata.default_agent is not None:
        return script.metadata.default_agent
    raise ValueError(
        "no agent selected; pass --claude, --codex, --agent, set APSEUDO_AGENT, or set default_agent"
    )


def _resolve_workspace(script: ExecutableScript, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    raw = script.metadata.workspace
    if raw == "cwd":
        return Path.cwd().resolve()
    if raw == "script_dir":
        return script.path.parent.resolve()
    if raw == "git_root":
        return _git_root(script.path.parent) or script.path.parent.resolve()
    return (script.path.parent / str(raw)).expanduser().resolve()


def _string_option(options: dict[str, JsonValue], key: str, *, default: str) -> str:
    value = options.get(key, default)
    return value if isinstance(value, str) else default


def _bool_option(options: dict[str, JsonValue], key: str, *, default: bool) -> bool:
    value = options.get(key, default)
    return value if isinstance(value, bool) else default


def _int_option(options: dict[str, JsonValue], key: str) -> int | None:
    value = options.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float_option(options: dict[str, JsonValue], key: str) -> float | None:
    value = options.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _list_option(options: dict[str, JsonValue], key: str) -> list[str]:
    value = options.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def _parse_arg_scalar(value: str) -> JsonValue:
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _coerce_arg_value(name: str, value: JsonValue, spec: Mapping[str, JsonValue]) -> JsonValue:
    kind = spec.get("type", "string")
    if not isinstance(kind, str):
        kind = "string"
    try:
        if kind in {"string", "path"}:
            coerced: JsonValue = str(value)
        elif kind in {"int", "integer"}:
            coerced = int(cast(str | int | float | bool, value))
        elif kind in {"float", "number"}:
            coerced = float(cast(str | int | float | bool, value))
        elif kind in {"bool", "boolean"}:
            if isinstance(value, bool):
                coerced = value
            elif isinstance(value, str):
                coerced = value.lower() in {"1", "true", "yes", "on"}
            else:
                coerced = bool(value)
        else:
            coerced = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid value for argument {name}: expected {kind}") from exc
    allowed = spec.get("allowed_values") or spec.get("choices")
    if isinstance(allowed, list) and coerced not in allowed:
        raise ValueError(f"invalid value for argument {name}: expected one of {allowed}")
    return coerced


def _write_text(path: Path, text: str) -> None:
    path.expanduser().parent.mkdir(parents=True, exist_ok=True)
    path.expanduser().write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.expanduser().parent.mkdir(parents=True, exist_ok=True)
    with path.expanduser().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", text).strip("-") or "script"


def _limit_text(text: str, max_bytes: int | None) -> str:
    if max_bytes is None:
        return text
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    return (
        data[:max_bytes].decode("utf-8", errors="replace") + "\n[apseudo-run: output truncated]\n"
    )


def _hooks_configured(invocation: RunnerInvocation) -> bool:
    if invocation.agent == "claude":
        return (invocation.workspace / ".claude" / "settings.json").exists()
    return (invocation.workspace / ".codex" / "hooks.json").exists()


def _safe_lock_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", name))


@contextlib.contextmanager
def _workspace_lock(invocation: RunnerInvocation) -> Generator[None]:
    lock_name = invocation.options.lock_name
    if not lock_name:
        yield
        return
    lock_dir = invocation.workspace / ".apseudo" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{lock_name}.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"runner lock already held: {lock_name}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\nstarted_at={_now()}\n")
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.unlink()
