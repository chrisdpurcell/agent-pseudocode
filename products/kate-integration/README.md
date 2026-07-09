---
schema_version: '1.1'
id: 'index-dfvacg-kate-files'
title: 'Kate Files'
description: 'Index for Kate integration files for Pythonic Agent Pseudocode.'
doc_type: 'index'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'product-maintainers'
consumer: 'user'
tags:
  - 'product'
  - 'kate'
  - 'editor-integration'
aliases:
  - 'Kate integration'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Kate Files

- `agent-pseudocode.xml`: KSyntaxHighlighting definition for standalone pseudocode files.
- `lsp-client-settings.json`: LSP Client settings for standalone pseudocode files.
- `lsp-client-settings.markdown-opt-in.json`: optional Markdown LSP settings.

Install the XML file with:

```bash
../scripts/install-kate-user.sh
```

Then configure Kate's LSP Client plugin. If `apseudo-lsp` is not on `PATH`, use the absolute path to `scripts/apseudo-lsp`.
