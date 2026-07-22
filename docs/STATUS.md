# Project Status

## Current snapshot

- The Pythonic Agent Pseudocode toolkit includes syntax, formatter, validator, LSP, MCP, hooks, skills, CI, and documentation.
- Project Standards V5 enables adr, agent-handoff, cli-documentation, markdown-frontmatter, markdown-tooling, and project-spec; python-tooling stays disabled.
- Durable Markdown frontmatter follows accepted ADR-0003; `docs/specs/` is reserved for new project-spec-conformant specifications.
- Three pre-existing product bugs remain open in `docs/handoff/bugs/`; bug 003 is fixed.
- Agent Handoff v1 provides one shared repo-local Claude/Codex SessionStart runtime and canonical `docs/` status and task paths.
- The project-standards V4→V5 migration applied on release 5.4.0; `.standards/` is the sole authority and `.project-standards.yml` is retired.
- The lint-markdown and validate-specs gates are enabled but red: 272 pre-existing markdownlint errors, and no `docs/specs/` corpus yet.
- The Prettier gate is installed as `workflow_dispatch`-only via `format = false`; `cli-docs-check.yml` stays consumer-owned to keep its SHA pins.
