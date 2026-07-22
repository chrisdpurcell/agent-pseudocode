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

- [ ] Complete full-repo Markdown cleanup so the enabled lint gate passes, then turn on the Prettier gate.

  `lint-markdown.yml` is live and currently red on 272 markdownlint errors. Run the pinned formatter/linter fix pass and review the diff. `format.yml` is installed `workflow_dispatch`-only; enable it by setting `format = true` and `ci.format_caller = true` under `[standards.markdown-tooling]` in `.standards/config.toml`, then `project-standards reconcile --apply`.

- [ ] Raise coverage from 60% to the Python Tooling 85% floor, then make the CI coverage step blocking.

  Prioritize untested CLI, output, discovery, Mermaid, LSP, and MCP paths documented by the adoption audit.

- [ ] Author the first project-spec-conformant spec under `docs/specs/`.

  `validate-specs.yml` is already live and red: `project-standards spec validate` exits 2 on an empty corpus (upstream #17).

- [ ] Author `docs/usage.md` for the `apseudo` CLI.

  The cli-documentation package created it as a scaffold with literal `toolname` placeholders. It is consumer-owned and create-only, so edits survive reconciliation.

- [ ] Fix the three remaining pre-existing bugs in `docs/handoff/bugs/`.

  - [bug 001](handoff/bugs/001-mcp-resource-map-stale-paths.md): stale MCP resource paths.
  - [bug 002](handoff/bugs/002-review-completeness-stale-paths.md): stale completeness-check paths.
  - [bug 004](handoff/bugs/004-lsp-serve-unhandled-read-message.md): unguarded LSP message reads.

- [ ] Consider adopting the `python-tooling` package, which V5 leaves disabled.

  It was never in the V4 config, so migration did not select it. Enabling it rewrites `pyproject.toml`'s `[build-system]` and adds a managed `check.yml` plus `scripts/check.py`; upstream #14 documents keys it can drop. Preview with `reconcile` before applying.
