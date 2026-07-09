# Adopt agent-handoff-v3 and project-standards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt the agent-handoff-v3 session-state system and six standards from `project-standards` (adr, markdown-tooling, cli-documentation, project-spec, python-tooling, python-coding) into this repo, per `TODO.md`'s User Managed section, closing out that TODO list.

**Architecture:** Nine sequential tasks. Task 1 adopts `markdown-frontmatter` narrowly (prerequisite the `adr` standard hard-requires — not itself a TODO item, scoped to `docs/adr/**` only, not repo-wide). Tasks 2–8 each adopt one TODO item. Task 9 closes out `TODO.md`. Standards that ship a packaged CLI installer (`uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' project-standards adopt <name>`) use it instead of hand-transcribing generated files; tasks specify exact merge content only where the CLI prints-but-doesn't-write (pyproject.toml fragments, `.project-standards.yml` blocks) or where no CLI exists (agent-handoff-v3, docs/handoff content, python-coding pointer).

**Tech Stack:** Python 3.14 / uv / Ruff / BasedPyright / pytest+coverage (python-tooling baseline), `project-standards` CLI (`uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' ...`), Claude Code + Codex hook JSON/TOML.

## Global Constraints

- Pin every `project-standards` CLI invocation to `@v4` (the first release carrying `project-spec`; older tags lack it — keep all standards on the same major for consistency).
- Never run `~/projects/agent-handoff-v3/agent-handoff-v3/scripts/handoff/install-globals.sh` — it defaults to a fleet-wide rollout across all of `~/projects/`. Hand-install this repo's handoff files only.
- Use `uv` for all dependency changes (`uv add`, `uv sync`) — never hand-edit `uv.lock`.
- This repo's pseudocode-enforcement hooks (`integrations/agent-hooks/apseudo-hook.py`) block Bash commands whose arguments merely *mention* `.pre-commit-config.yaml` or `.codex/hooks.json`, even for reads — use the `Read` tool for those files, not `cat`/`grep` via Bash, to avoid false-positive blocks.
- Any deliberate deviation from a standard's baseline (e.g. merging python-tooling's CI gate into the existing `apseudo-lint.yml` instead of a separate `check.yml`) gets recorded as an ADR once Task 3 (adr adoption) is complete — do not silently deviate.
- After Task 3, every subsequent task that touches Markdown under `docs/adr/**` follows the frontmatter rules from Task 1; nothing outside `docs/adr/**` gets frontmatter in this plan (repo-wide frontmatter adoption is out of scope — TODO.md does not list `markdown-frontmatter`).
- Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before completing any task that edits `.apseudo`/`.agentpseudo`/`.pseudocode` files or Markdown `apseudo` fences (none of these tasks touch such files directly, but re-check if a task ends up editing `docs/apseudo-docs/**`).
- Commit at the end of each task (single-developer repo, direct commits per global convention) with a message describing which standard/item was adopted.
- **Deferred-enforcement pattern:** when a standard's CI gate would fail immediately against this repo's pre-existing, never-conformant content (markdownlint across ~150 files, project-spec's empty-corpus refusal), adopt the standard's config/local-tooling now but do NOT wire the CI workflow file — record a Task 9 follow-up TODO instead. Do not silently skip adoption steps to dodge this; every deferral in this plan is explicit and tracked.

---

### Task 1: Adopt markdown-frontmatter (prerequisite for adr, scoped narrowly)

**Files:**
- Create: `.project-standards.yml`
- Create: `.github/workflows/validate-standards.yml`

**Interfaces:**
- Produces: `.project-standards.yml` with a `markdown.frontmatter` block that Task 3 (adr) extends with a `markdown.adr` block, and Task 4/6/8 extend with their own top-level blocks (`markdown_tooling`, `spec`, `cli_documentation`).

- [ ] **Step 1: Run the adopt CLI**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt markdown-frontmatter
```

Expected: writes `.project-standards.yml` (only if absent — it is) and `.github/workflows/validate-standards.yml`.

- [ ] **Step 2: Narrow the `include` scope to just `docs/adr/**`**

This repo has ~150+ untouched Markdown files with no frontmatter; enabling `required: true` repo-wide would fail validation on all of them — a full docs-frontmatter migration nobody asked for. TODO.md does not list `markdown-frontmatter` as an item; only `adr` needs it. Edit `.project-standards.yml` to:

```yaml
standards_version: "v3"

markdown:
  frontmatter:
    version: "1.1"
    schema: "markdown-frontmatter"
    required: true
    include:
      - "docs/adr/**/*.md"
    exclude:
      - "**/*.template.md"
      - "CHANGELOG.md"
      - "LICENSE.md"
      - "CLAUDE.md"
      - "AGENTS.md"
      - ".claude/**"
      - ".agents/**"
      - ".codex/**"
      - ".github/**"
      - "node_modules/**"
```

- [ ] **Step 3: Verify the CI workflow content**

`.github/workflows/validate-standards.yml` must read:

```yaml
name: Validate project standards

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    uses: L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v4
    with:
      config-path: ".project-standards.yml"
      standards-ref: "v4"
```

- [ ] **Step 4: Validate locally (expect a clean pass — no files exist under `docs/adr/` yet)**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards validate --config .project-standards.yml
```

Expected: exit 0 (glob matches nothing yet).

- [ ] **Step 5: Commit**

```bash
git add .project-standards.yml .github/workflows/validate-standards.yml
git commit -m "chore: adopt markdown-frontmatter standard (scoped to docs/adr/, prerequisite for ADR standard)"
```

---

### Task 2: Adopt agent-handoff-v3

**Files:**
- Create: `docs/handoff/state.md`, `docs/handoff/deployed.md`, `docs/handoff/architecture.md`, `docs/handoff/credentials.md`, `docs/handoff/conventions.md`, `docs/handoff/specs-plans.md`, `docs/handoff/sessions/2026-07.md`, `docs/handoff/bugs/INDEX.md`, `docs/handoff/bugs/_regen_index.py`
- Create: `STATUS.md`
- Modify: `TODO.md` (rename section headings, preserve all content)
- Create: `.claude/hooks/session_start.py`
- Modify: `.claude/settings.json` (add a second `SessionStart` entry alongside the existing pseudocode-hook entry)
- Modify: `.codex/hooks.json` (add a second `SessionStart` entry, mirroring `.claude/settings.json` — this repo registers Codex hooks via `.codex/hooks.json`, not a `[hooks]` TOML table, so follow that existing convention rather than the canonical `config.toml` example)
- Modify: `AGENTS.md` (add the required top-of-file pointer block)
- Modify: `CLAUDE.md` (repo root — add the required top-of-file pointer block)

**Interfaces:**
- Produces: `docs/handoff/state.md` etc. — consumed by the `session_start.py` hook (reads `docs/handoff/state.md` first, falling back to `docs/state.md`) and by future sessions per the `handoff-system-v3` skill.

- [ ] **Step 1: Copy the canonical hook script**

```bash
mkdir -p .claude/hooks
cp ~/projects/agent-handoff-v3/agent-handoff-v3/global/hooks/session_start.py .claude/hooks/session_start.py
```

- [ ] **Step 2: Add the SessionStart entry to `.claude/settings.json`**

Add a second object to the existing `hooks.SessionStart[0].hooks` array (same `matcher`, alongside the existing `apseudo-hook.py` entry — do not replace it):

```json
{
  "type": "command",
  "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/session_start.py\"",
  "timeout": 10,
  "statusMessage": "Loading handoff state"
}
```

Resulting `hooks.SessionStart` array has one matcher object (`"startup|resume|clear|compact"`) containing two hook entries.

- [ ] **Step 3: Add the SessionStart entry to `.codex/hooks.json`**

Add a second object to the existing `hooks.SessionStart[0].hooks` array (same `matcher`, alongside the existing `apseudo-hook.py --host codex` entry):

```json
{
  "type": "command",
  "command": "bash -c 'python3 \"$(git rev-parse --show-toplevel)/.claude/hooks/session_start.py\"'",
  "timeout": 30,
  "statusMessage": "Loading handoff state"
}
```

The hook script is shared between both harnesses (it detects Codex by the *absence* of `$CLAUDE_PROJECT_DIR`), so only one copy is needed at `.claude/hooks/session_start.py`; Codex's registration just points at the same file, git-root-anchored.

- [ ] **Step 4: Create `docs/handoff/state.md`** (≤2048 bytes; current in-flight work only)

```markdown
**Last updated:** 2026-07-08

## In flight

Adopting agent-handoff-v3 and six project-standards standards per `TODO.md`
(User Managed section), via a single implementation plan at
`docs/superpowers/plans/2026-07-08-adopt-standards.md`. Executing task-by-task.

## Recently landed

- `docs/adr/` created, scoped `markdown-frontmatter` adopted as prerequisite.

## Watch out for

- `.project-standards.yml`'s `markdown.frontmatter.include` is deliberately
  scoped to `docs/adr/**` only — do not widen it to the whole repo without a
  separate decision; this repo has ~150 pre-existing Markdown files with no
  frontmatter.
- `python-tooling` adoption bumps `requires-python` to `>=3.14` and swaps
  `pyright` → `basedpyright`, `hatchling` → `uv_build`.
```

- [ ] **Step 5: Create `docs/handoff/deployed.md`**

```markdown
**Last updated:** 2026-07-08

# Deployed

This repo has no deployment target. It is a local development toolkit
(syntax highlighting, formatter/validator, LSP, MCP server, hooks, skills)
consumed by editors (VS Code, Kate) and agent harnesses (Claude Code, Codex)
directly from a checkout — there is no packaged release, hosted service, or
server component to track here.
```

- [ ] **Step 6: Create `docs/handoff/architecture.md`**

```markdown
**Last updated:** 2026-07-08

# Architecture

## Components

- `src/apseudo_lint/` — the policy source of truth: rules (`rules.py`),
  formatter (`format_cli.py`), linter (`cli.py`), LSP (`lsp.py`), MCP server
  (`mcp.py`), pseudocode runner (`runner_cli.py`), project reviewer
  (`review.py`), template generator (`template_cli.py`), Mermaid renderer
  (`mermaid_cli.py`).
- `integrations/agent-hooks/apseudo-hook.py` — Claude Code + Codex hook
  entry point; calls into `src/apseudo_lint` rather than reimplementing rules.
- `products/vscode-extension/`, `products/kate-integration/` — editor
  integrations; thin wrappers over the LSP/formatter, no duplicated policy.
- `docs/specs/` (being relocated to `docs/reference/` — see Task 6 of the
  2026-07-08 adoption plan) — normative language/format references, not
  project plans.
- `docs/handoff/` — this handoff system (adopted 2026-07-08).

## Standing structural backlog

- `src/apseudo_lint/mcp.py:253` referenced `docs/RULES.md`, which never
  existed (the real file was `docs/specs/RULES.md`) — fixed during the
  docs/specs → docs/reference/ relocation (Task 6).
```

- [ ] **Step 7: Create `docs/handoff/credentials.md`**

```markdown
**Last updated:** 2026-07-08

# Credentials

None. This repo has no external service dependencies, API keys, or deployment
credentials — it is a local toolkit with no network-facing components.
```

- [ ] **Step 8: Create `docs/handoff/conventions.md`**

```markdown
**Last updated:** 2026-07-08

# Conventions

## Quick Reference

| # | Applies when | Rule |
| --- | --- | --- |
| C-001 | Adding a new pseudocode rule | Define it in `src/apseudo_lint/rules.py`; `docs/reference/RULES.md` is generated from it, never hand-edited. |
| C-002 | Editing validator/formatter behavior | The validator and formatter are the policy source of truth — LSP, MCP, hooks, pre-commit, CI, VS Code, and Kate integrations must call or reuse `src/apseudo_lint`, never reimplement rules. |
| C-003 | Adding a CLI entry point | Add it to `[project.scripts]` in `pyproject.toml` and document it per the `cli-documentation` standard (`docs/apseudo-docs/usage/usage.md`). |

## C-001: Rule catalog is generated, not authored

**Applies when:** touching `docs/reference/RULES.md` (formerly `docs/specs/RULES.md`).

**Rule:** Never hand-edit the rule catalog. It states at its own top: "This file is generated from `src/apseudo_lint/rules.py`."

**Why:** it's the shared explanatory layer for the CLI, LSP, MCP server, hooks, and docs — a hand-edit would drift from the actual rule implementations.

**Related:** [[C-002]]

## C-002: Validator/formatter own policy; integrations reuse it

**Applies when:** working in `integrations/agent-hooks/`, `products/vscode-extension/`, `products/kate-integration/`, or the language server.

**Rule:** Call into `src/apseudo_lint`; never duplicate rule logic.

**Why:** stated explicitly in this repo's `CLAUDE.md` under "Tooling architecture."

## C-003: New CLI entry points need standard-compliant docs

**Applies when:** adding a `[project.scripts]` entry.

**Rule:** Follow the `cli-documentation` standard's section registry (`NAME`, `SYNOPSIS`, `DESCRIPTION`, `OPTIONS`, `EXIT STATUS`, `ENVIRONMENT`, `FILES`, `EXAMPLES`, `NOTES`, `SEE ALSO`) in `docs/apseudo-docs/usage/usage.md` or a dedicated per-command page.

**Why:** adopted 2026-07-08 (Task 5 of the adoption plan); `usage.md` and `RUNNER-USAGE.md` already followed this shape independently before adoption.
```

- [ ] **Step 9: Create `docs/handoff/specs-plans.md`**

```markdown
**Last updated:** 2026-07-08

# Specs & Plans

This repo does not use `docs/superpowers/specs/` — plans live under
`docs/superpowers/plans/`; reference specs live under `docs/reference/`
(relocated from `docs/specs/` — see Task 6 of the 2026-07-08 plan below).
Forward-looking project/feature specs adopted under the `project-spec`
standard (Task 6) will live under `docs/specs/` going forward — a fresh,
narrower use of that directory name than the pre-migration reference docs.

| Doc | Kind | Status |
| --- | --- | --- |
| `docs/superpowers/plans/2026-07-08-adopt-standards.md` | Plan | In progress |
| `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md` | Reference (relocated) | Active |
| `docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md` | Reference (relocated) | Active |
| `docs/reference/RULES.md` | Reference (relocated, generated) | Active |
| `docs/reference/language/` | Reference (relocated) | Active |
```

- [ ] **Step 10: Create `docs/handoff/sessions/2026-07.md`**

```markdown
**Last updated:** 2026-07-08

# Sessions — 2026-07

## 2026-07-08

Adopted agent-handoff-v3 and six project-standards standards per TODO.md,
via `docs/superpowers/plans/2026-07-08-adopt-standards.md`.
```

- [ ] **Step 11: Copy the bugs index helper and create an empty index**

```bash
mkdir -p docs/handoff/bugs
cp ~/projects/agent-handoff-v3/docs/handoff/bugs/_regen_index.py docs/handoff/bugs/_regen_index.py
python3 docs/handoff/bugs/_regen_index.py
```

Expected: generates `docs/handoff/bugs/INDEX.md` (empty — no bug records yet).

- [ ] **Step 12: Create `STATUS.md`**

```markdown
# Project Status

## Completed

- Pythonic Agent Pseudocode toolkit: syntax highlighting, formatter, validator, LSP, MCP server, hooks, skills, CI.

## Current State

- Local development toolkit, no deployment target. Repo migrated to `agent-handoff-v3` session-state layout and `project-standards` (adr, markdown-tooling, cli-documentation, project-spec, python-tooling) on 2026-07-08.

## Recent Changes

- [2026-07-08] Adopted agent-handoff-v3 and six project-standards standards.

## Notes For The Builder

- `docs/specs/` was relocated to `docs/reference/`; the `project-spec` standard now governs a fresh, forward-looking use of `docs/specs/` for project/feature plans only.
```

- [ ] **Step 13: Rename `TODO.md` section headings, preserving content**

Change `## User Managed` → `## User Tracked Tasks` and `## Agent Managed` → `## Agent Tracked Tasks` (exact headings the handoff spec's validator checks). Keep all existing bullets and the HTML instructions comment as-is.

- [ ] **Step 14: Add the pointer block to `AGENTS.md`**

Insert at the top of `AGENTS.md`, before `## Repository purpose`:

```markdown
**Session state:** read `docs/handoff/state.md` first — live state and active work.
**Full conventions reference:** `docs/handoff/conventions.md`.
**Detailed review workflows:** not configured for this repo.
```

- [ ] **Step 15: Add the pointer block to `CLAUDE.md`**

Insert at the top of `/home/chris/projects/agent-pseudocode/CLAUDE.md`, before `## Repository purpose`:

```markdown
**Session state:** read `docs/handoff/state.md` first — live state and active incidents.
```

- [ ] **Step 16: Validate the layout**

```bash
bash ~/projects/agent-handoff-v3/agent-handoff-v3/scripts/handoff/validate-layout.sh /home/chris/projects/agent-pseudocode
```

Expected: exit 0, no missing-file or heading-mismatch errors.

- [ ] **Step 17: Commit**

```bash
git add docs/handoff STATUS.md TODO.md .claude/hooks/session_start.py .claude/settings.json .codex/hooks.json AGENTS.md CLAUDE.md
git commit -m "feat: adopt agent-handoff-v3 session-state system"
```

---

### Task 3: Adopt the `adr` standard

**Files:**
- Create: `docs/adr/README.md` (index)
- Create: `docs/adr/adr.template.md`
- Create: `docs/adr/adr-0001-*.md` (first ADR — see Step 4)
- Modify: `.project-standards.yml` (add `markdown.adr` block)
- Modify: `/home/chris/projects/agent-pseudocode/CLAUDE.md` (add docs-table pointer row)

**Interfaces:**
- Consumes: `.project-standards.yml`'s `markdown.frontmatter` block from Task 1 (scoped to `docs/adr/**`).

- [ ] **Step 1: Run the adopt CLI**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt adr
```

Expected: writes `docs/decisions/adr.template.md` and prints the `.project-standards.yml` fragment. Since this repo uses `docs/adr/`, not the default `docs/decisions/`, move the generated template:

```bash
mkdir -p docs/adr
mv docs/decisions/adr.template.md docs/adr/adr.template.md
rmdir docs/decisions 2>/dev/null || true
```

- [ ] **Step 2: Merge the printed fragment into `.project-standards.yml`**

Add under the existing `markdown:` key:

```yaml
markdown:
  frontmatter:
    # ...unchanged from Task 1...
  adr:
    require_sections: false
```

Add `"**/*.template.md"` to the existing `exclude` list under `markdown.frontmatter` (already present from Task 1's starter — verify it's there).

- [ ] **Step 3: Create the ADR index**

`docs/adr/README.md`:

```markdown
---
schema_version: '1.1'
id: 'index-a1b2c3-adr'
title: 'Architecture Decision Records'
description: 'Index of ADRs for the agent-pseudocode repository.'
doc_type: 'index'
status: 'active'
created: '2026-07-08'
updated: '2026-07-08'
tags:
  - 'adr'
  - 'index'
aliases: []
related: []
---

# Architecture Decision Records

| Number | Title | Status |
| --- | --- | --- |
| [0001](adr-0001-relocate-language-reference-docs.md) | Relocate normative language reference docs out of docs/specs | Accepted |
```

(Generate the 6-character base-36 `id` token for real rather than the placeholder `a1b2c3` shown above — any lowercase `[0-9a-z]` sequence works; the validator only checks shape, not a specific value.)

- [ ] **Step 4: Author the first real ADR, recording the docs/specs relocation decision**

Use `docs/adr/adr.template.md` (the `adr-minimal.md` variant) as the starting point. Save as `docs/adr/adr-0001-relocate-language-reference-docs.md`, `id: 'adr-0001-agent-pseudocode-relocate-language-reference-docs'`, `doc_type: 'adr'`, documenting: existing `docs/specs/*.md` files (the pseudocode language standard, executable spec, generated rule catalog, token reference) are normative/reference material, not project plans — they don't fit the `project-spec` standard's scope, so they're relocated to `docs/reference/` (matching the existing `docs/reference/` taxonomy) and `docs/specs/` is freed up for the `project-spec` standard's forward-looking use (Task 6).

- [ ] **Step 5: Add a CLAUDE.md pointer**

Add a row to the docs table in `/home/chris/projects/agent-pseudocode/CLAUDE.md` (create a small table if none exists, next to the "Tooling architecture" section) pointing at `docs/adr/README.md` for architecture decisions.

- [ ] **Step 6: Validate**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards validate --config .project-standards.yml
```

Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add docs/adr .project-standards.yml CLAUDE.md
git commit -m "feat: adopt adr standard, record docs/specs relocation as ADR-0001"
```

---

### Task 4: Adopt the `markdown-tooling` standard

**Files:**
- Create: `.markdownlint.json`, `.prettierrc.json`, `.markdownlint-cli2.jsonc`, `package.json`
- Modify: `.editorconfig` (add `[*.md]` deviation)
- Modify: `.vscode/settings.json`, `.vscode/extensions.json` (created fresh — no `.vscode/` exists yet)
- Modify: `.project-standards.yml` (optional `markdown_tooling.version` pin)
- Modify: `AGENTS.md` (append §12 agent-instruction block)

- [ ] **Step 1: Run the adopt CLI**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards adopt markdown-tooling
```

Expected: writes `.markdownlint.json`, `.prettierrc.json`, `.vscode/extensions.json`, `lint-markdown.yml` and `format.yml` workflow callers. Merges `.editorconfig`'s `[*.md]` block only if the CLI supports append-to-existing (verify with `git diff .editorconfig`); if it skipped `.editorconfig` because the file already exists, manually add:

```ini
[*.md]
trim_trailing_whitespace = false
```

- [ ] **Step 2: Create a minimal root `package.json` for the Prettier devDependency pin**

No root `package.json` exists (this is a pure-Python + VS Code-extension-in-subdir project). Create:

```json
{
  "name": "agent-pseudocode-syntax-toolkit",
  "private": true,
  "devDependencies": {
    "prettier": "3.8.3"
  }
}
```

```bash
npm install
```

- [ ] **Step 3: Defer the format gate — this repo has never been Prettier-formatted**

In the generated `.github/workflows/format.yml` caller, set `prettier: false` so the job skips cleanly rather than failing on unformatted files. Add a follow-up TODO item (Task 9) to run `npx prettier@3.8.3 --write .` and flip this on in a later session — doing so now would touch ~150 files outside this plan's scope.

- [ ] **Step 4: Do NOT wire the lint-markdown CI job yet**

The adopt CLI may write a `lint-markdown.yml` (or `.caller.yml`) workflow file. This repo has ~150 pre-existing Markdown files that have never been linted (see Step 7) — wiring this as an active CI job now would make the gate red immediately. If the CLI wrote the workflow file, **delete it** (or move it to a non-`.github/workflows/` path, e.g. `.github/workflows-pending/lint-markdown.yml`, so it's tracked but not live):

```bash
rm -f .github/workflows/lint-markdown.yml .github/workflows/lint-markdown.caller.yml
```

Wiring it is deferred to the full-repo markdownlint cleanup task recorded in Task 9.

- [ ] **Step 5: Add `.markdownlint-cli2.jsonc` for local parity**

```jsonc
{
  "config": ".markdownlint.json",
  "globs": ["**/*.md"],
  "ignores": ["node_modules/**", ".venv/**"],
}
```

- [ ] **Step 6: Append the agent-instruction block to `AGENTS.md`**

Append the markdown-tooling standard's §12 block (fetch verbatim via `uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' project-standards adopt markdown-tooling --force --dry-run` if the CLI supports printing it, otherwise transcribe from `standards/markdown-tooling/README.md` §12 on `origin/main`) to `AGENTS.md`, after the existing Pythonic Agent Pseudocode block.

- [ ] **Step 7: Run markdownlint locally**

```bash
npx markdownlint-cli2 "**/*.md" "#node_modules"
```

Expected: this WILL surface pre-existing violations across ~150 files (this repo has never been linted). Do not attempt to fix all of them in this task — that's a separate cleanup effort. Record the finding in `docs/handoff/state.md`'s "Watch out for" section instead of blocking this task on a full-repo cleanup.

- [ ] **Step 8: Commit**

```bash
git add .markdownlint.json .prettierrc.json .markdownlint-cli2.jsonc .editorconfig .vscode package.json package-lock.json .github/workflows/format.yml .project-standards.yml AGENTS.md
git commit -m "feat: adopt markdown-tooling standard (rules seeded, lint+format CI deferred pending full-repo cleanup)"
```

---

### Task 5: Adopt the `cli-documentation` standard

**Files:**
- Modify: `docs/apseudo-docs/usage/usage.md` (already standard-shaped — close the gap, not a rewrite)
- Create: `.github/workflows/cli-docs-check.yml`
- Modify: `.project-standards.yml` (add `cli_documentation` block)

**Interfaces:**
- Consumes: the existing `NAME → SYNOPSIS → DESCRIPTION → OPTIONS → EXIT STATUS → ENVIRONMENT → FILES → EXAMPLES → NOTES → SEE ALSO` section registry already used in `usage.md` and `RUNNER-USAGE.md` — this task extends it, not replaces it.

- [ ] **Step 1: Record the profile decision at the top of `usage.md`**

This repo is **Packaged** (installed via `[project.scripts]`), tailored to stay Packaged (not Packaged-deep) despite the unified `apseudo` dispatcher's 9 subcommands, since nesting alone never forces the deep tier — record this explicitly:

```markdown
> **CLI documentation profile:** Packaged (per the `cli-documentation` standard).
> The unified `apseudo` dispatcher exposes 9 subcommands, which exceeds the
> "~5-7 top-level subcommands" Packaged-deep signal on count alone, but the
> standard is explicit that nesting/count alone never forces the deep tier —
> this repo stays Packaged as a deliberate tailoring.
```

- [ ] **Step 2: Add standalone entries for the four bare `[project.scripts]` keys that lack them**

`apseudo-lint`, `apseudo-format`, `apseudo-lsp`, `apseudo-explain` are separate `[project.scripts]` entries but currently only documented via the `apseudo <subcommand>` form. Add a short cross-reference section to `usage.md` for each, e.g.:

```markdown
## apseudo-lint (standalone entry point)

`apseudo-lint` is a standalone console-script alias for `apseudo lint` — see
the `apseudo lint` entry above for the full `NAME`/`SYNOPSIS`/`OPTIONS`/`EXIT
STATUS` contract, which applies identically to the standalone invocation.
```

Repeat for `apseudo-format` → `apseudo format`, `apseudo-lsp`, `apseudo-explain` (the latter two have no `apseudo <subcommand>` equivalent per the 9-subcommand list — verify and give them full standalone `NAME`/`SYNOPSIS`/`OPTIONS`/`EXIT STATUS` entries if so, not just cross-references).

- [ ] **Step 3: State the `apseudo-run` / `apseudo run` relationship**

In `RUNNER-USAGE.md`, add a note stating whether `apseudo-run` is the same entry point as `apseudo run` or a distinct standalone script, mirroring project-standards' own "unified front end vs. standalone scripts" pattern.

- [ ] **Step 4: Add the CI smoke-test workflow**

Create `.github/workflows/cli-docs-check.yml` from `standards/cli-documentation/templates/cli-docs-check.yml` (fetch via `git -C ~/projects/project-standards show origin/main:standards/cli-documentation/templates/cli-docs-check.yml`), with `env.TOOL: apseudo` and `NO_COLOR: "1"` kept as-is.

- [ ] **Step 5: Add the `.project-standards.yml` fragment**

```yaml
cli_documentation:
  version: "1.0"
```

- [ ] **Step 6: Commit**

```bash
git add docs/apseudo-docs/usage/usage.md docs/apseudo-docs/usage/RUNNER-USAGE.md .github/workflows/cli-docs-check.yml .project-standards.yml
git commit -m "feat: adopt cli-documentation standard, close standalone-entry-point gaps"
```

---

### Task 6: Adopt the `project-spec` standard + relocate `docs/specs/` → `docs/reference/`

**Files:**
- Move: `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md` → `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`
- Move: `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md` → `docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md`
- Move: `docs/specs/RULES.md` → `docs/reference/RULES.md`
- Move: `docs/specs/language/` → `docs/reference/language/`
- Modify: `src/apseudo_lint/review.py` (3 path references)
- Modify: `src/apseudo_lint/mcp.py:253` (fixes a pre-existing broken path — was `docs/RULES.md`, which never existed)
- Modify: 17 files referencing `docs/specs` (see Step 3 for the full list)
- Modify: `.project-standards.yml` (add `spec:` block, pointed at the now-empty `docs/specs/`)

**Interfaces:**
- Consumes: ADR-0001 from Task 3, which documents the rationale for this move.

- [ ] **Step 1: Move the files**

```bash
git mv docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md
git mv docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md
git mv docs/specs/RULES.md docs/reference/RULES.md
git mv docs/specs/language docs/reference/language
```

- [ ] **Step 2: Fix the two code references**

`src/apseudo_lint/review.py` lines 94, 95, 112 — replace `docs/specs/` with `docs/reference/` in the three `_check_file(...)` calls.

`src/apseudo_lint/mcp.py:253` — replace:

```python
"apseudo://rules": self.root / "docs" / "RULES.md",
```

with:

```python
"apseudo://rules": self.root / "docs" / "reference" / "RULES.md",
```

(This was a pre-existing broken path — `docs/RULES.md` never existed — fixed as part of this move, not a separate task.)

- [ ] **Step 3: Fix all Markdown references**

Update every `docs/specs/...` reference to `docs/reference/...` in: `CLAUDE.md`, `CHANGELOG.md`, `README.md`, `TODO.md`, `.agents/skills/agent-pseudocode/SKILL.md`, `.claude/skills/agent-pseudocode/SKILL.md`, `docs/README.md`, `docs/reviews/FEATURE-GAP-ANALYSIS.md`, `docs/reviews/PROJECT-REVIEW-RESULT.md`, `docs/reviews/PROJECT-TRACEABILITY-REVIEW.md`, `docs/reference/pre-migration/apseudo-chatgpt-conversation.md`, `docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md`, `docs/apseudo-docs/usage/RUNNER-USAGE.md`, `docs/apseudo-docs/usage/usage.md`, `docs/apseudo-docs/usage/use-cases/README.md`, `docs/apseudo-docs/usage/use-cases/CHOOSING-A-SURFACE.md`, `docs/apseudo-docs/usage/use-cases/COMMON-WORKFLOWS.md`, `docs/apseudo-docs/usage/use-cases/RUNNER-WORKFLOWS.md`, `docs/apseudo-docs/usage/use-cases/EXAMPLE-CATALOG.md`.

`CHANGELOG.md` is a historical record — update only links that would 404, not past-tense narrative text describing what happened at the time.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rln "docs/specs" --include="*.py" --include="*.md" --include="*.toml" --include="*.json" --include="*.yml" --include="*.yaml" . | grep -v node_modules
```

Expected: empty output, except any files that legitimately describe the *new* `docs/specs/` usage under project-spec (Step 6 onward).

- [ ] **Step 5: Run the project reviewer to confirm the moved-file checks still pass**

```bash
uv run apseudo-review .
```

Expected: clean (the three `_check_file` calls in `review.py` now point at `docs/reference/`).

- [ ] **Step 6: Add the `spec:` block to `.project-standards.yml`**

```yaml
spec:
  include:
    - 'docs/specs/**/*.md'
  exclude: []
```

`docs/specs/` is now empty and free for forward-looking project/feature specs authored via the CLI.

- [ ] **Step 7: Do NOT wire the validate-specs CI workflow yet**

`project-spec`'s own `adopt.md` states an empty corpus is "refused, not silently passed" — `docs/specs/` has zero files immediately after this relocation (nothing has been authored under the `project-spec` standard yet), so `spec validate` would fail, not vacuously pass. Wiring `.github/workflows/validate-specs.yml` now would make CI red for no real reason. Skip creating that workflow file in this task; add it once the first real spec is authored (tracked as a Task 9 follow-up).

- [ ] **Step 8: Confirm the CLI's behavior against the empty corpus locally (informational, not a gate)**

```bash
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  project-standards spec validate --config .project-standards.yml
```

Expected: nonzero exit (empty corpus refused) — this confirms the reasoning above, not a task failure. Do not treat this as a blocking check for this task.

- [ ] **Step 9: Commit**

```bash
git add docs/reference docs/specs src/apseudo_lint/review.py src/apseudo_lint/mcp.py CLAUDE.md CHANGELOG.md README.md TODO.md .agents .claude docs .project-standards.yml
git commit -m "feat: adopt project-spec standard (config only, CI deferred until first spec); relocate normative reference docs from docs/specs/ to docs/reference/ per ADR-0001"
```

---

### Task 7: Adopt the `python-tooling` standard

**Files:**
- Modify: `pyproject.toml`
- Create: `.python-version`
- Modify: `.github/workflows/apseudo-lint.yml` (update in place — see rationale below, not a new `check.yml`)
- Modify: `.vscode/settings.json` (merge Python blocks alongside markdown-tooling's, from Task 4)
- Create: `docs/adr/adr-0002-merge-python-tooling-ci-into-apseudo-lint.md`

**Interfaces:**
- Consumes: `docs/adr/adr.template.md` from Task 3.

- [ ] **Step 1: Update `pyproject.toml`'s `[project]` table**

```toml
requires-python = ">=3.14"
```

Update `classifiers` to add `"Programming Language :: Python :: 3.14"` and drop `3.11`/`3.12`/`3.13` if this repo intends to actually stop supporting them (it does — this is an internal toolkit, per the earlier scope decision).

- [ ] **Step 2: Replace `[project.optional-dependencies].dev` with `[dependency-groups].dev`**

```toml
[dependency-groups]
dev = [
    "basedpyright",
    "coverage[toml]",
    "pip-audit",
    "pytest>=9.0",
    "ruff>=0.14",
]
```

Remove `pre-commit` from this group — it stays in `.pre-commit-config.yaml` for the non-Python `apseudo-format`/`apseudo-lint`/`apseudo-review` hooks only (explicitly sanctioned by the standard's non-default-tools scope note), not as a duplicate Python gate.

- [ ] **Step 3: Replace `[build-system]`**

```toml
[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"
```

Read `standards/python-tooling/build-backend.md` (via `git -C ~/projects/project-standards show origin/main:standards/python-tooling/build-backend.md`) for the `[tool.hatch.build.targets.wheel]` → `uv_build` package-discovery equivalent, since this repo currently declares `packages = ["src/apseudo_lint"]` under hatchling.

- [ ] **Step 4: Replace `[tool.ruff]` / `[tool.ruff.lint]`, add `[tool.ruff.format]`**

```toml
[tool.ruff]
target-version = "py314"
line-length = 100
src = ["src", "tests", "integrations/agent-hooks"]
extend-exclude = [".claude", ".agents", ".codex", ".continue"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "C4", "PIE", "PTH", "RET", "RUF"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

- [ ] **Step 5: Replace `[tool.pyright]` with `[tool.basedpyright]`**

```toml
[tool.basedpyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.14"
pythonPlatform = "All"
failOnWarnings = true
```

- [ ] **Step 6: Extend `[tool.pytest.ini_options]`, add coverage tables**

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
minversion = "9.0"
addopts = ["-ra", "--strict-markers", "--strict-config"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 85
```

- [ ] **Step 7: Sync dependencies**

```bash
uv python pin 3.14
uv sync --extra dev
```

Expected: `.python-version` created with `3.14`; `uv.lock` updated.

- [ ] **Step 8: Author ADR-0002 recording the CI-merge deviation**

`python-tooling` §19.2/§21 expects a dedicated `.github/workflows/check.yml`. This repo already runs an equivalent gate (`pytest`, ruff, pyright/basedpyright, plus pseudocode-specific checks) in one consolidated `apseudo-lint.yml`. Record in `docs/adr/adr-0002-merge-python-tooling-ci-into-apseudo-lint.md` (using `docs/adr/adr.template.md`) that this repo updates the existing workflow's Python steps in place rather than adding a second, overlapping CI job — an explicit exception per the standard's §20 exceptions process.

- [ ] **Step 9: Update `.github/workflows/apseudo-lint.yml` in place**

- `Set up Python` step: `python-version: "3.13"` → `"3.14"`.
- `Run pyright strict type check` step: `uv run pyright` → `uv run basedpyright`.
- Add a new step after `Run unit tests`: `uv run coverage run -m pytest && uv run coverage report`.
- Add a new step: `uv run pip-audit`.

- [ ] **Step 10: Run the full check gate locally**

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests integrations/agent-hooks
uv run basedpyright
uv run coverage run -m pytest && uv run coverage report
uv run pip-audit
```

Expected: all pass, or surface and fix any real findings (do not suppress).

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml .python-version uv.lock .github/workflows/apseudo-lint.yml docs/adr/adr-0002-merge-python-tooling-ci-into-apseudo-lint.md .vscode
git commit -m "feat: adopt python-tooling standard (py3.14, uv_build, basedpyright, coverage, pip-audit)"
```

---

### Task 8: Document the `python-coding` standard (reference-only, no adopt CLI)

**Files:**
- Modify: `/home/chris/projects/agent-pseudocode/CLAUDE.md`

**Interfaces:**
- Consumes: nothing generated by prior tasks — this is a documentation-only pointer, since `python-coding` has no `adopt.md`, is not registered for adoption or validation, and is explicitly "reference-only" per its own §31.

- [ ] **Step 1: Add a one-line pointer to `CLAUDE.md`**

Under the existing "## Development commands" or a new short section, add:

```markdown
## Python code style

Python code in this repository follows the `python-coding` standard
(project-standards) — code shape, type policy, error handling, and testing
conventions. Use the `python-expert` skill as the front door to both
`python-coding` and `python-tooling`; canon (the standards themselves) wins on
any conflict.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: point CLAUDE.md at the python-coding standard via the python-expert skill"
```

---

### Task 9: Close out `TODO.md`

**Files:**
- Modify: `TODO.md`

- [ ] **Step 1: Check off every completed User Tracked Task**

Mark `[x]` for: adopt agent-handoff-v3, adr, markdown-tooling, cli-documentation, project-spec, python-tooling, python-coding. For the ingest/migrate-specs item, replace its text to reflect the actual outcome (relocated to `docs/reference/`, `project-spec` adopted for future specs — not a literal migration, per ADR-0001) and check it off.

- [ ] **Step 2: Add completion notes for the three deferred enforcement gates**

Add three new `## Agent Tracked Tasks` entries:

- `- [ ] Run \`npx prettier@3.8.3 --write .\` across the repo and flip \`format.yml\`'s \`prettier: false\` to enabled (deferred from markdown-tooling adoption, 2026-07-08 — touches ~150 files, out of scope for the adoption plan).`
- `- [ ] Fix markdownlint violations across the repo (\`npx markdownlint-cli2 "**/*.md" "#node_modules"\`) and add \`.github/workflows/lint-markdown.yml\` (deferred from markdown-tooling adoption, 2026-07-08 — CI would go red immediately otherwise; ~150 files never linted before).`
- `- [ ] Author the first project-spec-conformant spec under \`docs/specs/\` and add \`.github/workflows/validate-specs.yml\` (deferred from project-spec adoption, 2026-07-08 — the standard refuses an empty corpus rather than passing vacuously, so wiring CI before any spec exists would fail every run).`

- [ ] **Step 3: Update `docs/handoff/state.md` to close out the "In flight" section**

Replace the "In flight" note with "Standards adoption complete (2026-07-08) — see `docs/handoff/sessions/2026-07.md`." and move the finished-work bullets to "Recently landed."

- [ ] **Step 4: Commit**

```bash
git add TODO.md docs/handoff/state.md
git commit -m "chore: close out standards-adoption TODO items"
```

---

## Self-Review Notes

- **Spec coverage:** all 8 TODO items covered (Tasks 2–8 map 1:1 to the 7 listed standards + handoff system; the specs-migration item is covered by Task 6 with the ADR-recorded scope adjustment the user approved).
- **markdown-frontmatter scope:** deliberately narrow (Task 1) per the user's explicit approval — not a full repo-wide adoption.
- **Python floor bump, docs relocation, and CI-merge deviation** are each backed by an explicit prior user decision (floor bump, relocation) or an ADR (CI merge) — none are silent.
- **No placeholders:** every step names exact files, exact commands, or exact code/config content; where a step depends on CLI-generated output not fully known ahead of time (e.g. markdown-tooling's exact `.markdownlint.json` deviations), the step specifies running the canonical CLI rather than hand-guessing content, plus a concrete verification command.
