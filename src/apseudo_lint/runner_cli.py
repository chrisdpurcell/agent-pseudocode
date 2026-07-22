"""Command-line entry point for executable Agent Pseudocode scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

from . import __version__
from .executable import AgentName, JsonValue, RunMode, parse_executable_file
from .runner import (
    EXIT_CONFIG_INVALID,
    EXIT_VALIDATION_FAILED,
    ApprovalPolicy,
    OutcomeFormat,
    RunnerAction,
    RunnerOptions,
    build_agent_command,
    check_safety,
    execute_invocation,
    load_arg_values,
    load_invocation,
    outcome_schema_json,
    render_prompt,
    script_help,
    shell_join,
    validate_script,
)


def build_parser(prog: str = "apseudo-run") -> argparse.ArgumentParser:
    """Build the apseudo-run parser."""

    parser = argparse.ArgumentParser(
        prog=prog,
        description="Execute validated Agent Pseudocode scripts through headless Claude Code or Codex CLI.",
        epilog="Use `--` before script arguments, for example: apseudo-run --codex ./fix.apseudo -- target=src`.",
    )
    parser.add_argument(
        "script", type=Path, nargs="?", help="Executable .apseudo script to validate and run."
    )
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--claude", action="store_true", help="Run with Claude Code (`claude -p`)."
    )
    agent_group.add_argument(
        "--codex", action="store_true", help="Run with Codex CLI (`codex exec`)."
    )
    agent_group.add_argument("--agent", choices=("claude", "codex"), help="Agent backend to use.")

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--check", action="store_true", help="Validate the script and print diagnostics only."
    )
    action_group.add_argument(
        "--render-prompt",
        action="store_true",
        help="Render the prompt that would be sent to the agent.",
    )
    action_group.add_argument(
        "--print-command",
        action="store_true",
        help="Print the external agent command without running it.",
    )
    action_group.add_argument(
        "--schema", action="store_true", help="Print the expected outcome JSON Schema and exit."
    )
    action_group.add_argument(
        "--replay", type=Path, help="Print a saved run record summary without executing an agent."
    )
    action_group.add_argument(
        "--rerun", type=Path, help="Re-run the script snapshot stored in a run record."
    )
    action_group.add_argument(
        "--resume-run",
        type=Path,
        help="Resume the script snapshot stored in a run record when provider metadata is available.",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mode", choices=("plan", "review", "apply", "danger"), help="Execution mode override."
    )
    mode_group.add_argument("--plan", action="store_true", help="Shortcut for --mode plan.")
    mode_group.add_argument("--review", action="store_true", help="Shortcut for --mode review.")
    mode_group.add_argument("--apply", action="store_true", help="Shortcut for --mode apply.")
    mode_group.add_argument("--danger", action="store_true", help="Shortcut for --mode danger.")

    parser.add_argument("--workspace", type=Path, help="Workspace directory override.")
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Allow runs when the Git workspace is dirty."
    )
    parser.add_argument(
        "--require-clean-git",
        action="store_true",
        help="Require a clean Git workspace before executing.",
    )
    parser.add_argument(
        "--i-understand-danger", action="store_true", help="Required with --mode danger."
    )
    parser.add_argument("--agent-command", help="Override the agent executable path/name.")
    parser.add_argument("--model", help="Agent model override, passed through when supported.")
    parser.add_argument("--profile", help="Codex profile override.")
    parser.add_argument(
        "--sandbox",
        help="Codex sandbox override: read-only, workspace-write, or danger-full-access.",
    )
    parser.add_argument(
        "--approval-policy",
        choices=("untrusted", "on-request", "never", "auto-approved-tools"),
        help="Provider-neutral approval policy intent.",
    )
    parser.add_argument(
        "--add-dir",
        type=Path,
        action="append",
        default=[],
        help="Additional directory to grant/write-reference. Repeatable.",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Ask supported providers not to persist session rollout files.",
    )
    context_group = parser.add_mutually_exclusive_group()
    context_group.add_argument(
        "--hermetic",
        action="store_true",
        help="Prefer explicit runner context over project auto-discovery.",
    )
    context_group.add_argument(
        "--project-context",
        action="store_true",
        help="Prefer provider project context such as repo instructions, hooks, MCP, and skills.",
    )
    parser.add_argument("--claude-bare", action="store_true", help="Use Claude Code --bare mode.")
    parser.add_argument(
        "--claude-project",
        action="store_true",
        help="Force Claude project-context mode; disables frontmatter bare=true.",
    )
    parser.add_argument(
        "--allowed-tool", action="append", default=[], help="Claude allowed tool entry. Repeatable."
    )
    parser.add_argument("--max-turns", type=int, help="Claude Code max-turns override.")
    parser.add_argument("--max-budget-usd", type=float, help="Claude Code budget override.")
    parser.add_argument("--timeout-seconds", type=int, help="External agent process timeout.")
    parser.add_argument(
        "--timeout-idle-seconds",
        type=int,
        help="Reserved idle-output timeout for future provider adapters.",
    )
    parser.add_argument(
        "--max-output-bytes", type=int, help="Maximum captured stdout/stderr bytes per stream."
    )
    parser.add_argument(
        "--output-schema",
        type=Path,
        help="JSON Schema file to pass to providers instead of the built-in outcome schema.",
    )
    parser.add_argument("--run-dir", type=Path, help="Directory root for persistent run records.")
    parser.add_argument("--log-dir", type=Path, help="Backward-compatible alias for --run-dir.")
    parser.add_argument("--output", type=Path, help="Write normalized final outcome to this file.")
    parser.add_argument(
        "--output-last-message",
        type=Path,
        help="Write/capture provider final message to this file.",
    )
    parser.add_argument("--events", type=Path, help="Write JSONL event stream to this file.")
    parser.add_argument(
        "--stream", action="store_true", help="Stream provider output while also capturing it."
    )
    parser.add_argument(
        "--prompt-out", type=Path, help="Write rendered prompt to a file before executing."
    )
    parser.add_argument("--schema-out", type=Path, help="Write generated outcome schema to a file.")
    parser.add_argument(
        "--changed-files-out", type=Path, help="Write post-run Git changed files to a file."
    )
    parser.add_argument("--diff-out", type=Path, help="Write post-run Git diff patch to a file.")
    parser.add_argument(
        "--outcome-format",
        choices=("json", "markdown", "text"),
        default="json",
        help="Stdout/output file format for final outcome.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable runner output where supported."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress non-essential progress output."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print extra runner configuration details."
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment override for the agent process. Repeatable.",
    )
    parser.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set a script argument before values after --. Repeatable.",
    )
    parser.add_argument(
        "--arg-file",
        type=Path,
        action="append",
        default=[],
        help="Load script arguments from JSON or simple YAML-like file. Repeatable.",
    )
    parser.add_argument(
        "--vars",
        dest="var_files",
        type=Path,
        action="append",
        default=[],
        help="Alias for --arg-file for prompt variables.",
    )
    parser.add_argument(
        "--require-no-diff", action="store_true", help="Fail if the run leaves Git changes."
    )
    parser.add_argument(
        "--expect-diff", action="store_true", help="Fail if the run leaves no Git changes."
    )
    parser.add_argument(
        "--post-check",
        action="append",
        default=[],
        help="Shell command the runner executes after the agent. Repeatable.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Treat pseudocode linter warnings as validation failure.",
    )
    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Request provider hook/rule bypass where supported. Visible and safety-checked.",
    )
    parser.add_argument(
        "--require-hooks", action="store_true", help="Fail when project hook config is absent."
    )
    parser.add_argument(
        "--require-mcp", action="store_true", help="Fail when .mcp.json is absent in the workspace."
    )
    parser.add_argument("--resume", help="Resume a provider session by ID where supported.")
    parser.add_argument(
        "--resume-last",
        action="store_true",
        help="Resume/continue the most recent provider session where supported.",
    )
    parser.add_argument(
        "--resume-all",
        action="store_true",
        help="Allow provider resume search outside the current workspace where supported.",
    )
    parser.add_argument(
        "--lock",
        dest="lock_name",
        help="Acquire a named workspace lock under .apseudo/locks before running.",
    )
    parser.add_argument(
        "--retry", type=int, default=0, help="Retry provider process failures this many times."
    )
    parser.add_argument("--version", action="version", version=f"apseudo-run {__version__}")
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the pseudocode script after `--`.",
    )
    return parser


def main(argv: list[str] | None = None, *, forced_agent: AgentName | None = None) -> int:
    """Run apseudo-run."""

    actual_argv = list(sys.argv[1:] if argv is None else argv)
    if _script_help_requested(actual_argv):
        script = parse_executable_file(Path(actual_argv[0]).expanduser().resolve())
        sys.stdout.write(script_help(script, prog=Path(actual_argv[0]).name))
        return 0

    parser = build_parser()
    args = parser.parse_args(actual_argv)
    if args.schema:
        sys.stdout.write(outcome_schema_json())
        return 0
    if args.replay:
        return _replay_run(cast(Path, args.replay), json_output=bool(args.json))

    script_arg = cast(Path | None, args.script)
    if args.rerun or args.resume_run:
        script_arg, extra_values, extra_resume = _load_run_record_for_repeat(
            cast(Path, args.rerun or args.resume_run), resume=bool(args.resume_run)
        )
        if extra_resume and not args.resume:
            args.resume = extra_resume
    else:
        extra_values = {}

    if script_arg is None:
        parser.error("the following arguments are required: script")

    script_args = list(args.script_args)
    if script_args and script_args[0] == "--":
        script_args = script_args[1:]

    try:
        agent = _selected_agent(args, forced_agent)
        mode = _selected_mode(args)
        values = load_arg_values(
            [*cast(list[Path], args.arg_file), *cast(list[Path], args.var_files)]
        )
        values.update(extra_values)
        values.update(_parse_set_values(cast(list[str], args.sets)))
        options = RunnerOptions(
            action=_selected_action(args),
            agent=agent,
            mode=mode,
            workspace=cast(Path | None, args.workspace),
            allow_dirty=bool(args.allow_dirty),
            require_clean_git=True if args.require_clean_git else None,
            danger_accepted=bool(args.i_understand_danger),
            agent_command=cast(str | None, args.agent_command),
            model=cast(str | None, args.model),
            profile=cast(str | None, args.profile),
            sandbox=cast(str | None, args.sandbox),
            claude_bare=_claude_bare_override(args),
            allowed_tools=tuple(cast(list[str], args.allowed_tool)),
            max_turns=cast(int | None, args.max_turns),
            max_budget_usd=cast(float | None, args.max_budget_usd),
            timeout_seconds=cast(int | None, args.timeout_seconds),
            timeout_idle_seconds=cast(int | None, args.timeout_idle_seconds),
            max_output_bytes=cast(int | None, args.max_output_bytes),
            output_schema=cast(Path | None, args.output_schema),
            run_dir=cast(Path | None, args.run_dir),
            log_dir=cast(Path | None, args.log_dir),
            output=cast(Path | None, args.output),
            output_last_message=cast(Path | None, args.output_last_message),
            events_path=cast(Path | None, args.events),
            prompt_out=cast(Path | None, args.prompt_out),
            schema_out=cast(Path | None, args.schema_out),
            changed_files_out=cast(Path | None, args.changed_files_out),
            diff_out=cast(Path | None, args.diff_out),
            print_json=bool(args.json),
            outcome_format=cast(OutcomeFormat, args.outcome_format),
            stream=bool(args.stream),
            env=_parse_env(cast(list[str], args.env)),
            approval_policy=cast(ApprovalPolicy | None, args.approval_policy),
            add_dirs=tuple(cast(list[Path], args.add_dir)),
            ephemeral=bool(args.ephemeral),
            hermetic=bool(args.hermetic),
            project_context=bool(args.project_context),
            require_no_diff=bool(args.require_no_diff),
            expect_diff=bool(args.expect_diff),
            post_checks=tuple(cast(list[str], args.post_check)),
            fail_on_warning=bool(args.fail_on_warning),
            no_hooks=bool(args.no_hooks),
            require_hooks=bool(args.require_hooks),
            require_mcp=bool(args.require_mcp),
            resume=cast(str | None, args.resume),
            resume_last=bool(args.resume_last),
            resume_all=bool(args.resume_all),
            lock_name=cast(str | None, args.lock_name),
            retry=max(0, int(args.retry)),
            quiet=bool(args.quiet),
            verbose=bool(args.verbose),
        )
        invocation = load_invocation(
            script_arg, options=options, raw_script_args=script_args, arg_overrides=values
        )
    except Exception as exc:
        print(f"apseudo-run: configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    if args.check:
        validation = validate_script(invocation.script)
        _print_validation(validation, json_output=bool(args.json))
        return EXIT_VALIDATION_FAILED if validation.failed_with_options(invocation.options) else 0

    if args.render_prompt:
        prompt = render_prompt(invocation)
        if args.prompt_out:
            cast(Path, args.prompt_out).write_text(prompt, encoding="utf-8")
        sys.stdout.write(prompt)
        return 0

    if args.print_command:
        validation = validate_script(invocation.script)
        if validation.failed_with_options(invocation.options):
            _print_validation(validation, json_output=bool(args.json))
            return EXIT_VALIDATION_FAILED
        safety_error = check_safety(invocation)
        if safety_error is not None:
            print(safety_error, file=sys.stderr)
            return 50
        import tempfile

        with tempfile.TemporaryDirectory(prefix="apseudo-run-preview-") as raw_tmp:
            command = build_agent_command(invocation, render_prompt(invocation), Path(raw_tmp))
            if args.json:
                print(json.dumps(command.as_dict(), indent=2, sort_keys=True))
            else:
                print(shell_join(command.argv))
                if command.stdin:
                    print("# stdin: rendered prompt")
            return 0

    outcome, exit_code, output = execute_invocation(invocation)
    if outcome is None:
        print(output, file=sys.stderr)
        return exit_code
    if not args.quiet:
        print(output)
    return exit_code


def claude_main(argv: list[str] | None = None) -> int:
    """Run apseudo-run with Claude selected."""

    return main(argv, forced_agent="claude")


def codex_main(argv: list[str] | None = None) -> int:
    """Run apseudo-run with Codex selected."""

    return main(argv, forced_agent="codex")


def _selected_agent(args: argparse.Namespace, forced_agent: AgentName | None) -> AgentName | None:
    if forced_agent is not None:
        return forced_agent
    if bool(args.claude):
        return "claude"
    if bool(args.codex):
        return "codex"
    agent = cast(str | None, args.agent)
    return cast(AgentName | None, agent)


def _selected_mode(args: argparse.Namespace) -> RunMode | None:
    if bool(args.plan):
        return "plan"
    if bool(args.review):
        return "review"
    if bool(args.apply):
        return "apply"
    if bool(args.danger):
        return "danger"
    return cast(RunMode | None, args.mode)


def _selected_action(args: argparse.Namespace) -> RunnerAction:
    if bool(args.check):
        return "check"
    if bool(args.render_prompt):
        return "render-prompt"
    if bool(args.print_command):
        return "print-command"
    if bool(args.rerun):
        return "rerun"
    if bool(args.resume_run):
        return "resume-run"
    return "run"


def _claude_bare_override(args: argparse.Namespace) -> bool | None:
    if bool(args.claude_bare):
        return True
    if bool(args.claude_project):
        return False
    return None


def _parse_env(items: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--env must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError(f"--env key cannot be empty: {item}")
        values[key] = value
    return values


def _parse_set_values(items: list[str]) -> dict[str, JsonValue]:
    values: dict[str, JsonValue] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--set must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        values[key] = value
    return values


def _print_validation(validation: object, *, json_output: bool) -> None:
    from .runner import ValidationResult

    if not isinstance(validation, ValidationResult):
        return
    if json_output:
        print(json.dumps(validation.as_dict(), indent=2, sort_keys=True))
        return
    if validation.diagnostics:
        for diagnostic in validation.diagnostics:
            print(diagnostic.format_text())
        print(f"apseudo-run: {len(validation.diagnostics)} diagnostic(s).")
    else:
        print("apseudo-run: script validation passed.")


def _script_help_requested(argv: list[str]) -> bool:
    if not argv:
        return False
    first = Path(argv[0]).expanduser()
    if first.suffix not in {".apseudo", ".agentpseudo"} and not first.exists():
        return False
    return any(item in {"--help", "-h"} for item in argv[1:])


def _replay_run(run_dir: Path, *, json_output: bool) -> int:
    manifest_path = run_dir.expanduser() / "manifest.json"
    if not manifest_path.exists():
        print(f"apseudo-run: missing run manifest: {manifest_path}", file=sys.stderr)
        return EXIT_CONFIG_INVALID
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if json_output:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"Run: {manifest.get('run_id')}")
        print(
            f"Agent: {manifest.get('agent')}  Mode: {manifest.get('mode')}  Exit: {manifest.get('exit_code')}"
        )
        print(f"Script: {manifest.get('script_path')}")
        print(f"Workspace: {manifest.get('workspace')}")
        print(f"Outcome: {manifest.get('outcome')} — {manifest.get('reason')}")
    return 0


def _load_run_record_for_repeat(
    run_dir: Path, *, resume: bool
) -> tuple[Path, dict[str, JsonValue], str | None]:
    manifest_path = run_dir.expanduser() / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"missing run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    script = run_dir.expanduser() / "script.apseudo"
    if not script.exists():
        raw_script = manifest.get("script_path")
        if not isinstance(raw_script, str):
            raise ValueError("run record does not contain a runnable script path")
        script = Path(raw_script)
    args = manifest.get("args")
    values = cast(dict[str, JsonValue], args) if isinstance(args, dict) else {}
    session = manifest.get("session_id") if resume else None
    return script, values, session if isinstance(session, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
