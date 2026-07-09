---
schema_version: '1.1'
id: 'adr-0001-agent-pseudocode-relocate-language-reference-docs'
title: 'ADR 0001: Relocate normative language reference docs out of docs/specs'
description: 'Decision to keep normative language references in docs/reference instead of docs/specs.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags:
  - 'adr'
  - 'docs'
  - 'standards-adoption'
aliases:
  - 'ADR 0001'
  - 'Language reference relocation'
related:
  - 'docs/reference/README.md'
supersedes: []
superseded_by: null
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---

# Relocate normative language reference docs out of docs/specs

## Context and Problem Statement

This repository is mid-way through a plan to adopt several `project-standards` standards (markdown-frontmatter, agent-handoff-v3, adr, python-coding/python-tooling, and — in a later task — `project-spec`). The `project-spec` standard treats `docs/specs/` as the home for forward-looking, project-scoped specs: documents that describe planned or in-progress work for _this_ repository (e.g. a design for a new feature, a state-machine spec for a script).

`docs/specs/` currently holds a different kind of content: `PYTHONIC_PSEUDOCODE_STANDARD.md` (the Pythonic Agent Pseudocode language standard), `EXECUTABLE-PSEUDOCODE-SPEC.md` (the executable `.apseudo` runner spec), `RULES.md` (the APSEUDO-\* rule catalog, generated from `src/apseudo_lint/rules.py`), and `docs/specs/language/` (`TOKEN-SPEC.md`, `SCOPE-MAP.md`, `README.md`, and `examples/`). These are normative reference material this repository _implements and ships_ — they define the pseudocode convention itself, not a plan for building something. They are durable, versioned artifacts consumed by the formatter, linter, language server, MCP server, and this repo's own `CLAUDE.md` ("Follow `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md`"), not project-planning documents that get superseded once the described work ships.

Adopting `project-spec` on top of the current `docs/specs/` layout would conflate two unrelated meanings of "spec" in one directory: the language/DSL reference the tooling implements, and forward-looking task/feature specs the `project-spec` standard is designed to manage. Where should the normative language reference material live so that `docs/specs/` can be handed cleanly to the `project-spec` standard?

## Decision Drivers

- `project-spec`'s scope is project plans, not durable normative references — forcing the reference docs to conform to its structure would misrepresent their nature and churn stable content for no benefit.
- The repository already has a `docs/reference/` directory (with `SOURCES.md` and `pre-migration/`) established as the home for durable, non-plan reference material — reusing that taxonomy avoids inventing a second reference location.
- Tooling and `CLAUDE.md` hard-require these files by path (e.g. `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md`); the relocation must be a deliberate, tracked task (Task 6) with those references updated, not an incidental side effect of adopting `project-spec`.

## Considered Options

- Leave the language reference docs in `docs/specs/` and adopt `project-spec` alongside them.
- Relocate the normative language reference docs to `docs/reference/`, freeing `docs/specs/` for `project-spec`.
- Give the language reference docs a new top-level directory (e.g. `docs/language/`) instead of folding them into `docs/reference/`.

## Decision Outcome

Chosen option: "Relocate the normative language reference docs to `docs/reference/`", because it reuses this repository's existing reference taxonomy instead of adding a fourth kind of docs directory, and it cleanly separates "what the pseudocode language is" (reference) from "what we plan to build" (spec) — the exact distinction `project-spec` assumes when it takes over `docs/specs/`.

This decision is recorded now, ahead of execution. The actual move — `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md`, `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md`, `docs/specs/RULES.md`, and `docs/specs/language/` to their `docs/reference/` equivalents, plus every path reference in `CLAUDE.md`, tooling, and docs that points at the old locations — is Task 6 of the standards-adoption plan, not this task.

### Consequences

- Good, because `docs/specs/` becomes available for `project-spec` without ambiguity about what belongs there.
- Good, because `docs/reference/` gains a coherent, single home for all durable non-plan reference material in this repo.
- Bad, because every hard-coded path reference to the old `docs/specs/*.md` locations (in `CLAUDE.md`, the formatter/linter/language-server/MCP code, hooks, and any other docs) must be found and updated in Task 6, or those integrations will point at stale paths.

### Confirmation

Task 6 is complete, and this decision is confirmed, when: `docs/specs/` contains only forward-looking project-spec documents (or is empty pending its first one), the former language-standard files exist under `docs/reference/` at their new paths, `apseudo-lint`/`apseudo-format`/CI pass with the updated paths, and no remaining reference in `CLAUDE.md` or tooling points at the old `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md`-style locations.

## Pros and Cons of the Options

### Leave the language reference docs in docs/specs/

- Good, because it requires no file moves right now.
- Neutral, because it defers the naming conflict rather than resolving it.
- Bad, because it directly conflicts with `project-spec`'s intended scope for `docs/specs/`, conflating durable language reference material with forward-looking project plans in the same directory.

### Relocate to docs/reference/

- Good, because `docs/reference/` already exists in this repo for exactly this kind of durable, non-plan material.
- Good, because it gives `project-spec` an unambiguous, empty-of-conflicting-content directory to adopt.
- Bad, because it requires a coordinated, multi-file path-reference update (Task 6).

### New docs/language/ directory

- Good, because it would give the pseudocode language its own clearly-named home.
- Bad, because it introduces a fourth top-level docs taxonomy entry alongside `docs/reference/`, `docs/adr/`, and `docs/handoff/` for content that already fits the existing `docs/reference/` definition — unnecessary proliferation.

## More Information

This ADR is authored as part of Task 3 (adopting the `adr` standard) in this repository's 9-task standards-adoption plan. The decision it records is executed by Task 6 (relocating `docs/specs/*.md` to `docs/reference/*.md`), which comes later in the same plan. See `docs/adr/README.md` for the ADR index.
