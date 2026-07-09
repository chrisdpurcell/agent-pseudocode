# Project Status

## Completed

- Pythonic Agent Pseudocode toolkit: syntax highlighting, formatter, validator, LSP, MCP server, hooks, skills, CI.

## Current State

- Local development toolkit, no deployment target. Repo migrated to `agent-handoff-v3` session-state layout and `project-standards` (adr, markdown-tooling, cli-documentation, project-spec, python-tooling, python-coding) on 2026-07-08.

## Recent Changes

- [2026-07-08] Adopted agent-handoff-v3 and six project-standards standards.
- [2026-07-09] Merged the standards-adoption branch to `main`; recorded 4 pre-existing bugs found (not introduced) during adoption in `docs/handoff/bugs/`.
- [2026-07-09] Kept agent-handoff-v3 SessionStart hooks active at canonical `.claude/hooks/` and `.codex/hooks/` paths; moved agent-pseudocode lifecycle hook configs under `hooks/` so they stay dormant while MCP wrappers live under `mcp/`.
- [2026-07-09] Accepted ADR-0003, defining the durable Markdown frontmatter corpus, field ownership, consumers, lifecycle, confidence, tags, aliases, and relationship conventions ahead of migration.

## Notes For The Builder

- `docs/specs/` was relocated to `docs/reference/`; the `project-spec` standard now governs a fresh, forward-looking use of `docs/specs/` for project/feature plans only.
