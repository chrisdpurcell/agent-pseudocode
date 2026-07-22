# Claude repository instructions

**Session state:** Agent Handoff SessionStart injects `docs/handoff/state.md`; do not reread it when injected.

## Repository purpose

Implements the Pythonic Agent Pseudocode convention and its tooling: syntax highlighting, formatter, validator, language server, MCP server, hooks, skills, CI, docs.

## Pythonic Agent Pseudocode

Use the project `agent-pseudocode` skill and local validation tools whenever the task mentions pseudocode, APSEUDO-\* rules, process specs, agent workflows, bounded retry loops, or Markdown `apseudo` fences.

Hard requirements:

- Follow `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`.
- `apseudo-lint`/`apseudo-format` are the source of truth for compliance/formatting.
- Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before completion.
- Use `scripts/apseudo-explain <RULE>` for unclear diagnostics.
- Do not claim completion with APSEUDO-\* errors remaining.
- No `--no-verify`, `SKIP=...`, disabled hooks, or other enforcement bypasses.

## Development commands

```bash
uv sync
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run basedpyright
```

## Python code style

Follows `python-coding`; use the `python-expert` skill (front door to `python-coding` + `python-tooling` — canon wins on conflict).

## Tooling architecture

Validator and formatter are the policy source of truth. LSP, MCP, hooks, pre-commit, CI, VS Code, Kate must reuse those modules, never reimplement rules.

## Key docs

`docs/adr/README.md` — architecture decision records.

## Executable Agent Pseudocode runner

Use `apseudo-run`/`apseudo run` for executable `.apseudo` scripts. Before trusting a new/edited runner script, run `uv run apseudo-run --check`, `--render-prompt`, `--print-command`. Prefer `--run-dir .apseudo/runs`. Do not bypass runner post-checks, diff policy, hooks, pre-commit, or CI.

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:agent-handoff -->
<!-- markdownlint-disable MD025 -->
# Agent Handoff

Use the repo-local `agent-handoff` skill at session startup and closeout. Do not reread state already injected by SessionStart. Keep project knowledge inside this repository and store credential references only, never values.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:agent-handoff -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:markdown-tooling -->
<!-- markdownlint-disable MD025 -->
# Markdown and structured-text tooling

Prettier owns physical formatting and markdownlint owns Markdown structure. Do not add overlapping tools.

Enabled checks: lint.
Markdown scope: `**/*.md`.
Structured-config scope: `**/*.json`, `**/*.jsonc`, `**/*.yml`, `**/*.yaml`.

Run the enabled checks before claiming completion.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-tooling -->

<!-- prettier-ignore-end -->
