# Project Traceability Review

**Date:** 2026-07-08  
**Toolkit version:** 0.4.0  
**Review scope:** Language convention, tooling, editor integrations, hooks, MCP, skills, repository instructions, and tests.

## Executive summary

The Pythonic Agent Pseudocode convention is now represented across all major enforcement and authoring surfaces. The language standard remains the human-readable source of policy. `src/apseudo_lint/lint.py` and `src/apseudo_lint/rules.py` are the executable source of validation and explanation. Every integration calls or exposes that shared implementation rather than redefining the rules.

## Traceability matrix

| Convention element | Standard section | Validator/rule | Formatter | LSP | Hooks/CI | MCP | Docs/status |
|---|---|---|---|---|---|---|---|
| Python-shaped block structure | Process, branching, loops | `APSEUDO-PARSE-001`, `APSEUDO-PARSE-002` | Normalizes headers and spacing | Diagnostics, symbols, folding | Enforced by `apseudo-lint` | `validate_text`, `validate_file` | OK |
| Named workflows | Process definitions | `APSEUDO-PROC-001` | Preserves declaration shape | Document/workspace symbols | Enforced when configured | Templates generate `process` blocks | OK |
| Explicit outcomes | Outcomes and returns | `APSEUDO-RETURN-*`, `APSEUDO-OUTCOME-001` | Preserves outcome constructors | Completion, hover, diagnostics | Enforced by hooks/CI | Rule explanations and validation | OK |
| Bounded `while` loops | While loops, retry loops | `APSEUDO-WHILE-*` | Preserves bounds and comments | Diagnostics and quick fixes | Enforced by hooks/CI | Rule explanations and templates | OK |
| Finite `for` loops | For loops | `APSEUDO-FOR-001` | Preserves iterable names | Diagnostics and quick fixes | Enforced by hooks/CI | Rule explanations | OK |
| Explicit fallback branches | Conditional branching | `APSEUDO-BRANCH-001` | Preserves branch layout | Quick fix adds `else` fallback | Enforced by hooks/CI | Templates and rule explanations | OK |
| Placeholder resolution | Branching and anti-patterns | `APSEUDO-BRANCH-002` | Preserves placeholders for validator | Diagnostics | Enforced by hooks/CI | Rule explanations | OK |
| Shallow nesting | Guard clauses | `APSEUDO-NEST-001` | Preserves indentation | Diagnostics and folding | Enforced by hooks/CI | Rule explanations | OK |
| Mutating action verification | Side effects | `APSEUDO-ACTION-001` when enabled | Preserves action calls | Diagnostics | Enforced by config/hook/CI when enabled | Rule explanations | OK |
| Action naming | Naming conventions | `APSEUDO-ACTION-002` when verification mode enabled | Preserves names | Diagnostics | Enforced by config/hook/CI when enabled | Rule explanations | OK |
| Normative keywords | Normative language | `APSEUDO-NORM-*` | Uppercases and normalizes | Hover/code action | Enforced as warnings | Rule explanations | OK |
| Markdown fenced blocks | Document-level structure | Extracted by `extract.py` | Formats supported fences only | Diagnostics/completion inside fences | Hooks/CI scan Markdown | MCP validates Markdown files/text | OK |
| Mermaid visualization as view | Combining diagrams and source | Not a correctness rule | Not applicable | Not applicable | Not enforced | `render_mermaid` | OK; documented as view only |

## Tooling representation

| Tooling area | Files | Review |
|---|---|---|
| Standard | `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md` | Complete enough for internal use; labels sourced/adapted/internal claims. |
| Token spec | `docs/reference/language/TOKEN-SPEC.md`, `docs/reference/language/SCOPE-MAP.md` | Provides shared vocabulary for VS Code and Kate. |
| VS Code syntax | `products/vscode-extension/syntaxes/*.yaml`, generated JSON | Grammar files exist and are generated from YAML. |
| Markdown injection | `products/vscode-extension/syntaxes/agent-pseudocode-markdown-injection.*` | Supports fenced Markdown blocks. |
| VS Code LSP client | `products/vscode-extension/extension.js`, `products/vscode-extension/package.json` | Starts `apseudo-lsp` and exposes commands. |
| Kate syntax | `products/kate-integration/agent-pseudocode.xml` | Provides standalone syntax highlighting. |
| Kate LSP | `products/kate-integration/lsp-client-settings*.json` | Config examples for `.apseudo` and optional Markdown. |
| Formatter | `src/apseudo_lint/formatting.py`, `scripts/apseudo-format` | Conservative and shared by LSP/MCP/CLI. |
| Validator | `src/apseudo_lint/lint.py`, `scripts/apseudo-lint` | Enforces core instruction-following rules. |
| Rule catalog | `src/apseudo_lint/rules.py`, `docs/reference/RULES.md` | Central explanation source for humans and tools. |
| Language server | `src/apseudo_lint/lsp.py`, `scripts/apseudo-lsp` | Diagnostics, completion, hover, formatting, code actions, symbols, folding, definition, references. |
| MCP server | `src/apseudo_lint/mcp.py`, `scripts/apseudo-mcp` | Tools/resources/prompts for Claude Code and Codex. |
| Hooks | `integrations/agent-hooks/apseudo-hook.py`, `.claude/settings.json`, `.codex/hooks.json` | Shared script with host-specific configs. |
| Skills | `.claude/skills/agent-pseudocode`, `.agents/skills/agent-pseudocode` | Both agent hosts have repo-scoped skills. |
| pre-commit | `.pre-commit-config.yaml`, `.pre-commit-hooks.yaml` | Local enforcement. |
| CI | `.github/workflows/apseudo-lint.yml` | Repository enforcement. |
| Tests | `tests/` | Covers linter, formatter, LSP, MCP, hooks, and project review. |

## Verification commands

```bash
uv sync --extra dev
uv run pytest
uv run apseudo-format --check .
uv run apseudo-lint .
uv run apseudo-review .
uv run ruff check src tests integrations/agent-hooks
uv run pyright
python3 -m json.tool .claude/settings.json
python3 -m json.tool .codex/hooks.json
python3 -m json.tool .mcp.json
```

## Review result

The project is complete for local internal use. Remaining items are distribution polish rather than missing core capability: SARIF output, semantic tokens, rename support, plugin packaging, and remote MCP transport can be added later if there is a concrete need.
