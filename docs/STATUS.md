# Project Status

## Current snapshot

- The Pythonic Agent Pseudocode toolkit includes syntax, formatter, validator, LSP, MCP, hooks, skills, CI, and documentation.
- Project Standards V5 enables all seven consumer packages: adr, agent-handoff, cli-documentation, markdown-frontmatter, markdown-tooling, project-spec, python-tooling.
- The V4 to V5 migration applied on release 5.4.0; `.standards/` is the sole authority and `.project-standards.yml` is retired.
- Durable Markdown frontmatter follows accepted ADR-0003; `docs/specs/` holds project-spec-conformant specifications.
- `SPEC-QZXW` specifies the validation toolchain and is the traceability source for coverage and defect work.
- `docs/usage.md` is the authored CLI reference for `apseudo` and its per-command entry points.
- Markdown lint and Prettier gates are green; the archived pre-migration transcript is a declared, reasoned exclusion.
- The `check.yml` gate is red on coverage alone: 62% against the 85% floor. All other gates pass.
- Three pre-existing product bugs remain open in `docs/handoff/bugs/`; bugs 003, 005, and 006 are fixed.
- Agent Handoff v1 provides one shared repo-local Claude/Codex SessionStart runtime and canonical `docs/` status and task paths.
- `cli-docs-check.yml` stays consumer-owned to keep its SHA-pinned action hardening.
