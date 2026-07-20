# Project Status

## Current snapshot

- The Pythonic Agent Pseudocode toolkit includes syntax, formatter, validator, LSP, MCP, hooks, skills, CI, and documentation.
- The repo adopts ADR, Markdown Tooling, CLI Documentation, Project Specification, Python Tooling, Python Coding, and Agent Handoff.
- Durable Markdown frontmatter follows accepted ADR-0003; `docs/specs/` is reserved for new project-spec-conformant specifications.
- Three pre-existing product bugs remain open in `docs/handoff/bugs/`; bug 003 is fixed.
- Agent Handoff v1 provides one shared repo-local Claude/Codex SessionStart runtime and canonical `docs/` status and task paths.
- The project-standards V4→V5 migration is tool-ready on release 5.2.0 but deferred; three deliberately-customized files (`.editorconfig`, `format.yml`, `cli-docs-check.yml`) need intent decisions before applying, and upstream #12/#13 track the workflow-ownership gaps.
