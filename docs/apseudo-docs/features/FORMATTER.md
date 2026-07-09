---
schema_version: '1.1'
id: 'reference-y3sfgy-agent-pseudocode-formatter'
title: 'Agent Pseudocode Formatter'
description: 'Reference for the apseudo-format formatter and its formatting contract.'
doc_type: 'reference'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'formatter'
aliases:
  - 'apseudo-format'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Pseudocode Formatter

Use `apseudo-format` to normalize standalone `.apseudo` files and recognized pseudocode fences in Markdown.

```bash
uv run apseudo-format .
uv run apseudo-format --check .
uv run apseudo-format --diff --check docs examples
```

The formatter normalizes whitespace, indentation width, simple Python-like spacing, inline comment spacing, and normative keyword casing inside comments. It is intentionally conservative and does not rewrite control flow.

See `docs/apseudo-docs/features/FORMATTER-LSP-AUTOCOMPLETE.md` for full details.
