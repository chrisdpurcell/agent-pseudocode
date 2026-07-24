"""Behavior contracts for guarded Agent Pseudocode runner evidence capture."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest

from video_pipeline.runner_capture import (
    REQUIRED_EVIDENCE_NAMES,
    RunnerCaptureError,
    RunnerCaptureResult,
    capture_guarded_runner,
    expand_display_command,
    prepare_runner_runtime,
)

REVIEW_SCRIPT = "docs/apseudo-docs/examples/runner/review-spec.apseudo"
SPEC_PATH = "docs/specs/repository-explainer-video.md"
HOOK_COMMAND = '"$(git rev-parse --show-toplevel)/.agents/hooks/agent-handoff/session_start.py"'
SECRET_PATTERN = re.compile(
    rb"(?i)(?:authorization|api[_-]?key|access[_-]?token|secret[_-]?key|password)"
    rb"\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_executable(path: Path, body: str, *, shebang: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{shebang}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path


def _fake_hook_body() -> str:
    return """\
import os
import pathlib
import subprocess
import sys

if os.environ.get("APSEUDO_TEST_HOOK_MODE") == "nonzero":
    sys.stderr.write("configured hook failed\\n")
    raise SystemExit(7)

root = pathlib.Path(__file__).resolve().parents[3]
branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
commit = subprocess.run(
    ["git", "rev-parse", "--short", "HEAD"],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
state = (root / "docs/handoff/state.md").read_text(encoding="utf-8")
if os.environ.get("APSEUDO_TEST_HOOK_MODE") == "degraded":
    print("<session_context>(session_start.py failed: RuntimeError)</session_context>")
else:
    print("<session_context>")
    print(f"Branch: {branch}")
    print(state)
    print(f"{commit} fixture commit")
    print("</session_context>")
"""


def _fake_runner_body() -> str:
    return """\
import json
import os
import pathlib
import shlex
import subprocess
import sys

from apseudo_lint.runner_cli import main as _apseudo_runner_main

args = sys.argv[1:]
mode = os.environ.get("APSEUDO_TEST_RUNNER_MODE", "accepted")

if args and args[0] == "--check":
    print("apseudo-run: script validation passed.")
    raise SystemExit(0)
if args and args[0] == "--render-prompt":
    print("Runner policy:")
    print("- no_hooks_requested: False")
    print("- hooks_required: False")
    print("spec_path: docs/specs/repository-explainer-video.md")
    raise SystemExit(0)
if args and args[0] == "--print-command":
    print(shlex.join(["codex", "exec", "--cd", str(pathlib.Path.cwd()), "--sandbox", "read-only", "-"]))
    print("# stdin: rendered prompt")
    raise SystemExit(0)
if mode == "execution-nonzero":
    sys.stderr.write("fake provider execution failed\\n")
    raise SystemExit(40)
if mode == "execution-partial-nonzero":
    run_root = pathlib.Path(args[args.index("--run-dir") + 1])
    run_record = run_root / "fixture-run"
    run_record.mkdir(parents=True)
    (run_record / "manifest.json").write_text(
        json.dumps({"run_id": "fixture-run", "exit_code": 40}) + "\\n",
        encoding="utf-8",
    )
    (run_record / "agent-command.json").write_text(
        json.dumps({"argv": ["codex", "exec"], "env_overrides": {}}) + "\\n",
        encoding="utf-8",
    )
    (run_record / "validation-before.json").write_text(
        json.dumps({"diagnostics": [], "failed": False}) + "\\n",
        encoding="utf-8",
    )
    sys.stderr.write("fake provider failed after creating a run record\\n")
    raise SystemExit(40)

run_root = pathlib.Path(args[args.index("--run-dir") + 1])
run_record = run_root / "fixture-run"
run_record.mkdir(parents=True)
post_check = args[args.index("--post-check") + 1]
post_result = subprocess.run(
    shlex.split(post_check),
    cwd=pathlib.Path.cwd(),
    check=False,
    capture_output=True,
    text=True,
)
post_returncode = 9 if mode == "post-check-nonzero" else post_result.returncode
outcome_name = "Accepted" if post_returncode == 0 else "Blocked"
exit_code = 0 if outcome_name == "Accepted" else 20

if mode == "changed-files":
    pathlib.Path("unexpected-change.txt").write_text("changed\\n", encoding="utf-8")

def write_json(name, payload):
    (run_record / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\\n",
        encoding="utf-8",
    )

write_json(
    "manifest.json",
    {
        "run_id": "fixture-run",
        "agent": "codex",
        "workspace": str(pathlib.Path.cwd()),
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "exit_code": exit_code,
        "outcome": outcome_name,
    },
)
write_json(
    "agent-command.json",
    {
        "argv": ["codex", "exec", "--cd", str(pathlib.Path.cwd()), "--sandbox", "read-only", "-"],
        "cwd": str(pathlib.Path.cwd()),
        "env_overrides": {},
        "stdin": "rendered prompt",
    },
)
write_json("validation-before.json", {"diagnostics": [], "failed": False})
write_json(
    "post-checks.json",
    [
        {
            "command": post_check,
            "returncode": post_returncode,
            "stdout": post_result.stdout,
            "stderr": post_result.stderr,
            "passed": post_returncode == 0,
        }
    ],
)
write_json(
    "outcome.json",
    {
        "outcome": outcome_name,
        "reason": "fixture result",
        "summary": "fake provider completed",
        "checks_run": [post_check],
        "artifacts": [],
    },
)
print(
    json.dumps(
        {
            "outcome": outcome_name,
            "reason": "fixture result",
            "summary": "fake provider completed",
            "checks_run": [post_check],
            "artifacts": [],
        }
    )
)
raise SystemExit(exit_code)
"""


def _fake_status_body(message: str) -> str:
    return f"print({message!r})\n"


@contextmanager
def _runner_repository(
    tmp_path: Path,
    *,
    hook_command: str = HOOK_COMMAND,
) -> Generator[tuple[Path, str, Path, dict[str, str]]]:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Runner Capture Test")
    _git(
        repository,
        "config",
        "user.email",
        "168346341+chrisdpurcell@users.noreply.github.com",
    )
    _git(repository, "config", "commit.gpgsign", "false")
    (repository / ".gitignore").write_text("dist/\n", encoding="utf-8")

    config = repository / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text(
        "[[hooks.SessionStart]]\n"
        'matcher = "startup|resume|clear|compact"\n'
        "[[hooks.SessionStart.hooks]]\n"
        'type = "command"\n'
        f"command = {json.dumps(hook_command)}\n",
        encoding="utf-8",
    )
    _write_executable(
        repository / ".agents/hooks/agent-handoff/session_start.py",
        _fake_hook_body(),
        shebang="/usr/bin/env python3",
    )
    state = repository / "docs/handoff/state.md"
    state.parent.mkdir(parents=True)
    state.write_text(
        "# Session state\n\n"
        "## Current focus\n\n"
        "- Capture exact guarded runner evidence.\n\n"
        "## Active incidents\n\n"
        "- None.\n",
        encoding="utf-8",
    )
    script = repository / REVIEW_SCRIPT
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env apseudo-run\n"
        "---\n"
        "name: review_spec\n"
        "description: Review a specification.\n"
        "default_agent: codex\n"
        "mode: review\n"
        "codex:\n"
        "  sandbox: read-only\n"
        "---\n\n"
        "process review_spec(spec_path):\n"
        "    if spec_path is None:\n"
        '        return NeedsUserDecision(reason="spec_path argument is missing")\n\n'
        '    return Accepted(reason="spec review passed")\n',
        encoding="utf-8",
    )
    spec = repository / SPEC_PATH
    spec.parent.mkdir(parents=True)
    spec.write_text("# Repository explainer specification\n", encoding="utf-8")
    (repository / "pyproject.toml").write_text(
        "[project]\n"
        'name = "runner-capture-fixture"\n'
        'version = "0.6.1"\n'
        "[project.scripts]\n"
        'apseudo-run = "apseudo_lint.runner_cli:main"\n',
        encoding="utf-8",
    )

    imported_module = subprocess.run(
        [
            sys.executable,
            "-c",
            "import pathlib, apseudo_lint; print(pathlib.Path(apseudo_lint.__file__).resolve())",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    module_target = repository / "src/apseudo_lint/__init__.py"
    module_target.parent.mkdir(parents=True)
    module_target.write_bytes(Path(imported_module).read_bytes())
    operator_python = repository / "operator/bin/python"
    operator_python.parent.mkdir(parents=True)
    operator_python.symlink_to(Path(sys.executable).resolve())
    runner = _write_executable(
        repository / "operator/bin/apseudo-run",
        _fake_runner_body(),
        shebang=str(operator_python.absolute()),
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "uv",
        _fake_status_body("locked environment synchronized"),
        shebang=str(Path(sys.executable).resolve()),
    )
    _write_executable(
        fake_bin / "codex",
        _fake_status_body("Logged in using fixture"),
        shebang=str(Path(sys.executable).resolve()),
    )

    _git(repository, "add", ".")
    _git(repository, "commit", "--quiet", "-m", "runner capture fixture")
    revision = _git(repository, "rev-parse", "HEAD")
    environment = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "PYTHONPATH": str(Path(imported_module).parents[1]),
    }
    yield repository, revision, runner, environment


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _prepare_and_capture(
    repository: Path,
    revision: str,
    runner: Path,
    environment: Mapping[str, str],
    evidence_root: Path,
) -> RunnerCaptureResult:
    runtime = prepare_runner_runtime(
        repository,
        revision=revision,
        operator_python=runner.parent / "python",
        operator_apseudo_run=runner,
        environment=environment,
    )
    return capture_guarded_runner(
        repository,
        revision=revision,
        runtime=runtime,
        evidence_root=evidence_root,
        environment=environment,
    )


def test_accepts_only_exact_clean_guarded_codex_run(tmp_path: Path) -> None:
    """TC-T4-001: exact hook, aliases, run record, post-check, and cleanup pass."""
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    assert result.mode == "accepted"
    assert result.reason == "guarded runner capture passed"
    assert not result.clone_path.exists()
    assert set(result.evidence_hashes) == set(REQUIRED_EVIDENCE_NAMES)
    for name, digest in result.evidence_hashes.items():
        evidence = evidence_root / name
        assert evidence.is_file()
        assert hashlib.sha256(evidence.read_bytes()).hexdigest() == digest
        if evidence.read_bytes().startswith(b"{\n"):
            assert evidence.read_bytes().startswith(b"{\n\t")

    hook = _json_object(evidence_root / "hook-preflight.json")
    assert hook["status"] == "passed"
    assert hook["config_command"] == HOOK_COMMAND
    assert hook["input"] == '{"hook_event_name":"SessionStart","source":"startup","cwd":"."}'
    assert hook["cwd"] == "."
    assert hook["exit_status"] == 0
    interpreter = cast(dict[str, object], hook["interpreter"])
    assert cast(list[int], interpreter["version_info"])[:2] == [3, 14]

    commands = _json_object(evidence_root / "runner-commands.json")
    runtime_record = cast(dict[str, object], commands["runtime"])
    assert runtime_record["sync_argv"] == ["uv", "sync", "--locked", "--all-groups"]
    assert runtime_record["console_entrypoint"] == "apseudo_lint.runner_cli:main"
    vectors = cast(list[dict[str, object]], commands["vectors"])
    assert [vector["action"] for vector in vectors] == [
        "check",
        "render-prompt",
        "print-command",
        "execute",
    ]
    base_argv = cast(list[str], commands["base_argv"])
    assert "--require-hooks" not in base_argv
    assert base_argv[1:] == [
        "--agent",
        "codex",
        "--workspace",
        ".",
        "--sandbox",
        "read-only",
        "--require-no-diff",
        "--post-check",
        commands["post_check"],
        "--run-dir",
        "dist/video/work/runner-runs",
        "--set",
        f"spec_path={SPEC_PATH}",
        REVIEW_SCRIPT,
    ]
    assert commands["prompt_assertions"] == {
        "hooks_required: False": True,
        "no_hooks_requested: False": True,
    }
    display = cast(dict[str, object], commands["display"])
    display_command = cast(str, display["command"])
    assert str(Path(sys.executable).resolve()) not in display_command
    assert str(runner.resolve()) not in display_command
    assert expand_display_command(display_command, cast(dict[str, object], display["aliases"])) == (
        tuple(base_argv)
    )

    changed = _json_object(evidence_root / "changed-files.json")
    assert changed == {"clean": True, "files": [], "no_diff": True}
    outcome = _json_object(evidence_root / "outcome.json")
    assert outcome["mode"] == "accepted"
    assert outcome["accepted"] is True


@pytest.mark.parametrize(
    ("hook_mode", "runner_mode", "reason_fragment"),
    [
        pytest.param("nonzero", "accepted", "hook exited 7", id="nonzero-hook"),
        pytest.param("degraded", "accepted", "degraded diagnostic", id="degraded-hook"),
        pytest.param(
            "",
            "execution-nonzero",
            "fake provider execution failed",
            id="nonzero-execution",
        ),
        pytest.param(
            "",
            "execution-partial-nonzero",
            "fake provider failed after creating a run record",
            id="partial-nonzero-execution",
        ),
        pytest.param("", "post-check-nonzero", "post-check failed", id="nonzero-post-check"),
        pytest.param("", "changed-files", "workspace changed", id="changed-files"),
    ],
)
def test_falls_back_to_verified_preflight(
    tmp_path: Path,
    hook_mode: str,
    runner_mode: str,
    reason_fragment: str,
) -> None:
    """TC-T4-002: any degraded guard records preflight-only, never acceptance."""
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        selected_environment = dict(environment)
        if hook_mode:
            selected_environment["APSEUDO_TEST_HOOK_MODE"] = hook_mode
        selected_environment["APSEUDO_TEST_RUNNER_MODE"] = runner_mode
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            selected_environment,
            evidence_root,
        )

    assert result.mode == "preflight-only"
    assert reason_fragment in result.reason
    assert not result.clone_path.exists()
    assert set(result.evidence_hashes) == set(REQUIRED_EVIDENCE_NAMES)
    outcome = _json_object(evidence_root / "outcome.json")
    assert outcome["accepted"] is False
    assert outcome["mode"] == "preflight-only"
    assert reason_fragment in cast(str, outcome["reason"])
    for path in evidence_root.iterdir():
        assert not SECRET_PATTERN.search(path.read_bytes())


def test_runner_record_excludes_credentials(tmp_path: Path) -> None:
    """TC-T4-003: explicit credential input and secret-like output fail closed."""
    with (
        _runner_repository(tmp_path / "input") as (
            repository,
            revision,
            runner,
            environment,
        ),
        pytest.raises(RunnerCaptureError, match="credential-like environment"),
    ):
        _prepare_and_capture(
            repository,
            revision,
            runner,
            {**environment, "OPENAI_API_KEY": "sk-prohibited123456789"},
            tmp_path / "input-evidence",
        )

    with _runner_repository(tmp_path / "output") as (
        repository,
        revision,
        runner,
        environment,
    ):
        runner.write_text(
            runner.read_text(encoding="utf-8").replace(
                'print("apseudo-run: script validation passed.")',
                'print("OPENAI_API_KEY=sk-prohibited123456789")',
            ),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        _git(repository, "add", "operator/bin/apseudo-run")
        _git(repository, "commit", "--quiet", "-m", "leaky runner")
        revision = _git(repository, "rev-parse", "HEAD")
        with pytest.raises(RunnerCaptureError, match="credential-like output"):
            _prepare_and_capture(
                repository,
                revision,
                runner,
                environment,
                tmp_path / "output-evidence",
            )

    for evidence_root in (tmp_path / "input-evidence", tmp_path / "output-evidence"):
        if evidence_root.exists():
            assert not any(
                SECRET_PATTERN.search(path.read_bytes())
                for path in evidence_root.rglob("*")
                if path.is_file()
            )


def test_wrong_configured_hook_command__records_preflight_only(tmp_path: Path) -> None:
    with _runner_repository(tmp_path, hook_command="./wrong-hook") as (
        repository,
        revision,
        runner,
        environment,
    ):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    assert result.mode == "preflight-only"
    assert "configured SessionStart command changed" in result.reason


def test_post_check__uses_synced_operator_interpreter_and_bound_spec(tmp_path: Path) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        _prepare_and_capture(repository, revision, runner, environment, evidence_root)

    commands = _json_object(evidence_root / "runner-commands.json")
    expected_post_check = shlex.join(
        [str(runner.parent / "python"), "-m", "apseudo_lint.cli", REVIEW_SCRIPT]
    )
    assert commands["post_check"] == expected_post_check
    assert f"spec_path={SPEC_PATH}" in cast(list[str], commands["base_argv"])
    post_checks = cast(
        list[dict[str, object]],
        json.loads((evidence_root / "post-checks.json").read_text(encoding="utf-8")),
    )
    assert post_checks == [
        {
            "command": expected_post_check,
            "passed": True,
            "returncode": 0,
            "stderr": "",
            "stdout": "apseudo-lint: checked 1 file(s); no diagnostics.\n",
        }
    ]
