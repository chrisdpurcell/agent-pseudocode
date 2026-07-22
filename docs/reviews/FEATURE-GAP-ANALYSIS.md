# Feature Gap Analysis: Pythonic Agent Pseudocode Toolkit

**Date:** 2026-07-08  
**Toolkit version:** 0.4.0  
**Status:** Implemented review snapshot

## Executive summary

The original toolkit already had the core authoring path: syntax highlighting, Markdown injection, formatter, validator, VS Code language-client wiring, Kate syntax files, pre-commit, CI, and basic Claude/Codex hooks. The main missing layers were agent-facing deterministic access, richer editor repair features, reusable skill packaging, project-level review, and explicit traceability from the language convention to every tool.

Version 0.4.0 adds those missing layers:

- MCP server: `apseudo-mcp`.
- Project review CLI: `apseudo-review`.
- Rule explanation CLI: `apseudo-explain`.
- Template CLI: `apseudo-template`.
- Mermaid visualization CLI: `apseudo-mermaid`.
- LSP code actions, document symbols, folding ranges, definition, references, and workspace symbols.
- Claude Code and Codex repo skills.
- Claude and Codex MCP configuration examples.
- Expanded Claude/Codex hooks for prompt, pre-tool, permission, post-tool, subagent, and stop events.
- Audit logging for hooks under `.cache/apseudo-hooks/audit.jsonl`.
- Agent instruction wording that can be copied into other repositories.
- Project traceability review.

## Feature analysis by layer

| Layer | Earlier status | Gap | Added in 0.4.0 | Remaining optional work |
| --- | --- | --- | --- | --- |
| Language convention | Comprehensive Markdown standard existed | Needed explicit traceability into tool rules | `docs/reviews/PROJECT-TRACEABILITY-REVIEW.md` and `docs/reference/RULES.md` | Add project-specific outcome profiles for different agent domains |
| Syntax highlighting | VS Code TextMate and Kate XML existed | No semantic repair | LSP code actions now complement highlighting | Add semantic tokens if the language grows beyond regex scopes |
| Formatter | Conservative formatter existed | No MCP exposure | `format_text` and `format_file` MCP tools | Add configurable import-like section sorting if the dialect later gains sections |
| Validator/linter | Core structural rules existed | Rule explanations were not central enough | `src/apseudo_lint/rules.py`, `apseudo-explain`, `docs/reference/RULES.md`, MCP `explain_rule` | Add deeper path analysis for exhaustive branch proof |
| CLI utilities | Lint/format/LSP existed | Missing templates, rule explanation, visualization, review | `apseudo-template`, `apseudo-explain`, `apseudo-mermaid`, `apseudo-review` | Add SARIF output for code scanning platforms |
| Language server | Diagnostics/completion/hover/format existed | Missing quick fixes and navigation | Code actions, symbols, folding, definition, references, workspace symbols | Add semantic tokens and rename support if needed |
| VS Code extension | LSP client existed | Needed to advertise richer LSP behavior | Server capabilities now expose richer features | Add VS Code command UI for template insertion |
| Kate integration | Syntax XML and LSP config existed | Kate depends on client support for richer LSP features | Existing Kate LSP config now benefits from server code actions/symbols where supported | Add Kate snippets/templates if you want parity with VS Code snippets |
| Hooks | Basic SessionStart/PostToolUse/Stop | Missing prompt/pre-tool/permission/subagent checks and bypass policy | Expanded events and bypass blocking for Claude/Codex | Add host-specific JSON decision output if you want richer UI messages |
| Agent skills | Missing | Agents had to rely on instructions and hooks only | `.claude/skills/agent-pseudocode` and `.agents/skills/agent-pseudocode` | Package as a Claude plugin or Codex plugin for distribution |
| MCP | Missing | Agents lacked a callable validation/control plane | `apseudo-mcp` with tools, resources, prompts, and server instructions | Add streamable HTTP transport if remote use becomes necessary |
| Repository enforcement | pre-commit and CI existed | Needed complete agent wording and cross-host hooks | `docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md` and expanded hooks | Make CI check required in branch protection |
| Project review | Missing | No single command to check completeness | `apseudo-review` | Add machine-readable score thresholds if useful |

## Important design decisions

### One validator, many integrations

The validator remains the source of truth. The formatter, language server, hooks, MCP server, and CI do not implement independent policy. They call or reuse the same Python modules.

### MCP is agent access, not the final gate

The MCP server gives Claude Code and Codex tools such as `validate_file`, `explain_rule`, and `generate_template`. It is not the hard enforcement boundary. Hard enforcement remains pre-commit, CI, and hooks.

### Hooks block bypass attempts

The hook script now blocks obvious bypass commands such as `git commit --no-verify`, `SKIP=...`, `pre-commit uninstall`, and direct edits to enforcement files before tool execution. This is intentionally narrow; it protects this standard without trying to become a general shell security policy.

### LSP repair is intentionally conservative

Code actions add explicit fallbacks, terminal outcomes, bounded-loop placeholders, and normative keyword normalization. They do not attempt to prove business logic correctness.

## Remaining non-blocking opportunities

| Opportunity | Value | Cost | Recommendation |
| --- | --: | --: | --- |
| SARIF output | Useful for GitHub code scanning | Low-medium | Add later if this becomes a shared org standard |
| Semantic tokens | Better editor theming | Medium | Defer until syntax scopes become insufficient |
| Rename provider | Rename process symbols | Medium | Useful only if processes become large and cross-file |
| Deeper control-flow graph | Stronger branch/return proof | High | Defer; current line-oriented validator is appropriate |
| Remote MCP HTTP transport | Remote agents without local stdio | Medium-high | Defer until there is a concrete remote-host requirement |
| Plugin packaging | Easier distribution | Medium | Add if you plan to install this across many repos |

## Recommendation

Treat version 0.4.0 as the first complete internal distribution. The standard is now represented through authoring, validation, formatting, editor feedback, agent runtime enforcement, MCP access, skills, repository gates, and review documentation.
