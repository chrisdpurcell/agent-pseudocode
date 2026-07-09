# Agent Pseudocode Syntax Toolkit

**Version:** 0.6.1  
**Date:** 2026-07-08  
**Status:** Working prototype / internal convention

This repository contains a complete editor and enforcement toolkit for the Pythonic Agent Pseudocode convention.

Included layers:

- VS Code extension with TextMate syntax highlighting.
- VS Code Markdown injection grammar for fenced blocks such as ```` ```apseudo ````.
- YAML-to-JSON grammar compiler because VS Code loads JSON grammars while YAML is easier to maintain.
- VS Code snippets and Markdown fenced-block snippets.
- VS Code language-client integration for diagnostics, completion, hover, and formatting.
- Kate / KSyntaxHighlighting XML definition for standalone `.apseudo` files.
- Kate LSP Client configuration examples.
- Pure-Python validator: `apseudo-lint`.
- Pure-Python formatter: `apseudo-format`.
- Dependency-free stdio language server: `apseudo-lsp`.
- MCP stdio server: `apseudo-mcp`.
- Rule explanation, template, Mermaid, project review, and executable runner CLIs.
- Pre-commit hooks, GitHub Actions CI, Claude Code hooks, and Codex hooks.
- Claude Code and Codex repo-scoped skills.
- Executable `.apseudo` script runner for Claude Code and Codex CLI.
- Examples, tests, implementation notes, and operation guides.

## Quick start: Python tooling

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run pyright
```

## Quick start: VS Code

```bash
cd products/vscode-extension
npm install
npm run check
npm run package
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

Open a `.apseudo` file or a Markdown file with an `apseudo` fenced block. Diagnostics, autocomplete, hover, and formatting are provided by `apseudo-lsp`.

## Quick start: Kate

```bash
./scripts/install-kate-user.sh
```

Then enable Kate's LSP Client plugin and paste `products/kate-integration/lsp-client-settings.json` into the User Server Settings area. If `apseudo-lsp` is not on Kate's `PATH`, replace the command with the absolute path to `scripts/apseudo-lsp`.

## Quick start: enforcement

```bash
uv sync --extra dev
scripts/install-enforcement.sh
```

That installs pre-commit/pre-push hooks and runs the local validation suite.

## Core commands

```text
apseudo-lint      Validate structure and instruction-following rules.
apseudo-format    Format standalone pseudocode and recognized Markdown fences.
apseudo-lsp       Serve diagnostics, completion, hover, formatting, code actions, symbols, folding, definition, and references over stdio.
apseudo-mcp       Expose validation, formatting, rules, templates, Mermaid, and review over MCP stdio.
apseudo-explain   Explain APSEUDO-* rules.
apseudo-template  List or emit standard workflow templates.
apseudo-mermaid   Render pseudocode as a Mermaid visualization aid.
apseudo-review    Review project/tooling completeness.
apseudo-run       Execute validated .apseudo scripts through Claude Code or Codex CLI.
apseudo-claude    Runner alias that selects Claude Code.
apseudo-codex     Runner alias that selects Codex CLI.
```

## Docs

| Topic | Document |
|---|---|
| Documentation index | `docs/README.md` |
| Repository layout | `docs/usage/REPOSITORY-LAYOUT.md` |
| Products index | `products/README.md` |
| Feature gap analysis | `docs/reviews/FEATURE-GAP-ANALYSIS.md` |
| Traceability review | `docs/reviews/PROJECT-TRACEABILITY-REVIEW.md` |
| Agent instruction wording | `docs/usage/AGENT-INSTRUCTIONS-WORDING.md` |
| Rule catalog | `docs/specs/RULES.md` |
| MCP server | `docs/features/MCP.md` |
| Agent hooks | `docs/features/HOOKS.md` |
| Agent skills | `docs/features/SKILLS.md` |
| Formatter, LSP, autocomplete | `docs/features/FORMATTER-LSP-AUTOCOMPLETE.md` |
| Formatter only | `docs/features/FORMATTER.md` |
| Language server only | `docs/features/LANGUAGE-SERVER.md` |
| Autocomplete only | `docs/features/AUTOCOMPLETE.md` |
| Enforcement | `docs/enforcement/ENFORCEMENT-GUIDE.md` |
| VS Code | `docs/usage/VSCODE.md` and `products/vscode-extension/README.md` |
| Kate | `docs/usage/KATE.md` and `products/kate-integration/README.md` |
| Executable runner spec | `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md` |
| Runner usage | `docs/usage/RUNNER-USAGE.md` |
| Future runner versions | `docs/roadmap/FUTURE-VERSIONS.md` |
| Sources | `docs/reference/SOURCES.md` |

## Bottom line

The syntax definitions improve readability. `apseudo-lint` and `apseudo-format` are the source of truth for enforceable structure and formatting. `apseudo-lsp`, `apseudo-mcp`, `apseudo-run`, hooks, pre-commit, and CI reuse those same engines so editor feedback, agent access, and repository gates do not drift.
