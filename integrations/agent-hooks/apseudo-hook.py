#!/usr/bin/env python3
"""Host-neutral hooks for Pythonic Agent Pseudocode enforcement.

Claude Code and Codex both invoke this script with a JSON payload on stdin. The
script avoids model reasoning and calls the shared formatter/linter. It also
blocks common enforcement bypasses before tool execution.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CONTEXT = """Pythonic Agent Pseudocode enforcement is active for this repository.
When editing `.apseudo`, `.agentpseudo`, `.pseudocode`, or Markdown `apseudo` fenced blocks, run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before declaring completion. Do not bypass formatting, hooks, pre-commit, CI, or APSEUDO-* errors. Fix the pseudocode or surface the rule ID and rationale.
""".strip()

PSEUDOCODE_KEYWORDS = re.compile(
    r"\b(apseudo|agent[-_ ]pseudocode|pseudocode|APSEUDO-|MUST|SHOULD|while loop|bounded loop)\b",
    re.IGNORECASE,
)
BYPASS_PATTERNS = (
    re.compile(r"\b--no-verify\b"),
    re.compile(r"\bSKIP\s*="),
    re.compile(r"\bpre-commit\s+uninstall\b"),
    re.compile(r"\.pre-commit-config\.yaml"),
    re.compile(r"\.apseudo-lint\.toml"),
    re.compile(r"integrations/agent-hooks/apseudo-hook\.py"),
    re.compile(r"\.claude/settings\.json"),
    re.compile(r"\.codex/hooks\.json"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Pseudocode lifecycle enforcement.")
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument(
        "--event",
        choices=(
            "session-start",
            "user-prompt-submit",
            "pre-tool-use",
            "permission-request",
            "post-tool-use",
            "subagent-stop",
            "stop",
        ),
        required=True,
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as blocking errors.")
    args = parser.parse_args(argv)

    payload = _read_json_stdin()
    repo_root = _repo_root(payload)
    status = "ok"
    detail = ""

    try:
        if args.event == "session-start":
            print(CONTEXT)
            return 0

        if args.event == "user-prompt-submit":
            prompt = _prompt_from_payload(payload)
            if PSEUDOCODE_KEYWORDS.search(prompt):
                print(CONTEXT)
            return 0

        if args.event in {"pre-tool-use", "permission-request"}:
            command = _command_from_payload(payload)
            bypass_reason = _bypass_reason(command)
            if bypass_reason is not None:
                status = "blocked"
                detail = bypass_reason
                print(_block_message(args.host, args.event, bypass_reason), file=sys.stderr)
                return 2
            return 0

        format_result = _run_formatter(repo_root)
        if format_result.returncode != 0:
            status = "blocked"
            detail = _combined_output(format_result)
            print(_failure_message(args.host, args.event, format_result, "apseudo-format"), file=sys.stderr)
            return 2

        result = _run_linter(repo_root, strict=args.strict)
        if result.returncode == 0:
            return 0

        status = "blocked"
        detail = _combined_output(result)
        print(_failure_message(args.host, args.event, result, "apseudo-lint"), file=sys.stderr)
        return 2
    finally:
        _audit(repo_root, host=args.host, event=args.event, status=status, detail=detail, payload=payload)


def _read_json_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _repo_root(payload: dict[str, Any]) -> Path:
    for key in ("cwd", "project_dir", "workspace", "repo_root"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            candidate = Path(value).expanduser().resolve()
            root = _git_root(candidate)
            if root is not None:
                return root
            if candidate.exists():
                return candidate

    env_candidate = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR")
    if env_candidate:
        candidate = Path(env_candidate).expanduser().resolve()
        root = _git_root(candidate)
        if root is not None:
            return root
        if candidate.exists():
            return candidate

    return _git_root(Path.cwd()) or Path.cwd()


def _git_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return Path(value).resolve() if value else None


def _command_from_payload(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("command", "cmd", "script"):
            value = tool_input.get(key)
            if isinstance(value, str):
                return value
    for key in ("command", "cmd"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def _prompt_from_payload(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_prompt", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        parts = [str(item) for item in messages if isinstance(item, str | dict)]
        return "\n".join(parts)
    return ""


def _bypass_reason(command: str) -> str | None:
    if not command:
        return None
    if "git commit" in command and "--no-verify" in command:
        return "git commit --no-verify bypasses pseudocode pre-commit enforcement"
    for pattern in BYPASS_PATTERNS:
        if pattern.search(command):
            return f"command appears to modify or bypass pseudocode enforcement: {pattern.pattern}"
    return None


def _run_formatter(repo_root: Path) -> subprocess.CompletedProcess[str]:
    command = [str(repo_root / "scripts" / "apseudo-format"), "--check", "--changed"]
    return _run(command, repo_root)


def _run_linter(repo_root: Path, strict: bool) -> subprocess.CompletedProcess[str]:
    command = [str(repo_root / "scripts" / "apseudo-lint"), "--changed"]
    if strict:
        command.append("--strict")
    return _run(command, repo_root)


def _run(command: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(command, returncode=1, stdout="", stderr=str(exc))


def _failure_message(host: str, event: str, result: subprocess.CompletedProcess[str], tool: str) -> str:
    body = _combined_output(result) or f"{tool} failed without output."
    return (
        f"{tool} blocked {host} {event}: pseudocode validation failed.\n\n"
        f"{body}\n\n"
        "Fix formatting or APSEUDO-* errors before continuing. Warnings are non-blocking unless strict mode is enabled."
    )


def _block_message(host: str, event: str, reason: str) -> str:
    return (
        f"apseudo-hook blocked {host} {event}: {reason}.\n\n"
        "Run the normal formatter/linter/pre-commit path instead of bypassing enforcement."
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()


def _audit(
    repo_root: Path,
    *,
    host: str,
    event: str,
    status: str,
    detail: str,
    payload: dict[str, Any],
) -> None:
    try:
        run_dir = os.environ.get("APSEUDO_RUN_DIR")
        if run_dir:
            directory = Path(run_dir).expanduser().resolve()
            audit_path = directory / "hook-audit.jsonl"
        else:
            directory = repo_root / ".cache" / "apseudo-hooks"
            audit_path = directory / "audit.jsonl"
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": os.environ.get("APSEUDO_RUN_ID"),
            "host": host,
            "event": event,
            "status": status,
            "detail": detail[:4000],
            "tool_name": payload.get("tool_name"),
            "cwd": payload.get("cwd"),
        }
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        return


if __name__ == "__main__":
    raise SystemExit(main())
