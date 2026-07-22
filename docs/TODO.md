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

- [ ] Raise coverage from 62% to the Python Tooling 85% floor.

  The `check.yml` gate installed by python-tooling enforces `fail_under = 85`, so `scripts/check.py` and CI are red until this lands. Lowest-coverage modules: `output.py` 0%, `format_cli.py` 13%, `mermaid.py` 20%, `mermaid_cli.py` 29%, `mcp.py` 39%, `review_cli.py` 40%, `lsp.py` 42%.

  Prioritize the untested CLI, output, discovery, Mermaid, LSP, and MCP paths, and fill the `Not Started` rows in §17.3 of `docs/specs/apseudo-validation-toolchain.md` as the tests land.

- [ ] Fix the three remaining pre-existing bugs in `docs/handoff/bugs/`.

  - [bug 001](handoff/bugs/001-mcp-resource-map-stale-paths.md): stale MCP resource paths.
  - [bug 002](handoff/bugs/002-review-completeness-stale-paths.md): stale completeness-check paths.
  - [bug 004](handoff/bugs/004-lsp-serve-unhandled-read-message.md): unguarded LSP message reads.

  Add one pinning regression test per fix, per §17.2 of the toolchain spec.

- [ ] Add the single-policy-source test (NFR-004 / MS-1 in the toolchain spec).

  Assert no rule code or severity is defined outside `src/apseudo_lint/rules.py`. This is the architecture rule the whole design rests on and the only one with no mechanical enforcement.

- [ ] Resolve OQ-001: make `docs/reference/RULES.md` generated rather than hand-maintained.

  The file states it is generated from `rules.py`, but no generator exists. Either write one and wire it into CI, or correct the claim.
