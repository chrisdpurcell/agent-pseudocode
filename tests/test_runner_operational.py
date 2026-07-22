from __future__ import annotations

import json
from pathlib import Path

import pytest

from apseudo_lint.executable import parse_executable_file
from apseudo_lint.main_cli import main as apseudo_main
from apseudo_lint.runner import RunnerOptions, build_agent_command, load_invocation, script_help
from apseudo_lint.runner_cli import main as runner_main


def _fake_agent(path: Path) -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, pathlib, sys\n"
        "_prompt = sys.stdin.read()\n"
        "payload = {'outcome':'Accepted','reason':'ok','summary':'fake provider completed','checks_run':['fake'], 'artifacts':[]}\n"
        "if '--output-last-message' in sys.argv:\n"
        "    out = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])\n"
        "    out.parent.mkdir(parents=True, exist_ok=True)\n"
        "    out.write_text(json.dumps(payload), encoding='utf-8')\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _script(path: Path) -> Path:
    path.write_text(
        "#!/usr/bin/env apseudo-run\n"
        "---\n"
        "name: operational_demo\n"
        "description: Demonstrate runner operational features.\n"
        "default_agent: codex\n"
        "mode: review\n"
        "args:\n"
        "  target:\n"
        "    type: path\n"
        "    required: false\n"
        "    default: .\n"
        "    description: Target path.\n"
        "---\n\n"
        "process operational_demo(target='.'):\n"
        '    return Accepted(reason="ok")\n',
        encoding="utf-8",
    )
    return path


def test_runner_writes_run_record_outputs_and_post_checks(tmp_path: Path) -> None:
    fake = _fake_agent(tmp_path / "fake-codex")
    script = _script(tmp_path / "demo.apseudo")
    run_dir = tmp_path / "runs"
    output = tmp_path / "outcome.json"
    prompt = tmp_path / "prompt.md"
    schema = tmp_path / "schema.json"
    events = tmp_path / "events.jsonl"

    result = runner_main(
        [
            "--codex",
            "--agent-command",
            str(fake),
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
            "--prompt-out",
            str(prompt),
            "--schema-out",
            str(schema),
            "--events",
            str(events),
            "--post-check",
            "python3 -c 'print(123)'",
            str(script),
            "--",
            "target=src",
        ]
    )

    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8"))["outcome"] == "Accepted"
    assert "process operational_demo" in prompt.read_text(encoding="utf-8")
    assert json.loads(schema.read_text(encoding="utf-8"))["type"] == "object"
    records = list(run_dir.iterdir())
    assert len(records) == 1
    assert (records[0] / "manifest.json").exists()
    assert (records[0] / "rendered-prompt.md").exists()
    assert (records[0] / "post-checks.json").exists()
    assert events.exists()


def test_runner_command_includes_operational_codex_flags(tmp_path: Path) -> None:
    script = _script(tmp_path / "demo.apseudo")
    invocation = load_invocation(
        script,
        options=RunnerOptions(
            agent="codex",
            mode="apply",
            sandbox="workspace-write",
            approval_policy="never",
            add_dirs=(tmp_path / "other",),
            ephemeral=True,
            hermetic=True,
            resume_last=True,
        ),
        raw_script_args=[],
    )
    command = build_agent_command(invocation, "prompt", tmp_path)

    assert command.argv[:3] == ["codex", "exec", "resume"]
    assert "--last" in command.argv
    assert ["--ask-for-approval", "never"]
    assert "--ephemeral" in command.argv
    assert "--ignore-user-config" in command.argv
    assert "--add-dir" in command.argv


def test_script_specific_help_uses_arg_schema(tmp_path: Path) -> None:
    script = parse_executable_file(_script(tmp_path / "demo.apseudo"))
    text = script_help(script, prog="demo.apseudo")

    assert "operational_demo" in text
    assert "target" in text
    assert "Target path" in text


def test_unified_cli_doctor_and_registry_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _script(tmp_path / "demo.apseudo")
    registry_dir = tmp_path / ".apseudo"
    registry_dir.mkdir()
    (registry_dir / "scripts.toml").write_text(
        f'[scripts.demo]\npath = "{script}"\ndescription = "Demo task."\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    docs_result = apseudo_main(["docs", "generate", "--output", "docs/tasks.md"])
    doctor_result = apseudo_main(["doctor", "--json"])

    assert docs_result == 0
    assert (tmp_path / "docs" / "tasks.md").exists()
    assert doctor_result in {0, 1}
