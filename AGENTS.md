# Agent instructions

## Repository purpose

This repository implements the Pythonic Agent Pseudocode convention and its tooling: syntax highlighting, formatter, validator, language server, MCP server, hooks, skills, CI, and documentation.

## Pythonic Agent Pseudocode requirements

Codex MUST use the repository Pythonic Agent Pseudocode tooling for any task involving agent workflows, process instructions, `.apseudo` files, `.agentpseudo` files, `.pseudocode` files, or Markdown `apseudo` fences.

Required behavior:

1. Use the `agent-pseudocode` skill when available.
2. Use the `agent_pseudocode` MCP server when available for validation, rule explanations, templates, and project review.
3. Run `scripts/apseudo-template --list` before drafting a new workflow unless the user supplied a complete structure.
4. Run `scripts/apseudo-format --check --changed` before `scripts/apseudo-lint --changed`.
5. Do not finish while APSEUDO-\* errors remain.
6. Do not bypass `pre-commit`, CI, hooks, or validation.
7. If a rule appears inappropriate, surface the rule ID, rationale, and proposed standard change instead of suppressing it.

Completion statement requirement:

- If pseudocode files changed, report the formatter/linter status in the final response.

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

## Style

- Python 3.11+.
- Keep runtime dependencies minimal.
- Keep editor integrations thin; do not duplicate policy outside `src/apseudo_lint`.
- Keep examples deterministic and validation-friendly.

## Executable Agent Pseudocode runner

Use `apseudo-run` or `apseudo run` for executable `.apseudo` task scripts. Before trusting a new or edited runner script, run `uv run apseudo-run --check`, `--render-prompt`, and `--print-command`. Prefer `--run-dir .apseudo/runs` for auditable runs. Do not bypass runner post-checks, diff policy, hooks, pre-commit, or CI.
