---
schema_version: '1.1'
id: 'runbook-r72igm-vs-code-integration'
title: 'VS Code Integration'
description: 'User guide for configuring the VS Code extension for Pythonic Agent Pseudocode.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'product-maintainers'
consumer: 'user'
tags:
  - 'runbook'
  - 'usage'
  - 'vscode'
  - 'product'
aliases:
  - 'VS Code extension'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# VS Code Integration

## Features

- Standalone `.apseudo`, `.agentpseudo`, and `.pseudocode` language registration.
- Markdown injection grammar for supported fenced blocks.
- Snippets for standalone pseudocode and Markdown fences.
- Language server diagnostics, completion, hover, formatting, code actions, symbols, folding, definition, references, and workspace symbols.
- Commands:
  - `Agent Pseudocode: Restart Language Server`
  - `Agent Pseudocode: Show Language Server Output`
  - `Agent Pseudocode: Format Document`
  - `Agent Pseudocode: Explain Rule`
  - `Agent Pseudocode: Review Project`

## Build

```bash
cd products/vscode-extension
npm install
npm run check
npm run package
```

## Install

```bash
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

## Server resolution

The extension tries, in order:

1. Configured `agentPseudocode.server.command`.
2. `<workspace>/scripts/apseudo-lsp`.
3. `uv run apseudo-lsp` when the workspace has `pyproject.toml`.
4. `apseudo-lsp` on `PATH`.

## Markdown support

Markdown LSP support is enabled by default. Disable `agentPseudocode.server.enableMarkdown` if diagnostics in Markdown are too noisy.
