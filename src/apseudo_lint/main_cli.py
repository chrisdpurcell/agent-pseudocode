"""Unified `apseudo` command group."""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnnecessaryIsInstance=false, reportOptionalSubscript=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from . import __version__, format_cli, mermaid_cli, review_cli, runner_cli
from . import cli as lint_cli
from .runner import EXIT_CONFIG_INVALID


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(_help())
        return 0
    if args[0] in {"-V", "--version", "version"}:
        print(f"apseudo {__version__}")
        return 0
    command, rest = args[0], args[1:]
    if command == "lint":
        return lint_cli.main(rest)
    if command == "format":
        return format_cli.main(rest)
    if command == "review":
        return review_cli.main(rest)
    if command == "mermaid":
        return mermaid_cli.main(rest)
    if command == "run":
        return runner_cli.main(_resolve_registry_name(rest))
    if command == "doctor":
        return _doctor(rest)
    if command == "provider-test":
        return _provider_test(rest)
    if command == "docs":
        return _docs(rest)
    if command == "replay":
        if not rest:
            print("apseudo replay: missing run directory", file=sys.stderr)
            return EXIT_CONFIG_INVALID
        return runner_cli.main(["--replay", rest[0], *rest[1:]])
    print(f"apseudo: unknown command: {command}", file=sys.stderr)
    return 2


def _help() -> str:
    return f"""apseudo {__version__} — Agent Pseudocode toolkit

Usage:
  apseudo <command> [<args>...]

Commands:
  lint        Validate .apseudo files and Markdown fenced blocks.
  format      Format .apseudo files and Markdown fenced blocks.
  review      Run project-level completeness checks.
  mermaid     Render a Mermaid view for a pseudocode process.
  run         Execute an executable .apseudo script through Claude or Codex.
  replay      Summarize a saved runner run directory.
  doctor      Check local provider/tool availability.
  provider-test  Run a fake-provider runner smoke test.
  docs generate  Generate Markdown docs for registered executable scripts.

Examples:
  apseudo lint .
  apseudo format --check .
  apseudo run --codex --apply fix-ruff -- target=src
  apseudo doctor --json
""".rstrip()


def _registry_path(cwd: Path | None = None) -> Path | None:
    start = cwd or Path.cwd()
    for directory in [start, *start.parents]:
        path = directory / ".apseudo" / "scripts.toml"
        if path.exists():
            return path
    return None


def _load_registry() -> dict[str, Any]:
    path = _registry_path()
    if path is None:
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _resolve_registry_name(args: list[str]) -> list[str]:
    if not args:
        return args
    registry = _load_registry()
    scripts = registry.get("scripts")
    if not isinstance(scripts, dict):
        return args
    split_index = args.index("--") if "--" in args else len(args)
    before = list(args[:split_index])
    after = args[split_index:]
    for index, token in enumerate(before):
        if token.startswith("-"):
            continue
        if token in scripts and isinstance(scripts[token], dict):
            entry = scripts[token]
            path = entry.get("path")
            if isinstance(path, str):
                before[index] = path
                return [*before, *after]
    return args


def _doctor(args: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="apseudo doctor")
    parser.add_argument("--claude", action="store_true", help="Only check Claude Code.")
    parser.add_argument("--codex", action="store_true", help="Only check Codex CLI.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    ns = parser.parse_args(args)
    providers = []
    if not ns.codex:
        providers.append(_provider_status("claude", "claude"))
    if not ns.claude:
        providers.append(_provider_status("codex", "codex"))
    payload = {
        "toolkit_version": __version__,
        "providers": providers,
        "hooks": {
            "claude_settings": Path(".claude/settings.json").exists(),
            "codex_hooks": Path(".codex/hooks.json").exists(),
            "mcp_config": Path(".mcp.json").exists(),
        },
        "registry": str(_registry_path()) if _registry_path() else None,
    }
    if ns.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for provider in providers:
            available = "yes" if provider["available"] else "no"
            print(f"{provider['name']}: available={available} path={provider.get('path') or '-'}")
        print(
            f"hooks: claude={payload['hooks']['claude_settings']} codex={payload['hooks']['codex_hooks']} mcp={payload['hooks']['mcp_config']}"
        )
        print(f"registry: {payload['registry'] or '-'}")
    return 0 if all(provider["available"] for provider in providers) else 1


def _provider_status(name: str, command: str) -> dict[str, object]:
    path = shutil.which(command)
    status: dict[str, object] = {
        "name": name,
        "command": command,
        "available": path is not None,
        "path": path,
    }
    if path is not None:
        result = subprocess.run(
            [path, "--version"], text=True, capture_output=True, check=False, timeout=10
        )
        status["version_output"] = (result.stdout or result.stderr).strip()
        status["version_returncode"] = result.returncode
    return status


def _provider_test(args: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="apseudo provider-test")
    parser.add_argument("--json", action="store_true")
    ns = parser.parse_args(args)
    with tempfile.TemporaryDirectory(prefix="apseudo-provider-test-") as raw:
        root = Path(raw)
        provider = root / "fake-agent"
        provider.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "_ = sys.stdin.read()\n"
            "print(json.dumps({'outcome':'Accepted','reason':'fake provider ok','summary':'provider test passed','checks_run':['fake-provider'],'artifacts':[]}))\n",
            encoding="utf-8",
        )
        provider.chmod(0o755)
        script = root / "test.apseudo"
        script.write_text(
            "---\nname: provider_test\ndefault_agent: codex\nmode: review\n---\n\n"
            'process provider_test():\n    return Accepted(reason="ok")\n',
            encoding="utf-8",
        )
        result = runner_cli.main(["--codex", "--agent-command", str(provider), str(script)])
    payload = {"passed": result == 0, "exit_code": result}
    if ns.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("provider-test passed" if result == 0 else "provider-test failed")
    return result


def _docs(args: list[str]) -> int:
    if not args or args[0] != "generate":
        print("usage: apseudo docs generate [--output <path>]", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="apseudo docs generate")
    parser.add_argument("--output", type=Path, default=Path("docs/usage/agent-tasks.md"))
    ns = parser.parse_args(args[1:])
    registry = _load_registry()
    scripts = registry.get("scripts")
    if not isinstance(scripts, dict):
        print("apseudo docs generate: no .apseudo/scripts.toml registry found", file=sys.stderr)
        return EXIT_CONFIG_INVALID
    lines = ["# Agent Pseudocode Tasks", "", "Generated from `.apseudo/scripts.toml`.", ""]
    for name, raw in sorted(scripts.items()):
        if not isinstance(raw, dict):
            continue
        path = raw.get("path")
        description = raw.get("description", "")
        lines.extend(
            [
                f"## `{name}`",
                "",
                str(description) if description else "No description provided.",
                "",
            ]
        )
        if isinstance(path, str):
            lines.extend(["```bash", f"apseudo run --codex {name} --", "```", ""])
            try:
                script = Path(path)
                if script.exists():
                    parsed = __import__(
                        "apseudo_lint.executable", fromlist=["parse_executable_file"]
                    ).parse_executable_file(script)
                    if parsed.metadata.args:
                        lines.append("Arguments:")
                        for arg_name in parsed.metadata.args:
                            lines.append(f"- `{arg_name}`")
                        lines.append("")
            except Exception:
                pass
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {ns.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
