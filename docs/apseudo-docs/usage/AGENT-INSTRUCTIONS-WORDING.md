# Repository Agent Instruction Wording

**Purpose:** Copy these blocks into repositories that should follow the Pythonic Agent Pseudocode convention.

## Universal short block

Use this when you only have one place for instructions.

```md
## Pythonic Agent Pseudocode

When creating or editing `.apseudo`, `.agentpseudo`, `.pseudocode`, or Markdown fenced blocks tagged `apseudo`, `agent-pseudocode`, `agent_pseudocode`, `pythonic-pseudocode`, or `pseudocode-pythonic`:

- Follow the Pythonic Agent Pseudocode standard in `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`.
- Use `process name(...):` for complete workflows.
- Use explicit `if / elif / else`, bounded `while`, visibly finite `for`, and approved terminal outcomes.
- Do not leave unbounded loops, implicit fallthrough branches, placeholder bodies, or ambiguous returns.
- Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before declaring completion.
- If validation fails, fix the pseudocode or report the exact APSEUDO-* rule ID and blocker.
- Do not bypass hooks, pre-commit, CI, or validation with `--no-verify`, `SKIP=...`, disabled hooks, or ignored checks.
```

## AGENTS.md block for Codex

```md
# Agent instructions

## Pythonic Agent Pseudocode

Codex MUST use the repository Pythonic Agent Pseudocode tooling for any task involving agent workflows, process instructions, `.apseudo` files, `.agentpseudo` files, `.pseudocode` files, or Markdown `apseudo` fences.

Required behavior:

1. Use the `agent-pseudocode` skill when available.
2. Use the `agent_pseudocode` MCP server when available for validation, rule explanations, templates, and project review.
3. Run `scripts/apseudo-template --list` before drafting a new workflow unless the user supplied a complete structure.
4. Run `scripts/apseudo-format --check --changed` before `scripts/apseudo-lint --changed`.
5. Do not finish while APSEUDO-* errors remain.
6. Do not bypass `pre-commit`, CI, hooks, or validation.
7. If a rule appears inappropriate, surface the rule ID, rationale, and proposed standard change instead of suppressing it.

Completion statement requirement:

- If pseudocode files changed, report the formatter/linter status in the final response.
```

## CLAUDE.md block for Claude Code

```md
# Claude repository instructions

## Pythonic Agent Pseudocode

Use the project `agent-pseudocode` skill and local validation tools whenever the task mentions pseudocode, APSEUDO-* rules, process specs, agent workflows, bounded retry loops, or Markdown `apseudo` fences.

Hard requirements:

- Follow `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`.
- Treat `apseudo-lint` as the source of truth for structural compliance.
- Treat `apseudo-format` as the source of truth for formatting.
- Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before completion.
- Use `scripts/apseudo-explain <RULE>` for any unclear diagnostic.
- Do not claim completion if APSEUDO-* errors remain.
- Do not use `git commit --no-verify`, `SKIP=...`, disabled hooks, or other enforcement bypasses.
```

## One-off prompt for an agent

```text
Use the Pythonic Agent Pseudocode convention. Write workflows as Python-shaped pseudocode with `process name(...):`, explicit `if / elif / else`, bounded `while` loops, finite `for` loops, and terminal outcomes such as `Accepted(...)`, `Blocked(...)`, or `NeedsUserDecision(...)`. Validate with `apseudo-format` and `apseudo-lint`; do not complete until validation is clean or you have surfaced exact APSEUDO-* blockers.
```

## Pull request review checklist

```md
## Pseudocode review checklist

- [ ] New or changed pseudocode uses `process name(...):` for complete workflows.
- [ ] Every `while` loop has a visible cap, timeout, deadline, counter, or documented external stop condition.
- [ ] Every `for` loop iterates over a visibly finite collection.
- [ ] Every `if / elif` chain has an `else` fallback or `@exhaustive` rationale.
- [ ] Every process terminates with an approved outcome.
- [ ] Mutating actions are followed by verification where required.
- [ ] `scripts/apseudo-format --check .` passes.
- [ ] `scripts/apseudo-lint .` passes.
```

## Directory-specific override

```md
## Local pseudocode override

This directory may define domain-specific outcomes in `.apseudo-lint.toml`, but it MUST NOT weaken bounded-loop, fallback-branch, terminal-outcome, or placeholder-body rules without a documented rationale.
```

## Executable Agent Pseudocode runner instructions

Use this block in repositories that include executable `.apseudo` scripts.

```md
## Executable Agent Pseudocode scripts

Files with a shebang such as `#!/usr/bin/env apseudo-run` are executable Agent Pseudocode task launchers. They are not Python or Bash scripts. Treat their pseudocode body as the normative workflow and their frontmatter as runner metadata.

When asked to use or edit an executable `.apseudo` script:

- Preserve the shebang, frontmatter delimiters, and `process name(...):` body.
- Do not remove loop bounds, fallback branches, safety gates, verification actions, or terminal outcomes.
- Validate edits with `uv run apseudo-run --check <script.apseudo>`.
- Preview new or changed execution behavior with `uv run apseudo-run --render-prompt <script.apseudo> -- <args>` before running it.
- Use `--plan` or `--review` before `--apply` when the script is new or safety-sensitive.
- Do not use `--danger` or Codex `danger-full-access` unless explicitly instructed by the user in the current conversation.
- If the script, repo instructions, hooks, or tool output conflict, stop and return/surface `NeedsUserDecision` or `Blocked` instead of inventing alternate behavior.

Allowed executable-runner commands:

```bash
uv run apseudo-run --check <script.apseudo>
uv run apseudo-run --render-prompt <script.apseudo> -- <key=value>...
uv run apseudo-run --print-command <script.apseudo> -- <key=value>...
uv run apseudo-run --claude --review <script.apseudo> -- <key=value>...
uv run apseudo-run --codex --apply <script.apseudo> -- <key=value>...
```

Before completing work that creates or edits executable pseudocode, run:

```bash
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-run --check <each changed executable .apseudo script>
uv run apseudo-review .
```
```

## Executable runner instructions for repositories

Add this block to `AGENTS.md` and `CLAUDE.md` in repositories that adopt executable `.apseudo` tasks:

```md
## Executable Agent Pseudocode

This repository may contain executable Agent Pseudocode scripts ending in `.apseudo` or `.agentpseudo`, and a task registry at `.apseudo/scripts.toml`.

Treat executable pseudocode as a process contract. Do not reinterpret it as Python, Bash, or prose. Follow the declared guards, bounded loops, terminal outcomes, post-check expectations, and runner mode.

Before editing executable pseudocode, run:

```bash
uv run apseudo-run --check <script.apseudo>
```

Before executing a new or changed executable script, inspect both:

```bash
uv run apseudo-run --render-prompt <script.apseudo> -- <args>
uv run apseudo-run --print-command <script.apseudo> -- <args>
```

When using an executable script to perform work, prefer a run record:

```bash
uv run apseudo-run --run-dir .apseudo/runs <agent/mode flags> <script.apseudo> -- <args>
```

Do not bypass `apseudo-lint`, `apseudo-format`, pre-commit, CI, hooks, post-checks, or diff policy. If a runner script conflicts with prose, existing implementation, or repo instructions, stop and surface the conflict instead of guessing.
```
