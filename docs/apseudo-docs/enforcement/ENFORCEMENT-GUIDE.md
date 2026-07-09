# Pythonic Agent Pseudocode Enforcement Guide

**Date:** 2026-07-08  
**Status:** Working implementation / internal convention

## Bottom line

This repository uses one validator everywhere:

```text
Pythonic pseudocode standard
        ↓
apseudo-lint CLI
        ↓
├─ pre-commit / pre-push
├─ GitHub Actions CI
├─ Claude Code lifecycle hooks
└─ Codex lifecycle hooks
```

The design rule is simple: **all policy logic lives in `src/apseudo_lint`; integrations only call it.** Do not reimplement rule logic in hook scripts, editor extensions, CI YAML, or agent instructions.

## What is sourced vs internal convention

| Area | Status | Notes |
|---|---|---|
| VS Code syntax highlighting | Sourced | VS Code uses TextMate grammars and supports injection grammars for Markdown fenced code blocks. |
| Kate highlighting | Sourced | Kate/KDE uses XML syntax definitions installed under KSyntaxHighlighting paths. |
| pre-commit | Sourced | Uses standard `.pre-commit-config.yaml` local hook configuration. |
| GitHub Actions | Sourced | Uses normal workflow YAML with checkout, Python setup, install, and validation steps. |
| Claude Code hooks | Sourced | Uses project `.claude/settings.json`, lifecycle events, matchers, command hooks, stdin JSON, and exit-code behavior. |
| Codex hooks | Sourced | Uses project `.codex/hooks.json`, event/matcher/handler nesting, command hooks, trust review, and `/hooks`. |
| `APSEUDO-*` rule IDs | Internal convention | Local policy names for this pseudocode standard. |
| Bounded-loop heuristics | Internal convention | Conservative linter heuristics, not formal termination proofs. |
| Approved outcomes | Internal convention | Defined in `.apseudo-lint.toml`. |

## Files added for enforcement

| Path | Purpose |
|---|---|
| `src/apseudo_lint/` | Shared Python validator package. |
| `scripts/apseudo-lint` | Install-free CLI wrapper using `PYTHONPATH=src`. |
| `.apseudo-lint.toml` | Project rule configuration. |
| `tests/` | Valid/invalid fixture tests for the validator. |
| `.pre-commit-config.yaml` | Local pre-commit and pre-push integration. |
| `.pre-commit-hooks.yaml` | Reusable hook manifest if this repository is consumed by another repo. |
| `.github/workflows/apseudo-lint.yml` | GitHub Actions CI gate. |
| `integrations/agent-hooks/apseudo-hook.py` | Host-neutral hook runner used by Claude Code and Codex. |
| `.claude/settings.json` | Claude Code project hooks. |
| `.codex/hooks.json` | Codex project hooks. |
| `AGENTS.md` | Codex/general agent instructions. |
| `CLAUDE.md` | Claude-specific instructions. |
| `scripts/install-enforcement.sh` | Local install helper. |
| `scripts/run-enforcement-smoke-test.sh` | Local end-to-end smoke test. |

## Local setup

From the repository root:

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-lint .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
```

The wrapper also works without package installation:

```bash
scripts/apseudo-lint .
scripts/apseudo-lint --changed
scripts/apseudo-lint --format json docs/apseudo-docs/examples/review-loop.apseudo
scripts/apseudo-lint --format github examples
```

## pre-commit and pre-push

Install hooks:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
uv run pre-commit run --all-files
```

The local hook calls:

```bash
uv run apseudo-lint <changed files>
```

The hook applies to:

```text
*.apseudo
*.agentpseudo
*.md
*.markdown
```

## GitHub Actions CI

The workflow is installed at:

```text
.github/workflows/apseudo-lint.yml
```

It runs on pull requests, pushes to `main`, and manual dispatch when pseudocode, Markdown, validator code, tests, project config, or the workflow changes.

The job runs:

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-lint .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
```

For hard enforcement, mark the `Validate pseudocode standard` job as a required branch-protection check.

## Claude Code hooks

Project hook config:

```text
.claude/settings.json
```

Configured events:

| Event | Purpose |
|---|---|
| `SessionStart` | Adds a short pseudocode-enforcement reminder. |
| `PostToolUse` | Runs after file-edit tools and validates changed pseudocode. |
| `Stop` | Validates changed pseudocode before final response. |

The command hook invokes:

```bash
python3 "${CLAUDE_PROJECT_DIR}/integrations/agent-hooks/apseudo-hook.py" --host claude --event <event>
```

The hook script reads JSON from stdin, resolves the repo root, runs `scripts/apseudo-lint --changed`, and exits `2` with diagnostic text on stderr when validation fails.

Operational notes:

1. Start Claude Code from inside the repository.
2. Inspect project hooks with `/hooks` before relying on them.
3. Treat hook failures as blockers; fix the reported `APSEUDO-*` diagnostics.

## Codex hooks

Project hook config:

```text
.codex/hooks.json
```

Configured events:

| Event | Purpose |
|---|---|
| `SessionStart` | Adds a short pseudocode-enforcement reminder. |
| `PostToolUse` | Runs after Bash/apply_patch/Edit/Write and validates changed pseudocode. |
| `Stop` | Validates changed pseudocode before turn completion. |

The command hook invokes:

```bash
/usr/bin/python3 "$(git rev-parse --show-toplevel)/integrations/agent-hooks/apseudo-hook.py" --host codex --event <event>
```

Operational notes:

1. Project-local hooks load only after the `.codex/` layer is trusted.
2. Open Codex in the repository and run `/hooks`.
3. Review and trust the exact hook definitions.
4. Re-review hooks after editing `.codex/hooks.json` or `integrations/agent-hooks/apseudo-hook.py`.

## Rule catalog

| Rule ID | Severity | Status | Meaning |
|---|---:|---|---|
| `APSEUDO-IO-001` | Error | Internal | File could not be read as UTF-8. |
| `APSEUDO-IO-002` | Error | Internal | File does not exist. |
| `APSEUDO-PARSE-001` | Error | Internal | Header syntax is malformed for the Pythonic pseudocode subset. |
| `APSEUDO-PARSE-002` | Error | Internal | Block header has no indented executable body. |
| `APSEUDO-PROC-001` | Warning | Internal | Full workflow block should declare `process name(...):` or `def name(...):` when configured. |
| `APSEUDO-RETURN-001` | Error | Internal | Process has no terminal return outcome. |
| `APSEUDO-RETURN-002` | Warning | Internal | Return value is missing or not an outcome constructor/name. |
| `APSEUDO-RETURN-003` | Warning | Internal | Process body should end with an explicit terminal statement. |
| `APSEUDO-OUTCOME-001` | Warning | Internal | Returned outcome is not in `.apseudo-lint.toml`. |
| `APSEUDO-WHILE-001` | Error | Internal | `while` loop lacks an obvious bound, cap, deadline, timeout, or annotation. |
| `APSEUDO-WHILE-002` | Warning | Internal | Loop body does not visibly update condition state or terminate. |
| `APSEUDO-WHILE-003` | Error | Internal | `while True` has no visible break, return, or raise. |
| `APSEUDO-FOR-001` | Warning | Internal | `for` loop iterable has unclear boundedness. |
| `APSEUDO-BRANCH-001` | Warning | Internal | Non-terminal `if`/`elif` chain lacks an explicit `else` fallback. |
| `APSEUDO-BRANCH-002` | Warning | Internal | Block body is only `pass` or `...`. |
| `APSEUDO-NEST-001` | Warning | Internal | Nesting exceeds configured max. |
| `APSEUDO-NORM-001` | Warning | Internal + RFC-style convention | Normative terms should be uppercase. |
| `APSEUDO-NORM-002` | Warning | Internal | `SHALL` is unsupported by this local convention. |
| `APSEUDO-ACTION-001` | Warning | Internal | Optional check: mutating action is not followed by visible verification. |
| `APSEUDO-ACTION-002` | Warning | Internal | Optional check: action/function name is not lower_snake_case. |

## Annotations

Annotations are comments on the same line or immediately preceding line.

| Annotation | Effect |
|---|---|
| `# @bounded` | Marks a loop/iteration source as intentionally bounded. |
| `# @external_stop_condition` | Allows loops controlled by external events, queues, or tools. |
| `# @explicit_stop_condition` | Documents a stop condition the heuristic cannot infer. |
| `# @timeout` | Documents a timeout-bounded loop. |
| `# @round_cap` | Documents a review/retry round cap. |
| `# @loop_cap` | Documents a general loop cap. |
| `# @intentional_infinite_loop` | Allows `while True` only when paired with reachable break/return/raise. |
| `# @exhaustive` | Allows a branch chain with no `else`. |
| `# @allow_empty_branch` | Allows `pass` / `...` placeholder bodies. |
| `# @allow_missing_process` | Allows snippets without `process`/`def` when process declaration is required. |
| `# @verified` | Marks a mutating action as verified. |
| `# @no_verification_required` | Marks a mutating action as intentionally not verified. |

Markdown can skip the next pseudocode fence:

````markdown
<!-- apseudo-lint: disable-next-fence -->
```apseudo
this example is intentionally invalid
```
````

A source line can suppress the next line:

```apseudo
# @allow_missing_process
# apseudo-lint: disable-next-line
while not externally_done:
    wait_for_event()
```

A source line can suppress specific diagnostics on that line:

```apseudo
# @allow_missing_process
while not externally_done:  # apseudo-lint: disable APSEUDO-WHILE-001 APSEUDO-WHILE-002
    wait_for_event()
```

## Configuration

Project defaults live in `.apseudo-lint.toml`.

Important keys:

```toml
max_nesting = 4
strict = false
fail_on_warning = false
require_process_declaration = true
require_verification_after_mutation = false
allowed_outcomes = ["Accepted", "Approved", "Blocked", "Rejected", "NeedsUserDecision", "NeedsInput", "OpenIssue", "Skipped", "Deferred", "Failed"]
markdown_fence_languages = ["apseudo", "agent-pseudocode", "agent_pseudocode", "pythonic-pseudocode", "pseudocode-pythonic"]
ignore_codes = []
```

Use `--strict` or `fail_on_warning = true` when warnings should fail CI/hook execution.

## Smoke test

```bash
scripts/run-enforcement-smoke-test.sh
```

This runs the unit tests, linter, Ruff, Pyright, and JSON validation for the Claude/Codex hook config files.

## Known limitations

This is a linter, not a theorem prover or full language server. It does not execute pseudocode, prove all paths terminate, or fully analyze helper-action side effects. The `while`, `for`, and branch checks are intentionally conservative and overrideable with annotations.

Use this operating model:

1. Treat linter errors as blockers.
2. Treat warnings as review prompts.
3. Prefer fixing unclear pseudocode over suppressing diagnostics.
4. Keep the rule set small and stable before adding LSP or MCP layers.

## Sources

- VS Code syntax highlighting guide: https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- VS Code contribution points: https://code.visualstudio.com/api/references/contribution-points
- Kate syntax highlighting docs: https://docs.kde.org/stable_kf6/en/kate/katepart/highlight.html
- pre-commit docs: https://pre-commit.com/
- GitHub Actions workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Claude Code hooks reference: https://code.claude.com/docs/en/hooks
- Codex hooks docs: https://developers.openai.com/codex/hooks
