"""Behavior contracts for guarded Agent Pseudocode runner evidence capture."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from video_pipeline import runner_capture as runner_capture_module
from video_pipeline import runner_evidence
from video_pipeline.capture import CaptureError
from video_pipeline.runner_capture import (
    MAX_EVIDENCE_FILE_BYTES,
    MAX_PROCESS_OUTPUT_BYTES,
    REQUIRED_EVIDENCE_NAMES,
    EvidencePromotionError,
    RunnerCaptureError,
    RunnerCaptureResult,
    RunnerOperationalError,
    UnsafeRunnerCaptureError,
    build_child_environment,
    capture_guarded_runner,
    expand_display_command,
    expected_console_wrapper_bytes,
    prepare_and_capture_guarded_runner,
    prepare_runner_runtime,
    promote_evidence_bundle,
    reject_credential_evidence,
    validation_record_passed,
)
from video_pipeline.runner_runtime import environment_digest
from video_pipeline.runner_security import ProcessResult

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

if os.environ.get("OPENAI_API_KEY"):
    sys.stderr.write("hook received provider auth\\n")
    raise SystemExit(8)
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
    body = """\
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import apseudo_lint

args = sys.argv[1:]
mode = os.environ.get("APSEUDO_TEST_RUNNER_MODE", "accepted")
prompt = (
    "Runner policy:\\n"
    "- no_hooks_requested: False\\n"
    "- hooks_required: False\\n"
    "spec_path: docs/specs/repository-explainer-video.md\\n"
)

if args and args[0] == "--check":
    if os.environ.get("OPENAI_API_KEY"):
        sys.stderr.write("check received provider auth\\n")
        raise SystemExit(8)
    if mode == "raw-secret-output":
        print(json.dumps({"PASSWORD": "opaque"}))
        raise SystemExit(0)
    if mode == "oversized-output":
        print("x" * (int(os.environ["APSEUDO_TEST_OUTPUT_LIMIT"]) + 1))
        raise SystemExit(0)
    if mode == "mutate-runtime-after-check":
        module_path = pathlib.Path(__file__).with_name("runner.py")
        module_path.write_text(
            module_path.read_text(encoding="utf-8") + "\\n# changed between vectors\\n",
            encoding="utf-8",
        )
    print("apseudo-run: script validation passed.")
    raise SystemExit(0)
if args and args[0] == "--render-prompt":
    if os.environ.get("OPENAI_API_KEY"):
        sys.stderr.write("render received provider auth\\n")
        raise SystemExit(8)
    print(prompt, end="")
    raise SystemExit(0)
if args and args[0] == "--print-command":
    preview_root = pathlib.Path.cwd() / ".preview"
    preview_sandbox = "workspace-write" if mode == "provider-preview-mismatch" else "read-only"
    if os.environ.get("OPENAI_API_KEY"):
        sys.stderr.write("preview received provider auth\\n")
        raise SystemExit(8)
    preview_argv = [
        "codex",
        "exec",
        "--cd",
        str(pathlib.Path.cwd()),
        "--json",
        "--output-last-message",
        str(preview_root / "outcome.json"),
        "--output-schema",
        str(preview_root / "schema.json"),
        "--sandbox",
        preview_sandbox,
        "-",
    ]
    if mode == "agent-duplicate-sandbox":
        preview_argv[-1:-1] = ["--sandbox", "danger-full-access"]
    print(shlex.join(preview_argv))
    print("# stdin: rendered prompt")
    raise SystemExit(0)
if mode == "execution-nonzero":
    sys.stderr.write("fake provider execution failed\\n")
    raise SystemExit(40)
if os.environ.get("APSEUDO_TEST_REQUIRE_AUTH") == "1" and not os.environ.get(
    "OPENAI_API_KEY"
):
    sys.stderr.write("execution did not receive provider auth\\n")
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
        json.dumps(
            {
                "summary": {"diagnostics": 0, "errors": 0, "warnings": 0},
                "diagnostics": [],
            }
        )
        + "\\n",
        encoding="utf-8",
    )
    sys.stderr.write("fake provider failed after creating a run record\\n")
    raise SystemExit(40)

run_root = pathlib.Path(args[args.index("--run-dir") + 1])
run_record = run_root / "fixture-run"
if mode == "run-record-root-symlink":
    external_record = run_root.parent / "external-fixture-run"
    external_record.mkdir(parents=True)
    run_record.parent.mkdir(parents=True, exist_ok=True)
    run_record.symlink_to(external_record.resolve(), target_is_directory=True)
else:
    run_record.mkdir(parents=True)
post_check = args[args.index("--post-check") + 1]
workspace = str(pathlib.Path.cwd())
schema_path = str(run_record / "outcome-schema.json")
last_message_path = str(run_record / "outcome-last-message.json")
provider_argv = [
    "codex",
    "exec",
    "--cd",
    workspace,
    "--json",
    "--output-last-message",
    last_message_path,
    "--output-schema",
    schema_path,
    "--sandbox",
    "read-only",
    "-",
]
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
        "started_at": "2026-07-24T00:00:00+00:00",
        "ended_at": "2026-07-24T00:00:01+00:00",
        "toolkit_version": apseudo_lint.__version__,
        "script_path": str(pathlib.Path.cwd() / "docs/apseudo-docs/examples/runner/review-spec.apseudo"),
        "script_name": "review_spec",
        "agent": "codex",
        "mode": "review",
        "workspace": workspace,
        "args": {"spec_path": "docs/specs/repository-explainer-video.md"},
        "passthrough": [],
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "exit_code": exit_code,
        "outcome": outcome_name,
        "reason": "fixture result",
    },
)
write_json(
    "agent-command.json",
    {
        "argv": provider_argv,
        "cwd": workspace,
        "env_overrides": {},
        "stdin": prompt,
        "schema_path": schema_path,
        "output_last_message_path": last_message_path,
    },
)
write_json(
    "validation-before.json",
    {
        "summary": {"diagnostics": 0, "errors": 0, "warnings": 0},
        "diagnostics": [],
    },
)
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
if mode == "manifest-git-mismatch":
    payload = json.loads((run_record / "manifest.json").read_text(encoding="utf-8"))
    payload["git_head"] = "0" * 40
    write_json("manifest.json", payload)
if mode == "manifest-exit-string":
    payload = json.loads((run_record / "manifest.json").read_text(encoding="utf-8"))
    payload["exit_code"] = "0"
    write_json("manifest.json", payload)
if mode == "manifest-script-mismatch":
    payload = json.loads((run_record / "manifest.json").read_text(encoding="utf-8"))
    payload["script_path"] = str(pathlib.Path.cwd() / "wrong.apseudo")
    write_json("manifest.json", payload)
if mode == "manifest-spec-mismatch":
    payload = json.loads((run_record / "manifest.json").read_text(encoding="utf-8"))
    payload["args"]["spec_path"] = "docs/specs/wrong.md"
    write_json("manifest.json", payload)
if mode == "manifest-nonobject":
    write_json("manifest.json", ["not", "an", "object"])
if mode == "agent-argv-nonstring":
    payload = json.loads((run_record / "agent-command.json").read_text(encoding="utf-8"))
    payload["argv"][1] = 7
    write_json("agent-command.json", payload)
if mode == "agent-cwd-mismatch":
    payload = json.loads((run_record / "agent-command.json").read_text(encoding="utf-8"))
    payload["cwd"] = "/wrong/workspace"
    write_json("agent-command.json", payload)
if mode == "agent-prompt-mismatch":
    payload = json.loads((run_record / "agent-command.json").read_text(encoding="utf-8"))
    payload["stdin"] = "different prompt"
    write_json("agent-command.json", payload)
if mode == "agent-sandbox-mismatch":
    payload = json.loads((run_record / "agent-command.json").read_text(encoding="utf-8"))
    payload["argv"][payload["argv"].index("read-only")] = "workspace-write"
    write_json("agent-command.json", payload)
if mode == "agent-duplicate-sandbox":
    payload = json.loads((run_record / "agent-command.json").read_text(encoding="utf-8"))
    payload["argv"][-1:-1] = ["--sandbox", "danger-full-access"]
    write_json("agent-command.json", payload)
if mode == "post-returncode-string":
    payload = json.loads((run_record / "post-checks.json").read_text(encoding="utf-8"))
    payload[0]["returncode"] = "0"
    write_json("post-checks.json", payload)
if mode == "outcome-checks-nonstring":
    payload = json.loads((run_record / "outcome.json").read_text(encoding="utf-8"))
    payload["checks_run"] = [7]
    write_json("outcome.json", payload)
if mode == "oversized-artifact":
    (run_record / "manifest.json").write_text(
        "x" * (int(os.environ["APSEUDO_TEST_FILE_LIMIT"]) + 1),
        encoding="utf-8",
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
    return f"def main():\n{textwrap.indent(body, '    ')}"


def _fake_linter_body() -> str:
    return """\
import sys

print("apseudo-lint: checked 1 file(s); no diagnostics.")
raise SystemExit(0)
"""


def _fake_status_body(
    message: str,
    failure_variable: str,
    *,
    message_variable: str | None = None,
    require_auth_variable: str | None = None,
) -> str:
    rendered_message = (
        repr(message)
        if message_variable is None
        else f"os.environ.get({message_variable!r}, {message!r})"
    )
    auth_guard = (
        ""
        if require_auth_variable is None
        else (
            f"if os.environ.get({require_auth_variable!r}) == '1' "
            "and not os.environ.get('OPENAI_API_KEY'):\n"
            "    raise SystemExit(9)\n"
        )
    )
    return (
        "import os\n"
        f"{auth_guard}"
        f"print({rendered_message})\n"
        f"raise SystemExit(int(os.environ.get({failure_variable!r}, '0')))\n"
    )


@contextmanager
def _runner_repository(
    tmp_path: Path,
    *,
    hook_command: str = HOOK_COMMAND,
    hook_shebang: str = "/usr/bin/env python3",
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
        shebang=hook_shebang,
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

    fake_runtime = tmp_path / "fake-runtime"
    runtime_package = fake_runtime / "apseudo_lint"
    runtime_package.mkdir(parents=True)
    (runtime_package / "__init__.py").write_bytes(module_target.read_bytes())
    fake_runner_source = _fake_runner_body()
    (runtime_package / "runner_cli.py").write_text(
        fake_runner_source,
        encoding="utf-8",
    )
    (module_target.parent / "runner_cli.py").write_text(
        fake_runner_source,
        encoding="utf-8",
    )
    (runtime_package / "cli.py").write_text(
        _fake_linter_body(),
        encoding="utf-8",
    )
    (module_target.parent / "cli.py").write_text(
        _fake_linter_body(),
        encoding="utf-8",
    )
    fake_policy_module = "# complete-package-closure fixture\\n"
    (runtime_package / "runner.py").write_text(fake_policy_module, encoding="utf-8")
    (module_target.parent / "runner.py").write_text(fake_policy_module, encoding="utf-8")

    operator_python = repository / "operator/bin/python"
    operator_python.parent.mkdir(parents=True)
    operator_python.symlink_to(Path(sys.executable).resolve())
    (operator_python.parents[1] / "pyvenv.cfg").write_text(
        f"home = {Path(sys.executable).resolve().parents[1]}\\n"
        "include-system-site-packages = false\\n"
        f"version = {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\\n",
        encoding="utf-8",
    )
    site_packages = (
        operator_python.parents[1]
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "apseudo_lint"
    )
    site_packages.parent.mkdir(parents=True)
    shutil.copytree(runtime_package, site_packages)
    runner = repository / "operator/bin/apseudo-run"
    runner.write_bytes(
        expected_console_wrapper_bytes(
            operator_python.absolute(),
            "apseudo_lint.runner_cli:main",
        )
    )
    runner.chmod(0o755)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "uv",
        "import os\n"
        'print("locked environment synchronized")\n'
        "raise SystemExit(8 if os.environ.get('OPENAI_API_KEY') else "
        "int(os.environ.get('APSEUDO_TEST_SYNC_STATUS', '0')))\n",
        shebang=str(Path(sys.executable).resolve()),
    )
    _write_executable(
        fake_bin / "codex",
        _fake_status_body(
            "Logged in using fixture",
            "APSEUDO_TEST_LOGIN_STATUS",
            message_variable="APSEUDO_TEST_LOGIN_MESSAGE",
            require_auth_variable="APSEUDO_TEST_REQUIRE_AUTH",
        ),
        shebang=str(Path(sys.executable).resolve()),
    )

    _git(repository, "add", ".")
    _git(repository, "commit", "--quiet", "-m", "runner capture fixture")
    revision = _git(repository, "rev-parse", "HEAD")
    environment = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    yield repository, revision, runner, environment


def _json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _validation_payload(
    diagnostics: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    selected = [] if diagnostics is None else diagnostics
    return {
        "summary": {
            "diagnostics": len(selected),
            "errors": sum(item["severity"] == "error" for item in selected),
            "warnings": sum(item["severity"] == "warning" for item in selected),
        },
        "diagnostics": selected,
    }


def _prepare_and_capture(
    repository: Path,
    revision: str,
    runner: Path,
    environment: Mapping[str, str],
    evidence_root: Path,
) -> RunnerCaptureResult:
    return prepare_and_capture_guarded_runner(
        repository,
        revision=revision,
        operator_python=runner.parent / "python",
        operator_apseudo_run=runner,
        evidence_root=evidence_root,
        environment=environment,
    )


def _assert_preflight_bundle(
    result: RunnerCaptureResult,
    evidence_root: Path,
    reason_fragment: str,
) -> None:
    assert result.mode == "preflight-only"
    assert reason_fragment in result.reason
    assert not result.clone_path.exists()
    assert set(result.evidence_hashes) == set(REQUIRED_EVIDENCE_NAMES)
    outcome = _json_object(evidence_root / "outcome.json")
    assert outcome["accepted"] is False
    assert outcome["mode"] == "preflight-only"
    assert reason_fragment in cast(str, outcome["reason"])


@pytest.mark.parametrize(
    ("value", "raw"),
    [
        pytest.param(
            {"outer": [{"PASSWORD": "opaque"}]},
            None,
            id="nested-secret-key",
        ),
        pytest.param(
            {"outer": [["sk-prohibited123456789"]]},
            None,
            id="secret-shaped-list-value",
        ),
        pytest.param(
            {"safe": "opaque"},
            b"PASSWORD=opaque",
            id="raw-fallback",
        ),
        pytest.param(
            None,
            b'{"OPENAI_API_KEY":"opaque"',
            id="malformed-json-raw-fallback",
        ),
    ],
)
def test_reject_credential_evidence__nested_or_raw_secret_shape__raises(
    value: object,
    raw: bytes | None,
) -> None:
    with pytest.raises(RunnerCaptureError, match="credential-like output"):
        reject_credential_evidence(value, raw=raw, context="fixture")


def test_reject_credential_evidence__opaque_safe_fields__passes() -> None:
    reject_credential_evidence(
        {"status": "opaque", "items": [{"name": "fixture"}], "tokenized": True},
        raw=b'{"status":"opaque","tokenized":true}',
        context="fixture",
    )


def test_validation_passed__exact_zero_error_schema__returns_true() -> None:
    assert validation_record_passed(_validation_payload())


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"failed": False}, id="generic-failed-false"),
        pytest.param(
            {
                "summary": {"diagnostics": 1, "errors": 0, "warnings": 0},
                "diagnostics": [],
            },
            id="summary-count-contradiction",
        ),
        pytest.param(
            _validation_payload(
                [
                    {
                        "path": "fixture.apseudo",
                        "line": 1,
                        "column": 1,
                        "code": "APSEUDO-FIXTURE",
                        "severity": "error",
                        "message": "fixture diagnostic",
                    }
                ]
            )
            | {
                "summary": {
                    "diagnostics": 1,
                    "errors": 0,
                    "warnings": 0,
                }
            },
            id="error-count-contradiction",
        ),
        pytest.param(
            {
                "summary": {"diagnostics": 1, "errors": 0, "warnings": 0},
                "diagnostics": [
                    {
                        "path": "fixture.apseudo",
                        "line": 1,
                        "column": 1,
                        "code": "APSEUDO-FIXTURE",
                        "severity": "info",
                        "message": "fixture diagnostic",
                        "unexpected": True,
                    }
                ],
            },
            id="unknown-diagnostic-field",
        ),
    ],
)
def test_validation_passed__nonproduction_or_contradictory_schema__returns_false(
    payload: object,
) -> None:
    assert not validation_record_passed(payload)


def test_prepare_runtime__console_has_extra_bytes__rejects_nonexact_wrapper(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runner.write_bytes(runner.read_bytes() + b"# unexpected wrapper bytes\n")

        with pytest.raises(RunnerCaptureError, match="console wrapper does not match"):
            prepare_runner_runtime(
                repository,
                revision=revision,
                operator_python=runner.parent / "python",
                operator_apseudo_run=runner,
                environment=environment,
            )


def test_capture__console_changes_after_preparation__records_preflight_only(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        runner.write_bytes(runner.read_bytes() + b"# stale wrapper\n")
        evidence_root = tmp_path / "promoted"

        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, "operator console wrapper changed")


def test_capture__module_changes_after_preparation__records_preflight_only(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        runtime.module_path.write_bytes(runtime.module_path.read_bytes() + b"# stale module\n")
        evidence_root = tmp_path / "promoted"

        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, "operator module changed")


def test_capture__entrypoint_module_changes_after_preparation__records_preflight_only(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        runtime.entrypoint_module_path.write_bytes(
            runtime.entrypoint_module_path.read_bytes() + b"# stale entrypoint module\n"
        )
        evidence_root = tmp_path / "promoted"

        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, "operator entrypoint module changed")


def test_capture__environment_changes_after_preparation__records_preflight_only(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        evidence_root = tmp_path / "promoted"

        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment={**environment, "LANG": "fr_FR.UTF-8"},
        )

    _assert_preflight_bundle(result, evidence_root, "operator environment changed")


def test_capture__runtime_changes_between_vectors__records_preflight_only(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"

        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            {**environment, "APSEUDO_TEST_RUNNER_MODE": "mutate-runtime-after-check"},
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "operator package closure changed")


def test_capture__runtime_identity_emits_secret__raises_unsafe_error(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        runtime.entrypoint_module_path.write_text(
            'print(\'{"PASSWORD":"opaque"}\')\n'
            + runtime.entrypoint_module_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        with pytest.raises(UnsafeRunnerCaptureError, match="credential-like output"):
            capture_guarded_runner(
                repository,
                revision=revision,
                runtime=runtime,
                evidence_root=tmp_path / "promoted",
                environment=environment,
            )


def test_capture__hook_interpreter_probe_emits_secret__raises_unsafe_error(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        fake_python = Path(environment["PATH"].split(":", maxsplit=1)[0]) / "python3"
        _write_executable(
            fake_python,
            'print(\'{"PASSWORD":"opaque"}\')\n',
            shebang=str(Path(sys.executable).resolve()),
        )

        with pytest.raises(UnsafeRunnerCaptureError, match="credential-like output"):
            _prepare_and_capture(
                repository,
                revision,
                runner,
                environment,
                tmp_path / "promoted",
            )


@pytest.mark.parametrize(
    ("runtime_change", "reason_fragment"),
    [
        pytest.param(
            {"revision": "0" * 40},
            "runtime revision does not match",
            id="revision-mismatch",
        ),
        pytest.param(
            {"sync_status": 1},
            "locked environment sync exited 1",
            id="sync-failed",
        ),
        pytest.param(
            {"provider_status": 1},
            "Codex login status exited 1",
            id="login-failed",
        ),
        pytest.param(
            {"operator_python_sha256": "0" * 64},
            "operator interpreter changed",
            id="interpreter-mismatch",
        ),
    ],
)
def test_capture__runtime_precondition_fails__promotes_complete_preflight_bundle(
    tmp_path: Path,
    runtime_change: dict[str, object],
    reason_fragment: str,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        evidence_root = tmp_path / "promoted"

        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=replace(runtime, **runtime_change),
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, reason_fragment)


@pytest.mark.parametrize(
    ("variable", "status", "reason_fragment"),
    [
        pytest.param(
            "APSEUDO_TEST_SYNC_STATUS",
            "8",
            "locked environment sync exited 8",
            id="sync-command",
        ),
        pytest.param(
            "APSEUDO_TEST_LOGIN_STATUS",
            "7",
            "Codex login status exited 7",
            id="login-command",
        ),
    ],
)
def test_prepare_and_capture__operational_precondition_fails__promotes_bundle(
    tmp_path: Path,
    variable: str,
    status: str,
    reason_fragment: str,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        selected_environment = {**environment, variable: status}
        evidence_root = tmp_path / "promoted"

        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            selected_environment,
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, reason_fragment)


@pytest.mark.parametrize(
    ("revision_value", "python_path", "mutate_module", "reason_fragment"),
    [
        pytest.param(
            "missing-revision",
            None,
            False,
            "revision: expected a resolvable Git commit",
            id="unresolved-revision",
        ),
        pytest.param(
            None,
            "missing-python",
            False,
            "operator_python: expected an existing file",
            id="missing-interpreter",
        ),
        pytest.param(
            None,
            None,
            True,
            "operator module hash does not match",
            id="module-mismatch",
        ),
    ],
)
def test_prepare_and_capture__genuine_precondition_failure__promotes_bundle(
    tmp_path: Path,
    revision_value: str | None,
    python_path: str | None,
    mutate_module: bool,
    reason_fragment: str,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        if mutate_module:
            module = (
                runner.parents[1]
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
                / "apseudo_lint"
                / "__init__.py"
            )
            module.write_bytes(module.read_bytes() + b"# mismatched module\n")
        evidence_root = tmp_path / "promoted"

        result = prepare_and_capture_guarded_runner(
            repository,
            revision=revision if revision_value is None else revision_value,
            operator_python=(
                runner.parent / "python" if python_path is None else tmp_path / python_path
            ),
            operator_apseudo_run=runner,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, reason_fragment)


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
        pytest.param(
            "",
            "run-record-root-symlink",
            "runner record root is a symlink",
            id="run-record-root-symlink",
        ),
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

    with (
        _runner_repository(tmp_path / "output") as (
            repository,
            revision,
            runner,
            environment,
        ),
        pytest.raises(RunnerCaptureError, match="credential-like output"),
    ):
        _prepare_and_capture(
            repository,
            revision,
            runner,
            {**environment, "APSEUDO_TEST_RUNNER_MODE": "raw-secret-output"},
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


def _promotion_bundle(marker: str) -> dict[str, object]:
    return {name: {"name": name, "marker": marker} for name in REQUIRED_EVIDENCE_NAMES}


def test_child_environment__inherited_credentials__are_not_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-api-value")
    monkeypatch.setenv("DATABASE_PASSWORD", "inherited-password-value")
    monkeypatch.setenv("UNRELATED_PARENT_STATE", "not-allowed")

    child = build_child_environment(
        {"PATH": "/usr/bin", "HOME": "/tmp/fixture-home"},
        auth_environment={"OPENAI_API_KEY": "explicit-api-value"},
    )

    assert child["OPENAI_API_KEY"] == "explicit-api-value"
    assert "DATABASE_PASSWORD" not in child
    assert "UNRELATED_PARENT_STATE" not in child
    assert "inherited-api-value" not in child.values()


def test_capture__explicit_auth_is_not_logged_in_evidence(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = prepare_and_capture_guarded_runner(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            evidence_root=evidence_root,
            environment={**environment, "APSEUDO_TEST_REQUIRE_AUTH": "1"},
            auth_environment={"OPENAI_API_KEY": "explicit-api-value"},
        )

    assert result.mode == "accepted"
    assert all(b"explicit-api-value" not in path.read_bytes() for path in evidence_root.iterdir())
    commands = _json_object(evidence_root / "runner-commands.json")
    runtime = cast(dict[str, object], commands["runtime"])
    assert runtime["environment_sha256"] == environment_digest(
        build_child_environment({**environment, "APSEUDO_TEST_REQUIRE_AUTH": "1"})
    )


def test_prepare_and_capture__not_logged_in_text__records_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            {**environment, "APSEUDO_TEST_LOGIN_MESSAGE": "Not logged in"},
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "did not confirm a configured login")


def test_capture__env_shebang_without_exact_python3__records_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path, hook_shebang="/usr/bin/env python") as (
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

    _assert_preflight_bundle(
        result,
        evidence_root,
        "configured hook env shebang must be exactly /usr/bin/env python3",
    )


def test_prepare_and_capture__process_start_failure__records_complete_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = prepare_and_capture_guarded_runner(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            evidence_root=evidence_root,
            environment=environment,
            sync_argv=("missing-runner-capture-command",),
        )

    _assert_preflight_bundle(result, evidence_root, "executable was not found")


def test_capture__timeout__records_complete_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timed_out_hook(
        _clone: Path,
        _environment: Mapping[str, str],
    ) -> tuple[dict[str, object], str | None]:
        raise RunnerOperationalError("SessionStart hook preflight: timed out")

    monkeypatch.setattr(runner_capture_module, "_capture_hook", timed_out_hook)
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "SessionStart hook preflight: timed out")


@pytest.mark.parametrize(
    ("failed_operation", "expected_hook_status"),
    [
        pytest.param(
            "SessionStart hook preflight",
            "failed",
            id="hook-process-failure",
        ),
        pytest.param(
            "runner check",
            "passed",
            id="runner-failure-after-hook",
        ),
    ],
)
def test_capture__operational_failure__records_truthful_hook_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_operation: str,
    expected_hook_status: str,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        original_run = runner_capture_module.run_capture_process

        def fail_selected_operation(
            argv: Sequence[str],
            *,
            cwd: Path,
            environment: Mapping[str, str],
            timeout: int,
            operation: str,
            input_text: str | None = None,
            screen_output: bool = True,
        ) -> ProcessResult:
            if operation == failed_operation:
                raise RunnerOperationalError(f"{operation}: timed out")
            return original_run(
                argv,
                cwd=cwd,
                environment=environment,
                timeout=timeout,
                operation=operation,
                input_text=input_text,
                screen_output=screen_output,
            )

        monkeypatch.setattr(
            runner_capture_module,
            "run_capture_process",
            fail_selected_operation,
        )
        evidence_root = tmp_path / "promoted"
        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, f"{failed_operation}: timed out")
    hook = _json_object(evidence_root / "hook-preflight.json")
    assert hook["status"] == expected_hook_status


def test_capture__missing_focus__records_complete_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, _revision, runner, environment):
        state = repository / "docs/handoff/state.md"
        state.write_text(
            "# Session state\n\n## Current focus\n\n## Active incidents\n", encoding="utf-8"
        )
        _git(repository, "add", state.relative_to(repository).as_posix())
        _git(repository, "commit", "--quiet", "-m", "remove current focus")
        revision = _git(repository, "rev-parse", "HEAD")
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "has no current-focus bullet")


def test_capture__oversized_process_output__records_complete_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            {
                **environment,
                "APSEUDO_TEST_RUNNER_MODE": "oversized-output",
                "APSEUDO_TEST_OUTPUT_LIMIT": str(MAX_PROCESS_OUTPUT_BYTES),
            },
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "output exceeded")


def test_capture__oversized_artifact__records_complete_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            {
                **environment,
                "APSEUDO_TEST_RUNNER_MODE": "oversized-artifact",
                "APSEUDO_TEST_FILE_LIMIT": str(MAX_EVIDENCE_FILE_BYTES),
            },
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "exceeds the read limit")


def test_capture__git_report_failure__records_complete_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_git_report(_repository: Path) -> list[str]:
        raise RunnerOperationalError("Git changed-file report failed")

    monkeypatch.setattr(runner_capture_module, "_git_changed_files", failed_git_report)
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "Git changed-file report failed")


@pytest.mark.parametrize(
    "runner_mode",
    [
        "manifest-git-mismatch",
        "manifest-exit-string",
        "manifest-script-mismatch",
        "manifest-spec-mismatch",
        "manifest-nonobject",
        "agent-argv-nonstring",
        "agent-cwd-mismatch",
        "agent-prompt-mismatch",
        "agent-sandbox-mismatch",
        "agent-duplicate-sandbox",
        "provider-preview-mismatch",
        "post-returncode-string",
        "outcome-checks-nonstring",
    ],
)
def test_capture__mutated_runner_artifact__cannot_be_accepted(
    tmp_path: Path,
    runner_mode: str,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            {**environment, "APSEUDO_TEST_RUNNER_MODE": runner_mode},
            evidence_root,
        )

    assert result.mode == "preflight-only"
    assert set(result.evidence_hashes) == set(REQUIRED_EVIDENCE_NAMES)


def test_capture__unexecuted_runner_module_mutation__records_preflight(
    tmp_path: Path,
) -> None:
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        runtime = prepare_runner_runtime(
            repository,
            revision=revision,
            operator_python=runner.parent / "python",
            operator_apseudo_run=runner,
            environment=environment,
        )
        runtime_runner = runtime.module_path.with_name("runner.py")
        runtime_runner.write_text(
            runtime_runner.read_text(encoding="utf-8") + "# post-prepare mutation\n",
            encoding="utf-8",
        )
        evidence_root = tmp_path / "promoted"
        result = capture_guarded_runner(
            repository,
            revision=revision,
            runtime=runtime,
            evidence_root=evidence_root,
            environment=environment,
        )

    _assert_preflight_bundle(result, evidence_root, "operator package closure changed")


def test_capture__clone_start_failure__records_complete_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def failed_clone(
        _repository_root: Path,
        *,
        revision: str,
    ) -> Generator[Path]:
        del revision
        raise CaptureError("Git clone could not complete")
        yield tmp_path / "unreachable"

    monkeypatch.setattr(runner_capture_module, "clean_revision_clone", failed_clone)
    with _runner_repository(tmp_path) as (repository, revision, runner, environment):
        evidence_root = tmp_path / "promoted"
        result = _prepare_and_capture(
            repository,
            revision,
            runner,
            environment,
            evidence_root,
        )

    _assert_preflight_bundle(result, evidence_root, "Git clone could not complete")


def test_promotion__new_or_identical_bundle__is_exact_and_idempotent(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "evidence"
    bundle = _promotion_bundle("first")

    first = promote_evidence_bundle(destination, bundle)
    second = promote_evidence_bundle(destination, bundle)

    assert first == second
    assert {path.name for path in destination.iterdir()} == set(REQUIRED_EVIDENCE_NAMES)
    assert all(path.is_file() and not path.is_symlink() for path in destination.iterdir())


def test_promotion__different_existing_bundle__requires_recapture_authority(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "evidence"
    original = _promotion_bundle("original")
    replacement = _promotion_bundle("replacement")
    original_hashes = promote_evidence_bundle(destination, original)

    with pytest.raises(EvidencePromotionError, match="explicit recapture authority"):
        promote_evidence_bundle(destination, replacement)

    assert promote_evidence_bundle(destination, original) == original_hashes


def test_promotion__authorized_recapture__removes_stale_ninth_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "evidence"
    promote_evidence_bundle(destination, _promotion_bundle("original"))
    (destination / "stale.json").write_text("{}\n", encoding="utf-8")

    promote_evidence_bundle(
        destination,
        _promotion_bundle("replacement"),
        allow_recapture=True,
    )

    assert {path.name for path in destination.iterdir()} == set(REQUIRED_EVIDENCE_NAMES)


def test_promotion__mid_commit_failure__restores_original_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "evidence"
    original = _promotion_bundle("original")
    promote_evidence_bundle(destination, original)
    original_bytes = {path.name: path.read_bytes() for path in destination.iterdir()}
    real_replace = runner_evidence.replace_evidence_path
    stage_commit_attempted = False

    def fail_stage_commit(source: Path, target: Path) -> None:
        nonlocal stage_commit_attempted
        if target == destination and ".stage-" in source.name:
            stage_commit_attempted = True
            raise OSError("injected directory commit failure")
        real_replace(source, target)

    monkeypatch.setattr(runner_evidence, "replace_evidence_path", fail_stage_commit)

    with pytest.raises(EvidencePromotionError, match="directory commit failed"):
        promote_evidence_bundle(
            destination,
            _promotion_bundle("replacement"),
            allow_recapture=True,
        )

    assert stage_commit_attempted
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == original_bytes


def test_promotion__post_commit_validation_failure__restores_original_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "evidence"
    original = _promotion_bundle("original")
    promote_evidence_bundle(destination, original)
    original_bytes = {path.name: path.read_bytes() for path in destination.iterdir()}
    real_validate = runner_evidence.validate_evidence_directory
    validation_count = 0

    def fail_committed_validation(
        directory: Path,
        hashes: Mapping[str, str],
    ) -> None:
        nonlocal validation_count
        validation_count += 1
        if directory == destination and validation_count >= 3:
            raise EvidencePromotionError("injected committed validation failure")
        real_validate(directory, hashes)

    monkeypatch.setattr(
        runner_evidence,
        "validate_evidence_directory",
        fail_committed_validation,
    )

    with pytest.raises(EvidencePromotionError, match="committed validation"):
        promote_evidence_bundle(
            destination,
            _promotion_bundle("replacement"),
            allow_recapture=True,
        )

    assert validation_count == 3
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == original_bytes
