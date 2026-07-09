---
schema_version: '1.1'
id: 'reference-f6gmg3-agent-pseudocode-autocomplete'
title: 'Agent Pseudocode Autocomplete'
description: 'Reference for autocomplete behavior in Pythonic Agent Pseudocode editor integrations.'
doc_type: 'reference'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'product-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'editor-integration'
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Pseudocode Autocomplete

Autocomplete is provided in two layers:

1. Static VS Code snippets in `products/vscode-extension/snippets/`.
2. Editor-neutral LSP completions from `apseudo-lsp`.

Completion categories:

- control-flow keywords;
- approved outcome constructors;
- annotations and lint suppressions;
- process, review-loop, bounded-while, and branch-chain snippets.

Kate receives autocomplete through the LSP Client plugin when `apseudo-lsp` is configured for the `Agent Pseudocode` highlighting mode.
