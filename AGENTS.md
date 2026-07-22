# Agent instructions

**Session state:** Agent Handoff SessionStart injects `docs/handoff/state.md`; do not reread it when injected.
**Full conventions reference:** `docs/handoff/conventions.md`.
**Detailed review workflows:** not configured for this repo.

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

## Markdown and structured-text fix pass

The managed `markdown-tooling` block below states the policy. These are the commands.

When changing Markdown, JSON, JSONC, or YAML, run the fix pass first, then the non-mutating check:

```bash
npx prettier --write .
npx markdownlint-cli2 --fix "**/*.md"

npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Do not claim completion if either check fails. Do not edit `.prettierrc.json` or `.markdownlint.json` to bypass a check without a documented ADR exception — both are package-managed, so reconciliation reverts hand edits anyway.

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

Enabled checks: format, lint.
Markdown scope: `**/*.md`.
Structured-config scope: `**/*.json`, `**/*.jsonc`, `**/*.yml`, `**/*.yaml`.

Declared exclusions:
- `docs/reference/pre-migration/**` (both): Verbatim archived ChatGPT transcript; reformatting or annotating it would destroy the historical record. Already exempt from APSEUDO fence linting per bug 003.
- `package-lock.json` (format): npm regenerates this file and reverts Prettier's formatting on every install.

Run the enabled checks before claiming completion.
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:markdown-tooling -->

<!-- prettier-ignore-end -->

<!-- prettier-ignore-start -->

<!-- BEGIN project-standards:python-tooling -->
<!-- markdownlint-disable MD025 -->
# Python tooling

Use uv for environments and dependency changes. Ruff owns formatting, linting, and imports.
Use basedpyright in strict mode for type checking. Do not add a competing Python gate.

Run before claiming completion:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

When the gate reports formatting or lint findings, run:

```bash
uv run ruff format .
uv run ruff check . --fix
```
<!-- markdownlint-enable MD025 -->
<!-- END project-standards:python-tooling -->

<!-- prettier-ignore-end -->
