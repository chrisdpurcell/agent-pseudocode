# Project Tasks

<!--
Purpose:
- This document is used to track tasks that need to be completed. It is intended to be a user-facing document that provides transparency about what the agent is working on and what tasks are still pending.

Instructions for AI agents:
- Do not add tasks to the `## User tasks` section.
- Do add tasks to the `## Agent tasks` section. Include all open work from agent-managed handoff documents.
- Use `- [ ]` to indicate an open task and mark `- [x]` upon completion.
- For partially completed tasks, append a brief log of what is done and what remains.
- Remove completed standalone agent tasks after recording their outcomes in `docs/STATUS.md`.
-->

## User tasks

- [ ] Setup GitHub repository settings; see `/home/chris/Downloads/public-repo-settings.md`
- [ ] Create specification documents from the existing project state. See `docs/reference`.
  - Some reverse-engineering may be required.
  - It is important to capture the current state of the project in a specification
    document to ensure that future development aligns with the intended design and functionality.

    It also provides a baseline for future reference and helps maintain consistency in the project's evolution.
  - Create multiple specification documents if necessary to cover different aspects of the project.

    Size/scope them appropriately to ensure clarity and comprehensiveness.
  - Ensure the specs comply with the project-spec standard.
- [ ] Correct naming of markdown files in `docs/` (except README.md) to use lower kebab-case.

  Ensure all links and references are updated accordingly.
- [ ] Ensure all markdown files lint and format correctly and do not break.
- [x] Create this repo's custom conventions for markdown-frontmatter.
  - [x] Codify as a proper ADR. Accepted as `docs/adr/adr-0003-markdown-frontmatter-scope-and-conventions.md` on 2026-07-09.
  - [x] Fix all existing covered markdown files to comply with the new conventions.
    - Try to script this as much as possible to save tokens and time.
- [ ] Verify all python files lint and format correctly and do not break.
- [ ] Review .gitignore, ensure it makes sense and entries are reasonable, and reorganize/reorder for clarity.

## Agent tasks

- [ ] Complete full-repo Markdown cleanup, then restore lint CI and enable the reusable Prettier gate.

  The adoption audit found 489 pre-existing violations across 33 files. Run the pinned formatter/linter fix pass, review the diff, restore `lint-markdown.yml`, and enable `.github/workflows/format.yml`.

- [ ] Raise coverage from 60% to the Python Tooling 85% floor, then make the CI coverage step blocking.

  Prioritize untested CLI, output, discovery, Mermaid, LSP, and MCP paths documented by the adoption audit.

- [ ] Author the first project-spec-conformant spec under `docs/specs/`, then add `validate-specs.yml`.

- [ ] Fix the three remaining pre-existing bugs in `docs/handoff/bugs/`.

  - [bug 001](handoff/bugs/001-mcp-resource-map-stale-paths.md): stale MCP resource paths.
  - [bug 002](handoff/bugs/002-review-completeness-stale-paths.md): stale completeness-check paths.
  - [bug 004](handoff/bugs/004-lsp-serve-unhandled-read-message.md): unguarded LSP message reads.

- [ ] Decide and execute the project-standards V4→V5 migration (tool-ready on release 5.2.0; prior blockers #8/#9/#10 fixed upstream).

  Assessed 2026-07-20: read-only preview reconciles 31 targets but is `applicable: false` on three deliberately-customized files. Resolve before applying: (a) align `.editorconfig` `[*] indent_style` `space`→`tab` (matches the repo's own tab-emitting Prettier; bounded takeover keeps the apseudo 4-space glob); (b) preserve the hardened `format.yml` and `cli-docs-check.yml` — blocked on upstream relinquishment (#12, #13), or accept restoring package bytes and re-applying hardening after; (c) sequence the deferred lint/Prettier/spec CI gates the plan would create. Then `init --catalog 5 --migrate --apply`. Not urgent — V5 keeps a read-only V4 fallback until V6.
