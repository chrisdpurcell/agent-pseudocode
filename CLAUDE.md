# Claude repository instructions

**Session state:** read `docs/handoff/state.md` first — live state and active incidents.

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
