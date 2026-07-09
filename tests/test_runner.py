from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from apseudo_lint.executable import parse_executable_file, split_source_parts
from apseudo_lint.runner import (
    OUTCOME_SCHEMA,
    RunnerOptions,
    build_agent_command,
    load_invocation,
    parse_runner_outcome,
    render_prompt,
    validate_script,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "fixtures" / "valid" / "executable_runner.apseudo"


def test_executable_parser_strips_shebang_and_frontmatter() -> None:
    script = parse_executable_file(SCRIPT)

    assert script.shebang is not None
    assert script.metadata.name == "executable_demo"
    assert script.metadata.default_agent == "codex"
    assert script.body_start_line == 8
    assert script.body.lstrip().startswith("process executable_demo")


def test_linter_accepts_executable_runner_script() -> None:
    script = parse_executable_file(SCRIPT)
    validation = validate_script(script)

    assert not validation.failed


def test_source_parts_preserve_prefix_for_formatter() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    parts = split_source_parts(source)

    assert parts.prefix.startswith("#!/usr/bin/env apseudo-run")
    assert "default_agent: codex" in parts.prefix
    assert "process executable_demo" in parts.body


def test_render_prompt_contains_contract_script_and_args() -> None:
    invocation = load_invocation(
        SCRIPT,
        options=RunnerOptions(agent="codex", mode="plan"),
        raw_script_args=["target=src"],
    )

    prompt = render_prompt(invocation)

    assert "Execution contract" in prompt
    assert "process executable_demo" in prompt
    assert '"target": "src"' in prompt
    assert "Outcome JSON schema" in prompt


def test_codex_command_uses_stdin_and_schema(tmp_path: Path) -> None:
    invocation = load_invocation(
        SCRIPT,
        options=RunnerOptions(agent="codex", mode="plan"),
        raw_script_args=["target=src"],
    )
    command = build_agent_command(invocation, "prompt text", tmp_path)

    assert command.argv[:2] == ["codex", "exec"]
    assert "--cd" in command.argv
    assert "--output-schema" in command.argv
    assert command.argv[-1] == "-"
    assert command.stdin == "prompt text"
    assert command.schema_path is not None
    assert json.loads(command.schema_path.read_text(encoding="utf-8")) == OUTCOME_SCHEMA


def test_claude_command_uses_print_mode_and_json_schema(tmp_path: Path) -> None:
    invocation = load_invocation(
        SCRIPT,
        options=RunnerOptions(agent="claude", mode="review", claude_bare=True),
        raw_script_args=[],
    )
    command = build_agent_command(invocation, "prompt text", tmp_path)

    assert command.argv[0] == "claude"
    assert "--bare" in command.argv
    assert "-p" in command.argv
    assert "--json-schema" in command.argv
    assert command.stdin is None


def test_parse_runner_outcome_accepts_plain_and_claude_json() -> None:
    direct = parse_runner_outcome(
        '{"outcome":"Accepted","reason":"ok","summary":"done","checks_run":["unit"],"artifacts":[]}'
    )
    claude = parse_runner_outcome(
        json.dumps(
            {
                "structured_output": {
                    "outcome": "Blocked",
                    "reason": "no",
                    "summary": "stopped",
                    "checks_run": [],
                    "artifacts": [],
                }
            }
        )
    )

    assert direct is not None
    assert direct.exit_code == 0
    assert claude is not None
    assert claude.exit_code == 20


def test_runner_cli_check_and_render_prompt() -> None:
    env = {"PYTHONPATH": str(ROOT / "src")}
    check = subprocess.run(
        [sys.executable, "-m", "apseudo_lint.runner_cli", "--check", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    prompt = subprocess.run(
        [sys.executable, "-m", "apseudo_lint.runner_cli", "--codex", "--render-prompt", str(SCRIPT), "--", "target=src"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert check.returncode == 0, check.stderr
    assert "validation passed" in check.stdout
    assert prompt.returncode == 0, prompt.stderr
    assert "target" in prompt.stdout
