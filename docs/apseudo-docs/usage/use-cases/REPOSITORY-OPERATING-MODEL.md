# Repository Operating Model

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Purpose

This document explains how to use Agent Pseudocode as a real repository convention while the project is still maintained as its own GitHub repo rather than a packaged `project-standards` standard.

## Recommended repository layout

For a project that consumes this toolkit, use this pattern:

```text
repo/
├── AGENTS.md
├── CLAUDE.md
├── .apseudo/
│   └── scripts.toml
├── .claude/
│   └── settings.json
├── .codex/
│   ├── config.toml
│   └── hooks.json
├── .github/
│   └── workflows/
│       └── apseudo-lint.yml
├── standards/
│   └── processes/
│       ├── review-loop.apseudo
│       ├── release-gate.apseudo
│       └── handoff-size-control.apseudo
└── docs/
    └── standards/
        └── agent-pseudocode.md
```

For this toolkit repository itself, the 0.6.1 layout keeps product/editor integrations under `products/`, shared hooks under `integrations/`, and docs grouped by purpose.

## What belongs at root

Keep only discovery/config files that tools expect at root:

- `AGENTS.md`;
- `CLAUDE.md`;
- `pyproject.toml`;
- `uv.lock`;
- `.pre-commit-config.yaml`;
- `.github/`;
- `.claude/`;
- `.codex/`;
- `.mcp.json`;
- `.apseudo/`;
- major project folders.

Everything else should live under grouped folders.

## Minimum adoption

Minimum useful adoption in another repo:

```text
AGENTS.md
CLAUDE.md
.apseudo/scripts.toml
.github/workflows/apseudo-lint.yml
standards/processes/*.apseudo
```

Minimum commands:

```bash
uv run apseudo-lint .
uv run apseudo-format --check .
uv run apseudo-review .
```

## Full adoption

Full adoption includes:

- VS Code extension or Kate integration;
- language server enabled;
- pre-commit hook;
- GitHub Actions CI check;
- Claude hooks;
- Codex hooks;
- MCP server;
- skill folders;
- registered runner scripts;
- run records under `.apseudo/runs/`.

Use full adoption for repos where agent processes are central to the development workflow.

## Day-to-day author workflow

### 1. Create or edit a process

Create:

```text
standards/processes/<process-name>.apseudo
```

Write the control flow. Keep prose in surrounding Markdown docs.

### 2. Format and validate

```bash
uv run apseudo-format standards/processes/<process-name>.apseudo
uv run apseudo-lint standards/processes/<process-name>.apseudo
```

### 3. Reference it from docs

```markdown
The normative process is `standards/processes/<process-name>.apseudo`.
If prose and pseudocode conflict, the agent must stop and surface the conflict.
```

### 4. Register it if it is executable

Add to `.apseudo/scripts.toml`:

```toml
[scripts.<task-name>]
path = "standards/processes/<process-name>.apseudo"
description = "Short task description."
default_agent = "codex"
default_mode = "apply"
```

### 5. Test the runner path

```bash
uv run apseudo run <task-name> --check
uv run apseudo run <task-name> --render-prompt -- arg=value
uv run apseudo run <task-name> --print-command -- arg=value
```

### 6. Run safely

Start in review mode:

```bash
uv run apseudo run <task-name> --review --require-no-diff --run-dir .apseudo/runs -- arg=value
```

Then apply with post-checks:

```bash
uv run apseudo run <task-name> --apply \
  --run-dir .apseudo/runs \
  --post-check "uv run apseudo-lint ." \
  --post-check "uv run pytest" \
  -- arg=value
```

## Day-to-day agent workflow

Agents should follow this order:

1. Read the relevant `.apseudo` file or fenced block.
2. Treat it as the control-flow source of truth.
3. Preserve loop bounds, guards, and outcomes.
4. Use MCP or `apseudo-explain` when a rule is unclear.
5. Run `apseudo-format --check`, `apseudo-lint`, and `apseudo-review` after edits.
6. Do not bypass hooks, pre-commit, CI, or runner validation.
7. If validation fails and cannot be fixed, return `Blocked` with evidence.

Put this wording in `AGENTS.md` and `CLAUDE.md`; see [`../AGENT-INSTRUCTIONS-WORDING.md`](../AGENT-INSTRUCTIONS-WORDING.md).

## When to make a runner script

Make a runner script when all of these are true:

- the workflow is repeatable;
- the workflow benefits from agent judgment;
- the workflow has clear outcomes;
- the workflow can be bounded;
- deterministic post-checks can verify success;
- run records would be useful.

Do not make a runner script when:

- the operation is purely deterministic;
- failure could destroy important state;
- the task requires secrets or production credentials;
- the task is better handled by CI or a normal script.

## Standard repo task set

A mature repo can define these registered tasks:

| Task | Provider | Mode | Purpose |
| --- | --- | --- | --- |
| `review-spec` | Claude | review | Critique specs without edits. |
| `amend-spec` | Claude or Codex | apply | Apply bounded spec-review amendments. |
| `fix-ruff` | Codex | apply | Repair Ruff findings. |
| `fix-pyright` | Codex | apply | Repair type-check findings. |
| `repair-docs` | Codex | apply | Fix docs validation issues. |
| `audit-agent-instructions` | Claude | review | Check `AGENTS.md`, `CLAUDE.md`, hooks, and skills. |
| `sync-template` | Codex | apply | Sync a template repo from standards. |

Generate a docs page from the registry:

```bash
uv run apseudo docs generate --output docs/usage/agent-tasks.md
```

## Recommended branch protection

For repos where this standard matters, require CI checks that run:

```bash
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
```

This makes the pseudocode convention enforceable, not merely advisory.

## Repository health checks

Use these before relying on the system:

```bash
uv run apseudo doctor
uv run apseudo provider-test --json
uv run apseudo-lint .
uv run apseudo-review .
```

If the project uses hooks, verify Claude/Codex show the hooks as trusted/enabled locally before relying on agent-runtime enforcement.
