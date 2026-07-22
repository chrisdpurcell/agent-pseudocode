# Architecture

**Last updated:** 2026-07-08

## Components

- `src/apseudo_lint/` — the policy source of truth: rules (`rules.py`), formatter (`format_cli.py`), linter (`cli.py`), LSP (`lsp.py`), MCP server (`mcp.py`), pseudocode runner (`runner_cli.py`), project reviewer (`review.py`), template generator (`template_cli.py`), Mermaid renderer (`mermaid_cli.py`).
- `integrations/agent-hooks/apseudo-hook.py` — Claude Code + Codex hook entry point; calls into `src/apseudo_lint` rather than reimplementing rules.
- `products/vscode-extension/`, `products/kate-integration/` — editor integrations; thin wrappers over the LSP/formatter, no duplicated policy.
- `docs/reference/` — normative language/format references (relocated from `docs/specs/` by Task 6 of the 2026-07-08 adoption plan); `docs/specs/` is now empty, reserved for forward-looking project/feature specs under the `project-spec` standard.
- `docs/handoff/` — this handoff system (adopted 2026-07-08).
