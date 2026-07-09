---
schema_version: '1.1'
id: 'reference-hwxn4n-language-server'
title: 'Language Server'
description: 'Reference for the Pythonic Agent Pseudocode language server.'
doc_type: 'reference'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'lsp'
aliases:
  - 'Language server'
  - 'apseudo-lsp'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Language Server

**Command:** `scripts/apseudo-lsp`  
**Python entry point:** `apseudo-lsp`  
**Transport:** stdio LSP with `Content-Length` framing

## Capabilities

| Capability | Status | Notes |
| --- | --: | --- |
| Diagnostics | Implemented | Uses `apseudo-lint` logic. |
| Completion | Implemented | Keywords, outcomes, annotations, templates. |
| Hover | Implemented | Keywords, outcomes, annotations, APSEUDO-\* rules. |
| Formatting | Implemented | Uses `apseudo-format` logic. |
| Code actions | Implemented | Quick fixes for common diagnostics plus format/fix-all. |
| Document symbols | Implemented | Process declarations. |
| Folding ranges | Implemented | Python-shaped block headers. |
| Definition | Implemented | Local process symbol lookup. |
| References | Implemented | Local token occurrences. |
| Workspace symbols | Implemented | Open-document process symbols. |
| Rename | Not implemented | Optional later feature. |
| Semantic tokens | Not implemented | Optional later feature. |

## Code actions

The server provides conservative quick fixes:

- Normalize normative keywords.
- Replace `SHALL` / `SHALL NOT` with `MUST` / `MUST NOT`.
- Add explicit `else` fallback.
- Add terminal `Blocked(...)` outcome.
- Insert bounded-loop or finite-collection annotation placeholders.
- Insert loop-control update reminder.
- Explain APSEUDO-\* rules through the VS Code command bridge when available.

Code actions do not prove business logic. They repair convention shape and make missing intent visible.

## Markdown behavior

For Markdown files, the server only provides pseudocode diagnostics/completion/hover inside supported fenced blocks:

````md
```apseudo
process demo() -> Outcome:
    return Accepted(reason="ok")
```
````

## VS Code

The VS Code extension starts the server from `products/vscode-extension/extension.js` using `vscode-languageclient`. It applies to standalone pseudocode files and Markdown documents.

## Kate

Kate can use the same server through the LSP Client plugin. Use `products/kate-integration/lsp-client-settings.json` and replace the command with an absolute path if Kate cannot find `apseudo-lsp`.
