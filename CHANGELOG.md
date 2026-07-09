# Changelog

## 0.6.1-docs — use-case documentation expansion

- Added comprehensive usage playbooks under `docs/usage/use-cases/`.
- Added `docs/usage/README.md` as a user-documentation index.
- Documented how pseudocode reaches agents through prompts, repo context, runner scripts, hooks, MCP, skills, and editor tooling.
- Added workflow examples for review loops, lint repair, handoff-size control, upstream bug reporting, release gates, template sync, documentation repair, and policy audit.

## 0.6.1 - 2026-07-09

- Restructured repository layout to reduce root sprawl.
- Moved editor/distribution products under `products/`.
- Moved language convention/specification material under `docs/specs/`.
- Moved user documentation under `docs/usage/`, feature docs under `docs/features/`, reviews under `docs/reviews/`, roadmap docs under `docs/roadmap/`, and examples under `docs/examples/`.
- Moved shared Claude/Codex hook implementation under `integrations/agent-hooks/` while preserving root `.claude`, `.codex`, and `.agents` discovery files.
- Updated validation, packaging, install scripts, review checks, and docs to use the new paths.

## 0.5.0 - 2026-07-08

- Added executable Agent Pseudocode runner: `apseudo-run`.
- Added provider aliases: `apseudo-claude` and `apseudo-codex`.
- Added shebang/frontmatter-aware parsing for executable `.apseudo` files.
- Added runner prompt rendering, command preview, built-in outcome schema, structured outcome parsing, safety gates, and shell exit-code mapping.
- Added Claude Code adapter using `claude -p` and JSON schema output.
- Added Codex CLI adapter using `codex exec`, stdin prompt input, `--output-schema`, and `--output-last-message`.
- Added MCP tools for runner validation and prompt rendering.
- Added executable runner examples under `docs/examples/runner/`.
- Added runner docs: `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md`, `docs/usage/RUNNER-USAGE.md`, and `docs/roadmap/FUTURE-VERSIONS.md`.

## 0.3.0 - 2026-07-08

- Added `apseudo-format` formatter CLI.
- Added dependency-free stdio `apseudo-lsp` language server.
- Added LSP-backed diagnostics, completion, hover, and document formatting.
- Added VS Code language-client integration through `vscode-languageclient`.
- Added Markdown snippets for fenced `apseudo` blocks.
- Added Kate LSP Client configuration examples.
- Added formatter/LSP/autocomplete docs and tests.
- Added packaged VSIX artifact: `products/vscode-extension/agent-pseudocode-0.6.1.vsix`.

## 0.2.0 - 2026-07-08

- Added `apseudo-lint` validator CLI.
- Added pre-commit hooks and GitHub Actions CI.
- Added Claude Code and Codex hook examples.
- Added enforcement guide and smoke-test script.

## 0.1.0 - 2026-07-08

- Initial VS Code TextMate grammar.
- Initial VS Code Markdown fenced-code injection grammar.
- Initial YAML-to-JSON grammar compiler.
- Initial VS Code snippets.
- Initial Kate KSyntaxHighlighting XML definition.
- Initial installation and implementation docs.

## 0.4.0 - Agent access, repair, and traceability

- Added `apseudo-mcp` MCP stdio server with validation, formatting, rule explanation, templates, Mermaid rendering, project review, resources, prompts, and server instructions.
- Added `apseudo-review` project completeness review.
- Added LSP code actions, document symbols, folding ranges, definition, references, and workspace symbols.
- Added Claude Code project skill under `.claude/skills/agent-pseudocode`.
- Added Codex repository skill under `.agents/skills/agent-pseudocode`.
- Added `.mcp.json` and `.codex/config.toml` MCP configuration examples.
- Expanded Claude/Codex hooks to SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, SubagentStop, and Stop.
- Added bypass blocking for obvious enforcement bypass commands.
- Added hook audit logging under `.cache/apseudo-hooks/audit.jsonl`.
- Added `docs/reviews/FEATURE-GAP-ANALYSIS.md`, `docs/reviews/PROJECT-TRACEABILITY-REVIEW.md`, `docs/usage/AGENT-INSTRUCTIONS-WORDING.md`, `docs/specs/RULES.md`, `docs/features/MCP.md`, `docs/features/HOOKS.md`, and `docs/features/SKILLS.md`.
