# Claude repository instructions

**Session state:** read `docs/handoff/state.md` first — live state and active incidents.

## Repository purpose

This repository implements the Pythonic Agent Pseudocode convention and its tooling: syntax highlighting, formatter, validator, language server, MCP server, hooks, skills, CI, and documentation.

## Pythonic Agent Pseudocode

Use the project `agent-pseudocode` skill and local validation tools whenever the task mentions pseudocode, APSEUDO-\* rules, process specs, agent workflows, bounded retry loops, or Markdown `apseudo` fences.

Hard requirements:

- Follow `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`.
- Treat `apseudo-lint` as the source of truth for structural compliance.
- Treat `apseudo-format` as the source of truth for formatting.
- Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before completion.
- Use `scripts/apseudo-explain <RULE>` for any unclear diagnostic.
- Do not claim completion if APSEUDO-\* errors remain.
- Do not use `git commit --no-verify`, `SKIP=...`, disabled hooks, or other enforcement bypasses.

## Development commands

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
```

## Tooling architecture

The validator and formatter are the policy source of truth. The language server, MCP server, hooks, pre-commit, CI, VS Code, and Kate integrations must call or reuse those modules rather than reimplementing rules.

## Key docs

| Doc | When to read |
| --- | --- |
| `docs/adr/README.md` | Architecture decision records — index of accepted decisions and their rationale. |

## Executable Agent Pseudocode runner

Use `apseudo-run` or `apseudo run` for executable `.apseudo` task scripts. Before trusting a new or edited runner script, run `uv run apseudo-run --check`, `--render-prompt`, and `--print-command`. Prefer `--run-dir .apseudo/runs` for auditable runs. Do not bypass runner post-checks, diff policy, hooks, pre-commit, or CI.
