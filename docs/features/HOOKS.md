# Claude Code and Codex Hook Enforcement

**Shared hook script:** `integrations/agent-hooks/apseudo-hook.py`

## Events covered

| Event | Claude Code | Codex CLI | Behavior |
|---|---:|---:|---|
| SessionStart | Yes | Yes | Injects pseudocode enforcement context. |
| UserPromptSubmit | Yes | Yes | Adds context when the prompt appears pseudocode-related. |
| PreToolUse | Yes | Yes | Blocks common enforcement bypass attempts before tools run. |
| PermissionRequest | Yes | Yes | Blocks bypass attempts that surface at approval time. |
| PostToolUse | Yes | Yes | Runs `apseudo-format --check --changed` and `apseudo-lint --changed`. |
| SubagentStop | Yes | Yes | Re-checks changed pseudocode after subagent work. |
| Stop | Yes | Yes | Re-checks before the final answer. |

## Bypass policy

The hook blocks commands that attempt to bypass or modify enforcement without an explicit standard-change workflow, including:

- `git commit --no-verify`
- `SKIP=...`
- `pre-commit uninstall`
- edits to `.apseudo-lint.toml`
- edits to `integrations/agent-hooks/apseudo-hook.py`
- edits to `.claude/settings.json`
- edits to `.codex/hooks.json`

This is intentionally narrow. It protects the pseudocode standard; it is not a general-purpose shell sandbox.

## Audit log

Hook executions write JSONL records under:

```text
.cache/apseudo-hooks/audit.jsonl
```

This path is ignored by Git. It is useful when debugging why an agent was blocked.

## Local test

```bash
printf '%s' '{"cwd":"'"$PWD"'","tool_name":"Bash","tool_input":{"command":"git commit --no-verify"}}' \
  | python3 integrations/agent-hooks/apseudo-hook.py --host codex --event pre-tool-use
```

The command should exit with status `2` and explain the bypass.
