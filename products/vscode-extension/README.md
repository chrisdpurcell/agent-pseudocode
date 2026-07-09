---
schema_version: '1.1'
id: 'index-0vtp0k-agent-pseudocode-vs-code-extension'
title: 'Agent Pseudocode VS Code Extension'
description: 'Index for the VS Code extension for Pythonic Agent Pseudocode.'
doc_type: 'index'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'product-maintainers'
consumer: 'user'
tags:
  - 'product'
  - 'vscode'
  - 'editor-integration'
aliases:
  - 'VS Code extension'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Pseudocode VS Code Extension

This extension provides syntax highlighting, Markdown fenced-block highlighting, snippets, and LSP-backed language features for Pythonic Agent Pseudocode.

## Features

- TextMate grammar for `.apseudo`, `.agentpseudo`, `.pseudocode`.
- Markdown injection grammar for `apseudo`, `agent-pseudocode`, `agent_pseudocode`, `pythonic-pseudocode`, and `pseudocode-pythonic` fences.
- Snippets for common workflow shapes.
- `apseudo-lsp` client with diagnostics, completion, hover, formatting, code actions, symbols, folding, definition, references, and workspace symbols.
- Commands for explaining APSEUDO-\* rules and reviewing the project.

## Development

```bash
npm install
npm run check
npm run package
```

## Local install

```bash
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

Set `agentPseudocode.server.command` to an absolute `scripts/apseudo-lsp` path if auto-detection fails.
